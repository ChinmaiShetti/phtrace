"""Run every lab-manual test case (TC01-TC34) on a fresh database and record the system's ACTUAL response.

Output: docs/final-report/evidence/test_evidence.json and test_evidence.md. This is the proof used in the
final report's test tables: the exact PostgreSQL error, row counts or HTTP status for each case.
It builds its own database (pharmatrace_evidence), so the demo and test databases are untouched.

Usage (from backend/): uv run python -m scripts.evidence
"""

import json
import threading
import time
from datetime import UTC, date, datetime, timedelta

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app import db as app_db
from app.auth import hasher
from app.config import ROOT, get_settings
from scripts.reset_db import apply_schema, create_roles_and_db

DB = "pharmatrace_evidence"
OUT = ROOT / "docs" / "final-report" / "evidence"
TABLES = ("audit_log, corrective_action, investigation, incident_batch, incident_reading, incident, sensor_reading, "
          "sensor_assignment, sensor, batch_movement, shipment_checkpoint, shipment_batch, shipment, vehicle, "
          "facility_phone, facility, batch, product, staff")
NOW = datetime.now(UTC).replace(microsecond=0)
PASSWORD = "evidence-pass"
s = get_settings()


def connect(role: str, autocommit: bool = True) -> psycopg.Connection:
    pw = s.pg_owner_password if role == "owner" else s.pg_app_password
    return psycopg.connect(s.url(f"pharmatrace_{role}", pw, DB), autocommit=autocommit)


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def as_staff(conn, staff_id):
    conn.execute("SELECT set_config('app.current_staff_id', %s, false)", [str(staff_id)])


def fresh_world(owner) -> dict:
    """Empty every table and insert a small consistent data set (same as tests/conftest.py::world)."""
    owner.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    w = {}
    for role in ("operator", "investigator", "quality_manager", "admin"):
        w[role] = one(owner, "INSERT INTO staff (staff_name, email, password_hash, role) VALUES (%s,%s,%s,%s) "
                             "RETURNING staff_id", [role.replace("_", " ").title(), f"{role}@test.local",
                                                    hasher.hash(PASSWORD), role])
    for key, name, lo, hi in (("vaccine", "Vaccine A", 2, 8), ("syrup", "Syrup E", 2, 25), ("tablet", "Tablet D", 15, 25)):
        w[key] = one(owner, "INSERT INTO product (product_name, product_type, min_temp, max_temp) "
                            "VALUES (%s,'medicine',%s,%s) RETURNING product_id", [name, lo, hi])
    for key, name in (("wh", "Warehouse"), ("dc", "Distribution Centre"), ("hosp", "Hospital")):
        w[key] = one(owner, "INSERT INTO facility (facility_name, facility_type, street, city, pincode) "
                            "VALUES (%s,'warehouse','1 Road','Bengaluru','560001') RETURNING facility_id", [name])
    w["van"] = one(owner, "INSERT INTO vehicle (registration_number, vehicle_type) VALUES ('KA01AA0001','refrigerated_van') "
                          "RETURNING vehicle_id")
    for key, product, qty, expiry in (("b1", "vaccine", 1000, date(2030, 1, 1)), ("b2", "vaccine", 500, date(2030, 1, 1)),
                                      ("b3", "syrup", 300, date(2030, 1, 1)), ("b4", "tablet", 200, date(2030, 1, 1)),
                                      ("bexp", "vaccine", 100, date.today() - timedelta(days=1))):
        w[key] = one(owner, "INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
                            "VALUES (%s,%s,'2024-01-01',%s,%s) RETURNING batch_id", [key.upper(), w[product], expiry, qty])
        owner.execute("INSERT INTO batch_movement (batch_id, facility_id, movement_type, movement_time, quantity_moved) "
                      "VALUES (%s,%s,'received',%s,%s)", [w[key], w["wh"], NOW - timedelta(days=2), qty])
    for i in (1, 2, 3):
        w[f"s{i}"] = one(owner, "INSERT INTO sensor (serial_number, sensor_type) VALUES (%s,'temperature') RETURNING sensor_id",
                         [f"S{i}"])
    return w


