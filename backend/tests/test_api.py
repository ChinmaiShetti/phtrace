"""API tests: authentication, role checks, validation and the full incident workflow over HTTP.
TC25 (login), TC26 (403), TC27 (SQL injection), TC34 (validation) and an end-to-end scenario."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app import db
from app.auth import hasher
from app.config import get_settings
from app.main import app
from tests.conftest import TEST_DB, one

PASSWORD = "secret-pass"


@pytest.fixture
def client(owner, world):
    owner.execute("UPDATE staff SET password_hash = %s", [hasher.hash(PASSWORD)])
    s = get_settings()
    db._pool = ConnectionPool(s.url("pharmatrace_app", s.pg_app_password, TEST_DB), min_size=1, max_size=4,
                              kwargs={"row_factory": dict_row}, open=True)
    with TestClient(app) as c:
        yield c
    db.close_pool()


def login(client, role):
    r = client.post("/api/auth/login", data={"username": f"{role}@test.local", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_tc25_wrong_password_rejected(client):
    r = client.post("/api/auth/login", data={"username": "operator@test.local", "password": "nope"})
    assert r.status_code == 401
    assert "access_token" not in r.json()


def test_requests_need_a_token(client):
    assert client.get("/api/batches").status_code == 401
    assert client.get("/api/batches", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_tc26_operator_cannot_change_batch_status(client, world):
    h = login(client, "operator")
    r = client.post(f"/api/batches/{world['b1']}/status", json={"status": "released", "reason": "try"}, headers=h)
    assert r.status_code == 403


def test_tc26_database_rule_applies_even_to_allowed_api_roles(client, world):
    h = login(client, "investigator")   # investigators may hold, but not quarantine
    r = client.post(f"/api/batches/{world['b1']}/status", json={"status": "quarantined", "reason": "test"}, headers=h)
    assert r.status_code == 403
    assert "may not change batch" in r.json()["detail"]


def test_tc27_sql_injection_is_plain_text(client):
    h = login(client, "operator")
    everything = client.get("/api/batches", headers=h).json()
    injected = client.get("/api/batches", params={"q": "' OR 1=1 --"}, headers=h)
    assert injected.status_code == 200
    assert injected.json() == [] and len(everything) == 5


def test_tc34_validation_messages(client, world):
    h = login(client, "operator")
    r = client.post("/api/products", json={"product_name": "X", "product_type": "vaccine", "min_temp": 8, "max_temp": 2},
                    headers=h)
    assert r.status_code == 422
    r = client.post("/api/shipments", json={"vehicle_id": world["van"], "origin_facility_id": world["wh"]}, headers=h)
    assert r.status_code == 422
    assert any(e["loc"][-1] == "destination_facility_id" for e in r.json()["detail"])


def test_db_errors_become_readable_responses(client, world):
    h = login(client, "operator")
    body = {"batch_number": "B1", "product_id": world["vaccine"], "manufacturing_date": "2025-01-01",
            "expiry_date": "2027-01-01", "initial_quantity": 5, "intake_facility_id": world["wh"]}
    r = client.post("/api/batches", json=body, headers=h)
    assert r.status_code == 409


def test_end_to_end_incident_workflow(client, world):
    op, inv, qm = login(client, "operator"), login(client, "investigator"), login(client, "quality_manager")
    arrival = (datetime.now(UTC) + timedelta(hours=5)).isoformat()

    # create and dispatch a shipment with a sensor
    r = client.post("/api/shipments", headers=op, json={
        "vehicle_id": world["van"], "origin_facility_id": world["wh"], "destination_facility_id": world["hosp"],
        "expected_arrival": arrival, "sensor_id": world["s1"],
        "lines": [{"batch_id": world["b1"], "quantity_shipped": 300}, {"batch_id": world["b3"], "quantity_shipped": 50}]})
    assert r.status_code == 201, r.text
    sid = r.json()["shipment_id"]
    assert client.post(f"/api/shipments/{sid}/dispatch", headers=op).json()["shipment_status"] == "in_transit"

    # readings: normal, then a breach (duplicate is skipped)
    t = datetime.now(UTC).replace(microsecond=0)
    # timestamps after the sensor was attached (readings before an assignment are stored but not evaluated)
    batch = [{"sensor_id": world["s1"], "recorded_at": (t + timedelta(seconds=s)).isoformat(), "temperature": temp}
             for s, temp in ((20, 5.0), (40, 10.4))]
    r = client.post("/api/readings", json=batch + batch[:1], headers=op).json()
    assert r == {"received": 3, "inserted": 2, "duplicates": 1, "incidents_opened": 1}

    incident = client.get("/api/incidents", headers=qm).json()[0]
    iid = incident["incident_id"]
    detail = client.get(f"/api/incidents/{iid}", headers=inv).json()
    assert [b["batch_number"] for b in detail["batches"]] == ["B1"]          # syrup (2-25 °C) not affected

    # quality manager assigns; investigator records findings, holds and assesses the batch, adds an action
    iv = client.post(f"/api/incidents/{iid}/investigations", json={"assigned_to": world["investigator"]}, headers=qm)
    assert iv.status_code == 201
    ivid = iv.json()["investigation_id"]
    assert client.post(f"/api/batches/{world['b1']}/status", json={"status": "on_hold", "reason": "excursion"},
                       headers=inv).status_code == 200
    client.patch(f"/api/incidents/{iid}/batches/{world['b1']}", headers=inv,
                 json={"assessment_status": "assessed", "assessment_note": "Within stability data"})
    act = client.post(f"/api/investigations/{ivid}/actions", headers=inv,
                      json={"assigned_to": world["operator"], "action_description": "Check door seal"}).json()

    # closing too early is refused with the reason
    r = client.post(f"/api/incidents/{iid}/status", json={"status": "resolved", "reason": "done"}, headers=qm)
    assert r.status_code == 409 and "not completed" in r.json()["detail"]

    client.patch(f"/api/investigations/{ivid}", headers=inv,
                 json={"findings": "Door left open at checkpoint", "investigation_status": "completed"})
    client.patch(f"/api/actions/{act['action_id']}", json={"action_status": "completed"}, headers=op)
    assert client.post(f"/api/incidents/{iid}/status", json={"status": "resolved", "reason": "review"},
                       headers=qm).status_code == 200
    assert client.post(f"/api/incidents/{iid}/status", json={"status": "closed", "reason": "investigator tries"},
                       headers=inv).status_code == 403
    assert client.post(f"/api/batches/{world['b1']}/status", json={"status": "released", "reason": "QA release"},
                       headers=qm).status_code == 200
    r = client.post(f"/api/incidents/{iid}/status", json={"status": "closed", "reason": "complete"}, headers=qm)
    assert r.status_code == 200 and r.json()["incident_status"] == "closed"

    trace = client.get(f"/api/batches/{world['b1']}/trace", headers=op).json()
    assert [h["to_status"] for h in trace["status_history"]] == ["on_hold", "released"]
    assert trace["status_history"][1]["reason"] == "QA release"
    assert client.get("/api/dashboard", headers=op).json()["counts"]["open_incidents"] == 0


def test_reports_and_dashboard_available(client):
    h = login(client, "operator")
    for rep in client.get("/api/reports", headers=h).json():
        assert client.get(f"/api/reports/{rep['key']}", headers=h).status_code == 200
    assert client.get("/api/reports/pg_shadow", headers=h).status_code == 404


def test_admin_only_endpoints(client):
    assert client.post("/api/staff", headers=login(client, "operator"),
                       json={"staff_name": "X Y", "email": "x@y.zz", "password": "longenough", "role": "admin"}
                       ).status_code == 403
    r = client.post("/api/staff", headers=login(client, "admin"),
                    json={"staff_name": "New Person", "email": "new@test.local", "password": "longenough",
                          "role": "investigator"})
    assert r.status_code == 201 and "password_hash" not in r.json()


def test_owner_sees_hashes_not_in_api(client, owner):
    assert one(owner, "SELECT COUNT(*) FROM staff WHERE password_hash LIKE '$argon2%%'") == 4