def shipment(conn, w, lines, sensor="s1", dest="dc"):
    sid = one(conn, "INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival) "
                    "VALUES (%s,%s,%s,%s) RETURNING shipment_id", [w["van"], w["wh"], w[dest], NOW + timedelta(hours=6)])
    for b, q in lines:
        conn.execute("INSERT INTO shipment_batch VALUES (%s,%s,%s)", [sid, w[b], q])
    if sensor:
        conn.execute("INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (%s,%s,%s)",
                     [w[sensor], sid, NOW - timedelta(hours=1)])
    return sid


def reading(conn, w, sensor, minutes_ago, temp):
    return one(conn, "INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) VALUES (%s,%s,%s) RETURNING reading_id",
               [w[sensor], NOW - timedelta(minutes=minutes_ago), temp])


def db_error(e: psycopg.Error) -> str:
    text = f"{type(e).__name__}: {e.diag.message_primary}"
    if e.diag.constraint_name:
        text += f" [constraint {e.diag.constraint_name}]"
    return text


def expect_error(conn, sql, params=()):
    """Run a statement that must fail; return the database's error text (raise AssertionError if it succeeds)."""
    try:
        conn.execute(sql, params)
    except psycopg.Error as e:
        return db_error(e)
    raise AssertionError("statement succeeded but should have been rejected")


# ---------------------------------------------------------------------------------------------- the test cases
CASES = []


def case(tc, module, title, action, expected):
    def wrap(fn):
        CASES.append((tc, module, title, action, expected, fn))
        return fn
    return wrap


@case("TC01", "Product", "Register a valid product", "INSERT product 'Vaccine X', vaccine, 2.00-8.00 °C",
      "Product saved; new product_id returned")
def tc01(owner, app, w, api):
    pid = one(app, "INSERT INTO product (product_name, product_type, min_temp, max_temp) "
                   "VALUES ('Vaccine X','vaccine',2.00,8.00) RETURNING product_id")
    return f"Saved: product_id={pid}"


@case("TC02", "Product", "Invalid temperature range rejected", "INSERT product with min_temp 8, max_temp 2",
      "Rejected by CHECK (min_temp < max_temp)")
def tc02(owner, app, w, api):
    return expect_error(app, "INSERT INTO product (product_name, product_type, min_temp, max_temp) VALUES ('Bad','vaccine',8,2)")


@case("TC03", "Batch", "Duplicate batch number rejected", "INSERT a second batch with number B1",
      "Second insert rejected (UNIQUE)")
def tc03(owner, app, w, api):
    return expect_error(app, "INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
                             "VALUES ('B1',%s,'2025-01-01','2027-01-01',10)", [w["vaccine"]])


@case("TC04", "Batch", "Expiry before manufacture rejected", "INSERT batch mfg 2026-05-01, expiry 2026-04-01",
      "Rejected by CHECK (expiry_date > manufacturing_date)")
def tc04(owner, app, w, api):
    return expect_error(app, "INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
                             "VALUES ('X1',%s,'2026-05-01','2026-04-01',10)", [w["vaccine"]])


@case("TC05", "Batch", "Quantity boundary", "INSERT batch with initial_quantity 0, then 1", "0 rejected; 1 accepted")
def tc05(owner, app, w, api):
    sql = ("INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
           "VALUES (%s,%s,'2025-01-01','2027-01-01',%s) RETURNING batch_id")
    zero = expect_error(app, sql, ["Q0", w["vaccine"], 0])
    bid = one(app, sql, ["Q1", w["vaccine"], 1])
    return f"Quantity 0 -> {zero}. Quantity 1 -> saved (batch_id={bid})"


@case("TC06", "Product", "Product with batches cannot be deleted", "DELETE product 'Vaccine A' (has batches)",
      "Rejected by foreign key (ON DELETE RESTRICT)")
def tc06(owner, app, w, api):
    return expect_error(owner, "DELETE FROM product WHERE product_id = %s", [w["vaccine"]])


@case("TC07", "Shipment", "Shipment with nonexistent vehicle rejected", "INSERT shipment with vehicle_id 999",
      "Rejected by foreign key")
def tc07(owner, app, w, api):
    return expect_error(app, "INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival) "
                             "VALUES (999,%s,%s,now())", [w["wh"], w["dc"]])


@case("TC08", "Shipment", "Same origin and destination rejected", "INSERT shipment Warehouse -> Warehouse",
      "Rejected by CHECK (origin <> destination)")
def tc08(owner, app, w, api):
    return expect_error(app, "INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival) "
                             "VALUES (%s,%s,%s,now())", [w["van"], w["wh"], w["wh"]])


@case("TC09", "Shipment", "Add batch to shipment", "INSERT shipment_batch (shipment, B1, 1000)", "Row saved in SHIPMENT_BATCH")
def tc09(owner, app, w, api):
    sid = shipment(app, w, [("b1", 1000)])
    q = one(app, "SELECT quantity_shipped FROM shipment_batch WHERE shipment_id = %s", [sid])
    return f"Saved: shipment {sid} carries B1 x {q}"


@case("TC10", "Shipment", "Same batch twice in one shipment rejected", "INSERT shipment_batch B1 again for the same shipment",
      "Rejected (composite primary key)")
def tc10(owner, app, w, api):
    sid = shipment(app, w, [("b1", 100)])
    return expect_error(app, "INSERT INTO shipment_batch VALUES (%s,%s,50)", [sid, w["b1"]])


@case("TC11", "Transaction", "Dispatch a shipment", "SELECT dispatch_shipment() for B1 x400 + B2 x100 with sensor attached",
      "Status in_transit; dispatch movements and departure checkpoint recorded; stock reduced")
def tc11(owner, app, w, api):
    sid = shipment(app, w, [("b1", 400), ("b2", 100)])
    app.execute("SELECT dispatch_shipment(%s)", [sid])
    st = one(app, "SELECT shipment_status FROM shipment WHERE shipment_id = %s", [sid])
    mv = one(app, "SELECT COUNT(*) FROM batch_movement WHERE shipment_id = %s AND movement_type = 'dispatched'", [sid])
    cp = one(app, "SELECT event_type FROM shipment_checkpoint WHERE shipment_id = %s", [sid])
    stock = one(app, "SELECT batch_stock_at(%s, %s)", [w["b1"], w["wh"]])
    assert (st, mv, cp, stock) == ("in_transit", 2, "departure", 600)
    return f"status={st}; dispatched movements={mv}; checkpoint={cp}; B1 stock at origin 1000 -> {stock}"


@case("TC12", "Transaction", "Partial failure rolls back the whole dispatch",
      "dispatch_shipment() with B1 x100 (in stock) and B2 x9999 (only 500 in stock)",
      "Error raised; no movement kept for B1 or B2; status stays planned")
def tc12(owner, app, w, api):
    sid = shipment(app, w, [("b1", 100), ("b2", 9999)])
    err = expect_error(app, "SELECT dispatch_shipment(%s)", [sid])
    mv = one(app, "SELECT COUNT(*) FROM batch_movement WHERE shipment_id = %s", [sid])
    st = one(app, "SELECT shipment_status FROM shipment WHERE shipment_id = %s", [sid])
    stock = one(app, "SELECT batch_stock_at(%s, %s)", [w["b1"], w["wh"]])
    assert (mv, st, stock) == (0, "planned", 1000)
    return f"{err}. Afterwards: movements for this shipment={mv}, status={st}, B1 stock={stock} (unchanged)"


@case("TC13", "Transaction", "Expired or quarantined batch cannot be dispatched",
      "dispatch_shipment() with an expired batch; then with a quarantined batch", "Dispatch rejected with a message")
def tc13(owner, app, w, api):
    e1 = expect_error(app, "SELECT dispatch_shipment(%s)", [shipment(app, w, [("bexp", 10)])])
    as_staff(app, w["quality_manager"])
    app.execute("UPDATE batch SET batch_status = 'quarantined' WHERE batch_id = %s", [w["b1"]])
    e2 = expect_error(app, "SELECT dispatch_shipment(%s)", [shipment(app, w, [("b1", 10)], sensor="s2")])
    return f"Expired: {e1}. Quarantined: {e2}"


@case("TC14", "Concurrency", "Two concurrent dispatches cannot oversell stock",
      "Two sessions each dispatch 800 of the 1,000 units of B1 at the same time",
      "One commits, the other fails; stock never negative")
def tc14(owner, app, w, api):
    a = shipment(app, w, [("b1", 800)], sensor="s1")
    b = shipment(app, w, [("b1", 800)], sensor="s2")
    first, second = connect("app", autocommit=False), connect("app", autocommit=False)
    first.execute("SELECT dispatch_shipment(%s)", [a])            # holds the row lock on B1, not committed yet
    outcome = {}

    def run_second():
        try:
            second.execute("SELECT dispatch_shipment(%s)", [b])
            second.commit()
            outcome["second"] = "committed"
        except psycopg.Error as e:
            second.rollback()
            outcome["second"] = db_error(e)

    t = threading.Thread(target=run_second)
    t.start()
    time.sleep(0.5)
    waited = t.is_alive()
    first.commit()
    t.join(10)
    first.close()
    second.close()
    stock = one(app, "SELECT batch_stock_at(%s, %s)", [w["b1"], w["wh"]])
    assert waited and "Insufficient stock" in outcome["second"] and stock == 200
    return (f"Session 1 committed. Session 2 waited for the row lock (waiting={waited}), then: {outcome['second']}. "
            f"Final B1 stock at origin = {stock}")


@case("TC15", "Transaction", "Receive a shipment", "dispatch_shipment() then receive_shipment() for B1 x300",
      "Status delivered; stock moved to destination; sensor assignment closed")
def tc15(owner, app, w, api):
    sid = shipment(app, w, [("b1", 300)])
    app.execute("SELECT dispatch_shipment(%s)", [sid])
    app.execute("SELECT receive_shipment(%s)", [sid])
    st = one(app, "SELECT shipment_status FROM shipment WHERE shipment_id = %s", [sid])
    stock = one(app, "SELECT batch_stock_at(%s, %s)", [w["b1"], w["dc"]])
    open_ = one(app, "SELECT COUNT(*) FROM sensor_assignment WHERE shipment_id = %s AND unassigned_at IS NULL", [sid])
    assert (st, stock, open_) == ("delivered", 300, 0)
    return f"status={st}; B1 stock at destination={stock}; open sensor assignments={open_}"


@case("TC16", "Monitoring", "Overlapping sensor assignment rejected",
      "Assign sensor S1 to a second shipment while it is still attached to the first", "Rejected (EXCLUDE constraint)")
def tc16(owner, app, w, api):
    shipment(app, w, [("b1", 10)], sensor="s1")
    s2 = shipment(app, w, [("b2", 10)], sensor=None)
    return expect_error(app, "INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (%s,%s,%s)",
                        [w["s1"], s2, NOW])


def dispatched(app, w):
    sid = shipment(app, w, [("b1", 100), ("b3", 50)])                    # vaccine 2-8 °C + syrup 2-25 °C
    app.execute("SELECT dispatch_shipment(%s, %s)", [sid, NOW - timedelta(minutes=50)])
    return sid


@case("TC17", "Monitoring", "Valid reading inside limits", "Reading 5.2 °C from S1 on a dispatched shipment",
      "Reading saved as valid; no incident")
def tc17(owner, app, w, api):
    dispatched(app, w)
    rid = reading(app, w, "s1", 30, 5.2)
    q = one(app, "SELECT quality_status FROM sensor_reading WHERE reading_id = %s", [rid])
    n = one(app, "SELECT COUNT(*) FROM incident")
    assert (q, n) == ("valid", 0)
    return f"reading_id={rid} stored, quality={q}; incidents={n}"


@case("TC18", "Monitoring", "Reading outside limits raises an incident", "Readings 5.2 °C, then 8.6 °C (vaccine limit 8 °C)",
      "Reading saved; incident created and linked to shipment, reading and batch")
def tc18(owner, app, w, api):
    sid = dispatched(app, w)
    reading(app, w, "s1", 30, 5.2)
    rid = reading(app, w, "s1", 25, 8.6)
    row = app.execute("SELECT incident_id, incident_type, shipment_id, detection_source, incident_status, severity FROM incident"
                      ).fetchall()
    assert len(row) == 1 and row[0][2] == sid
    linked = one(app, "SELECT COUNT(*) FROM incident_reading WHERE reading_id = %s", [rid])
    return (f"1 incident: id={row[0][0]}, type={row[0][1]}, shipment={row[0][2]}, source={row[0][3]}, status={row[0][4]}, "
            f"severity={row[0][5]}; breaching reading linked={bool(linked)}")


@case("TC19", "Monitoring", "Repeated breach appends to the same incident", "Readings 8.6 °C then 12.5 °C",
      "Same open incident; severity raised; no new incident")
def tc19(owner, app, w, api):
    dispatched(app, w)
    reading(app, w, "s1", 25, 8.6)
    sev1 = one(app, "SELECT severity FROM incident")
    reading(app, w, "s1", 20, 12.5)
    n, sev2, links = app.execute("SELECT COUNT(*), MAX(severity), (SELECT COUNT(*) FROM incident_reading) FROM incident"
                                 ).fetchone()
    assert n == 1 and links == 2
    return f"incidents={n}; severity {sev1} -> {sev2}; linked readings={links}"


@case("TC20", "Monitoring", "Duplicate reading rejected", "Same sensor and timestamp inserted twice",
      "Rejected (UNIQUE sensor_id, recorded_at)")
def tc20(owner, app, w, api):
    dispatched(app, w)
    reading(app, w, "s1", 30, 5.0)
    return expect_error(app, "INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) VALUES (%s,%s,5.0)",
                        [w["s1"], NOW - timedelta(minutes=30)])


@case("TC21", "Monitoring", "Future timestamp stored as invalid", "Reading 20 °C recorded 2 hours in the future",
      "Stored with quality invalid; no incident")
def tc21(owner, app, w, api):
    dispatched(app, w)
    rid = one(app, "INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) VALUES (%s, now() + interval '2 hours', 20) "
                   "RETURNING reading_id", [w["s1"]])
    q = one(app, "SELECT quality_status FROM sensor_reading WHERE reading_id = %s", [rid])
    n = one(app, "SELECT COUNT(*) FROM incident")
    assert (q, n) == ("invalid", 0)
    return f"reading_id={rid} stored, quality={q}; incidents={n}"


@case("TC22", "Monitoring", "Missing readings appear in the data-quality report",
      "Readings at -45, -40, -35, -5, 0 min (5-minute sensor) -> a 30-minute hole", "Gap shown in the sensor quality report")
def tc22(owner, app, w, api):
    dispatched(app, w)
    for m in (45, 40, 35, 5, 0):
        reading(app, w, "s1", m, 5.0)
    gaps, longest = app.execute("SELECT gaps, longest_gap_minutes FROM v_report_sensor_quality WHERE serial_number = 'S1'"
                                ).fetchone()
    assert (gaps, longest) == (1, 30)
    return f"v_report_sensor_quality for S1: gaps={gaps}, longest_gap_minutes={longest}"


@case("TC23", "Monitoring", "Original reading values are protected",
      "UPDATE the temperature of a stored reading; DELETE it; UPDATE only its quality flag",
      "Value change and delete rejected by trigger; quality flag change allowed")
def tc23(owner, app, w, api):
    dispatched(app, w)
    rid = reading(owner, w, "s1", 30, 5.0)
    e1 = expect_error(owner, "UPDATE sensor_reading SET temperature = 4 WHERE reading_id = %s", [rid])
    e2 = expect_error(owner, "DELETE FROM sensor_reading WHERE reading_id = %s", [rid])
    owner.execute("UPDATE sensor_reading SET quality_status = 'suspicious' WHERE reading_id = %s", [rid])
    t = one(owner, "SELECT temperature FROM sensor_reading WHERE reading_id = %s", [rid])
    return f"UPDATE value -> {e1}. DELETE -> {e2}. Quality flag update -> allowed; temperature still {t}"


@case("TC24", "Incident", "Trace affected batches", "Reading 10.1 °C on a shipment carrying vaccine (2-8 °C) and syrup (2-25 °C)",
      "Only the batches whose own limits were breached are linked")
def tc24(owner, app, w, api):
    dispatched(app, w)
    reading(app, w, "s1", 25, 10.1)
    linked = [r[0] for r in app.execute("SELECT b.batch_number FROM incident_batch ib JOIN batch b USING (batch_id)")]
    assert linked == ["B1"]
    return f"Linked batches: {linked} (B3 syrup, limit 25 °C, correctly not linked)"


@case("TC25", "Security", "Login with a wrong password", "POST /api/auth/login with a valid email and a wrong password",
      "401 Unauthorized; no token issued")
def tc25(owner, app, w, api):
    r = api.post("/api/auth/login", data={"username": "operator@test.local", "password": "wrong"})
    assert r.status_code == 401 and "access_token" not in r.json()
    good = api.post("/api/auth/login", data={"username": "operator@test.local", "password": PASSWORD})
    return f"Wrong password -> HTTP {r.status_code} {r.json()}. Correct password -> HTTP {good.status_code} with a token"


def token(api, role):
    r = api.post("/api/auth/login", data={"username": f"{role}@test.local", "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@case("TC26", "Security", "Unauthorised status change rejected (API and database)",
      "Operator calls POST /api/batches/B1/status 'released'; operator context runs the UPDATE directly in SQL",
      "Rejected by the API (403) and by the database trigger")
def tc26(owner, app, w, api):
    r = api.post(f"/api/batches/{w['b1']}/status", json={"status": "released", "reason": "try"}, headers=token(api, "operator"))
    as_staff(app, w["operator"])
    e = expect_error(app, "UPDATE batch SET batch_status = 'on_hold' WHERE batch_id = %s", [w["b1"]])
    assert r.status_code == 403
    return f"API -> HTTP {r.status_code} {r.json()}. Direct SQL -> {e}"


@case("TC27", "Security", "SQL injection attempt", "GET /api/batches?q=' OR 1=1 --", "Treated as plain text; no extra rows")
def tc27(owner, app, w, api):
    h = token(api, "operator")
    total = len(api.get("/api/batches", headers=h).json())
    r = api.get("/api/batches", params={"q": "' OR 1=1 --"}, headers=h)
    assert r.status_code == 200 and r.json() == []
    return f"All batches: {total} rows. Injection string -> HTTP {r.status_code}, {len(r.json())} rows (searched literally)"


@case("TC28", "Security", "Application role cannot delete readings or write the audit log",
      "As pharmatrace_app: DELETE FROM sensor_reading; INSERT INTO audit_log", "Permission denied")
def tc28(owner, app, w, api):
    reading(app, w, "s1", 5, 5.0)
    e1 = expect_error(app, "DELETE FROM sensor_reading")
    e2 = expect_error(app, "INSERT INTO audit_log (table_name, row_pk, action) VALUES ('x','1','INSERT')")
    return f"DELETE readings -> {e1}. INSERT audit_log -> {e2}"


def open_incident(app, w):
    sid = shipment(app, w, [("b1", 100), ("b2", 50)])
    app.execute("SELECT dispatch_shipment(%s, %s)", [sid, NOW - timedelta(minutes=50)])
    app.execute("INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) VALUES (%s,%s,11)",
                [w["s1"], NOW - timedelta(minutes=20)])
    iid = one(app, "SELECT incident_id FROM incident")
    as_staff(app, w["quality_manager"])
    iv = one(app, "INSERT INTO investigation (incident_id, assigned_to) VALUES (%s,%s) RETURNING investigation_id",
             [iid, w["investigator"]])
    return iid, iv


@case("TC29", "Investigation", "Complete an investigation", "Mark investigation completed without findings; then with findings",
      "Rejected without findings; with findings completed_at is recorded")
def tc29(owner, app, w, api):
    iid, iv = open_incident(app, w)
    e = expect_error(app, "UPDATE investigation SET investigation_status = 'completed', completed_at = now() "
                          "WHERE investigation_id = %s", [iv])
    app.execute("UPDATE investigation SET investigation_status = 'completed', completed_at = now(), "
                "findings = 'Door seal failed' WHERE investigation_id = %s", [iv])
    done = one(app, "SELECT completed_at IS NOT NULL FROM investigation WHERE investigation_id = %s", [iv])
    return f"Without findings -> {e}. With findings -> completed (completed_at recorded={done})"


@case("TC30", "Investigation", "Closing an incident too early is refused",
      "Resolve the incident, then close it while a corrective action is pending (and batches unassessed)",
      "Rejected with the reason shown")
def tc30(owner, app, w, api):
    iid, iv = open_incident(app, w)
    app.execute("INSERT INTO corrective_action (investigation_id, assigned_to, action_description) VALUES (%s,%s,'Fix seal')",
                [iv, w["operator"]])
    app.execute("UPDATE investigation SET investigation_status = 'completed', completed_at = now(), findings = 'x' "
                "WHERE investigation_id = %s", [iv])
    app.execute("UPDATE incident SET incident_status = 'resolved' WHERE incident_id = %s", [iid])
    e1 = expect_error(app, "UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [iid])
    app.execute("UPDATE corrective_action SET action_status = 'completed', completed_at = now()")
    e2 = expect_error(app, "UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [iid])
    return f"With a pending action -> {e1}. With the action done but batches unassessed -> {e2}"


@case("TC31", "Investigation", "Close a fully resolved incident",
      "All work done; investigator tries to close; quality manager closes", "Only the QM can close; status closed; audit entry")
def tc31(owner, app, w, api):
    iid, iv = open_incident(app, w)
    app.execute("UPDATE incident_batch SET assessment_status = 'assessed', assessment_note = 'Stable'")
    app.execute("UPDATE investigation SET investigation_status = 'completed', completed_at = now(), findings = 'x' "
                "WHERE investigation_id = %s", [iv])
    app.execute("UPDATE incident SET incident_status = 'resolved' WHERE incident_id = %s", [iid])
    as_staff(app, w["investigator"])
    e = expect_error(app, "UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [iid])
    as_staff(app, w["quality_manager"])
    app.execute("UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [iid])
    by, st = app.execute("SELECT s.staff_name, a.new_data->>'incident_status' FROM audit_log a "
                         "JOIN staff s ON s.staff_id = a.changed_by "
                         "WHERE a.table_name = 'incident' ORDER BY a.audit_id DESC LIMIT 1").fetchone()
    assert st == "closed"
    return f"Investigator -> {e}. Quality manager -> closed. Latest audit entry: incident_status={st}, changed_by={by}"


@case("TC32", "Reports", "Dashboard counts match base tables", "Compare v_dashboard with direct COUNT queries",
      "Every dashboard number equals the matching SQL count")
def tc32(owner, app, w, api):
    open_incident(app, w)
    d = app.execute("SELECT active_shipments, open_incidents, batches_under_investigation FROM v_dashboard").fetchone()
    direct = (one(app, "SELECT COUNT(*) FROM shipment WHERE shipment_status = 'in_transit'"),
              one(app, "SELECT COUNT(*) FROM incident WHERE incident_status IN ('open','investigating')"),
              one(app, "SELECT COUNT(DISTINCT batch_id) FROM incident_batch"))
    assert tuple(d) == direct
    return f"v_dashboard (active shipments, open incidents, batches under investigation) = {tuple(d)}; direct counts = {direct}"


@case("TC33", "Reports", "Incident report totals match", "SUM of v_report_incidents_by_type_severity vs COUNT(*) FROM incident",
      "Report total equals the table count")
def tc33(owner, app, w, api):
    open_incident(app, w)
    rep = one(app, "SELECT SUM(incidents) FROM v_report_incidents_by_type_severity")
    cnt = one(app, "SELECT COUNT(*) FROM incident")
    assert rep == cnt
    return f"Report total={rep}; COUNT(*) FROM incident={cnt}"


@case("TC34", "Forms", "Required-field and range validation",
      "POST /api/shipments without destination; POST /api/products with min 8 > max 2",
      "422 with a message naming the problem; nothing saved")
def tc34(owner, app, w, api):
    h = token(api, "operator")
    r1 = api.post("/api/shipments", json={"vehicle_id": w["van"], "origin_facility_id": w["wh"]}, headers=h)
    r2 = api.post("/api/products", json={"product_name": "X1", "product_type": "vaccine", "min_temp": 8, "max_temp": 2},
                  headers=h)
    missing = [e["loc"][-1] for e in r1.json()["detail"]]
    msg2 = r2.json()["detail"][0]["msg"]
    n = one(app, "SELECT COUNT(*) FROM shipment")
    assert r1.status_code == 422 and r2.status_code == 422 and "destination_facility_id" in missing and n == 0
    return (f"Shipment -> HTTP {r1.status_code}, missing fields {missing}. "
            f"Product -> HTTP {r2.status_code}, '{msg2}'. Shipments saved: {n}")


# ---------------------------------------------------------------------------------------------- runner
def main():
    from app.main import app as fastapi_app

    print(f"Building {DB}")
    create_roles_and_db(DB)
    apply_schema(DB)
    owner, app = connect("owner"), connect("app")
    app_db._pool = ConnectionPool(s.url("pharmatrace_app", s.pg_app_password, DB), min_size=1, max_size=4,
                                  kwargs={"row_factory": dict_row}, open=True)
    results = []
    with TestClient(fastapi_app) as api:
        for tc, module, title, action, expected, fn in CASES:
            w = fresh_world(owner)
            app.execute("SELECT set_config('app.current_staff_id', '', false)")
            try:
                actual, status = fn(owner, app, w, api), "Pass"
            except AssertionError as e:
                actual, status = f"Check failed: {e}", "Fail"
            except Exception as e:  # noqa: BLE001 - record any unexpected error as a failure
                actual, status = f"Unexpected {type(e).__name__}: {e}", "Fail"
            results.append({"tc": tc, "module": module, "title": title, "action": action, "expected": expected,
                            "actual": actual, "status": status})
            print(f"{tc} {status}  {title}")
    app_db.close_pool()
    owner.close()
    app.close()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "test_evidence.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# Test evidence: actual system responses ({datetime.now():%Y-%m-%d %H:%M})", "",
          f"Generated by `backend/scripts/evidence.py` on a fresh database `{DB}` (PostgreSQL 18). Each case starts from the "
          "same small data set. The Actual result column is the system's real output.", "",
          f"**{sum(r['status'] == 'Pass' for r in results)} of {len(results)} test cases passed.**", "",
          "| TC | Module | Test | Input / action | Expected | Actual result (system output) | Status |",
          "|---|---|---|---|---|---|---|"]
    for r in results:
        cells = [r[k].replace("|", "\\|").replace("\n", " ") for k in ("tc", "module", "title", "action", "expected", "actual",
                                                                        "status")]
        md.append("| " + " | ".join(cells) + " |")
    (OUT / "test_evidence.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'test_evidence.md'}")


if __name__ == "__main__":
    main()
