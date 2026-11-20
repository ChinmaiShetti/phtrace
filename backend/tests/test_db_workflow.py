"""TC26 and TC29-TC33: role rules, the investigation workflow, dashboard and reports."""

from datetime import timedelta

import pytest
from psycopg import errors

from tests.conftest import NOW, as_staff, make_shipment, one


@pytest.fixture
def incident(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 100), ("b2", 50)])
    app_db.execute("SELECT dispatch_shipment(%s, %s)", [sid, NOW - timedelta(minutes=50)])
    app_db.execute("INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) VALUES (%s,%s,11)",
                   [world["s1"], NOW - timedelta(minutes=20)])
    return one(app_db, "SELECT incident_id FROM incident")


def assign(conn, world, incident_id):
    as_staff(conn, world["quality_manager"])
    return one(conn, "INSERT INTO investigation (incident_id, assigned_to) VALUES (%s,%s) RETURNING investigation_id",
               [incident_id, world["investigator"]])


def test_tc26_operator_cannot_release_batch(app_db, world):
    as_staff(app_db, world["operator"])
    with pytest.raises(errors.InsufficientPrivilege, match="Role operator may not change batch"):
        app_db.execute("UPDATE batch SET batch_status = 'on_hold' WHERE batch_id = %s", [world["b1"]])


def test_status_change_needs_staff_context(app_db, world):
    with pytest.raises(errors.RaiseException, match="authenticated staff"):
        app_db.execute("UPDATE batch SET batch_status = 'on_hold' WHERE batch_id = %s", [world["b1"]])


def test_investigator_may_hold_but_not_release(app_db, world):
    as_staff(app_db, world["investigator"])
    app_db.execute("UPDATE batch SET batch_status = 'on_hold' WHERE batch_id = %s", [world["b1"]])
    with pytest.raises(errors.InsufficientPrivilege):
        app_db.execute("UPDATE batch SET batch_status = 'released' WHERE batch_id = %s", [world["b1"]])
    as_staff(app_db, world["quality_manager"])
    app_db.execute("UPDATE batch SET batch_status = 'released' WHERE batch_id = %s", [world["b1"]])


def test_disposed_is_terminal(app_db, world):
    as_staff(app_db, world["quality_manager"])
    app_db.execute("UPDATE batch SET batch_status = 'quarantined' WHERE batch_id = %s", [world["b1"]])
    app_db.execute("UPDATE batch SET batch_status = 'disposed' WHERE batch_id = %s", [world["b1"]])
    with pytest.raises(errors.InsufficientPrivilege):
        app_db.execute("UPDATE batch SET batch_status = 'available' WHERE batch_id = %s", [world["b1"]])


def test_assigning_investigation_moves_incident_to_investigating(app_db, world, incident):
    assign(app_db, world, incident)
    assert one(app_db, "SELECT incident_status FROM incident") == "investigating"


def test_operator_cannot_be_assigned_investigation(app_db, world, incident):
    with pytest.raises(errors.RaiseException, match="cannot be assigned"):
        app_db.execute("INSERT INTO investigation (incident_id, assigned_to) VALUES (%s,%s)",
                       [incident, world["operator"]])


def test_tc29_complete_investigation_requires_findings(app_db, world, incident):
    iv = assign(app_db, world, incident)
    with pytest.raises(errors.CheckViolation):
        app_db.execute("UPDATE investigation SET investigation_status = 'completed', completed_at = now() "
                       "WHERE investigation_id = %s", [iv])
    app_db.execute("UPDATE investigation SET investigation_status = 'completed', completed_at = now(), "
                   "findings = 'Door seal failure' WHERE investigation_id = %s", [iv])
    app_db.execute("UPDATE incident SET incident_status = 'resolved' WHERE incident_id = %s", [incident])


def test_cannot_resolve_with_open_investigation(app_db, world, incident):
    assign(app_db, world, incident)
    with pytest.raises(errors.RaiseException, match="not completed"):
        app_db.execute("UPDATE incident SET incident_status = 'resolved' WHERE incident_id = %s", [incident])


def test_tc30_cannot_close_with_pending_action_or_unassessed_batch(app_db, world, incident):
    iv = assign(app_db, world, incident)
    app_db.execute("INSERT INTO corrective_action (investigation_id, assigned_to, action_description) "
                   "VALUES (%s,%s,'Fix seal')", [iv, world["operator"]])
    app_db.execute("UPDATE investigation SET investigation_status = 'completed', completed_at = now(), findings = 'x' "
                   "WHERE investigation_id = %s", [iv])
    app_db.execute("UPDATE incident SET incident_status = 'resolved' WHERE incident_id = %s", [incident])
    with pytest.raises(errors.RaiseException, match="corrective actions that are not finished"):
        app_db.execute("UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [incident])
    app_db.execute("UPDATE corrective_action SET action_status = 'completed', completed_at = now()")
    with pytest.raises(errors.RaiseException, match="not assessed"):
        app_db.execute("UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [incident])


def test_tc31_close_fully_resolved_incident(app_db, world, incident):
    iv = assign(app_db, world, incident)
    app_db.execute("UPDATE incident_batch SET assessment_status = 'assessed', assessment_note = 'Stable'")
    app_db.execute("UPDATE investigation SET investigation_status = 'completed', completed_at = now(), findings = 'x' "
                   "WHERE investigation_id = %s", [iv])
    app_db.execute("UPDATE incident SET incident_status = 'resolved' WHERE incident_id = %s", [incident])
    as_staff(app_db, world["investigator"])
    with pytest.raises(errors.InsufficientPrivilege, match="Only a quality manager"):
        app_db.execute("UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [incident])
    as_staff(app_db, world["quality_manager"])
    app_db.execute("UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [incident])
    row = app_db.execute("SELECT changed_by, new_data->>'incident_status' FROM audit_log "
                         "WHERE table_name = 'incident' ORDER BY audit_id DESC LIMIT 1").fetchone()
    assert row == (world["quality_manager"], "closed")


def test_incident_cannot_skip_states(app_db, world, incident):
    with pytest.raises(errors.RaiseException, match="cannot move from open to closed"):
        app_db.execute("UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [incident])


def test_tc32_dashboard_matches_base_tables(app_db, world, incident):
    assign(app_db, world, incident)
    d = app_db.execute("SELECT active_shipments, open_incidents, batches_under_investigation FROM v_dashboard").fetchone()
    assert d == (
        one(app_db, "SELECT COUNT(*) FROM shipment WHERE shipment_status = 'in_transit'"),
        one(app_db, "SELECT COUNT(*) FROM incident WHERE incident_status IN ('open','investigating')"),
        one(app_db, "SELECT COUNT(DISTINCT batch_id) FROM incident_batch"),
    )
    assert d == (1, 1, 2)


def test_tc33_incident_report_totals_match(app_db, world, incident):
    report_total = one(app_db, "SELECT SUM(incidents) FROM v_report_incidents_by_type_severity")
    assert report_total == one(app_db, "SELECT COUNT(*) FROM incident") == 1


def test_audit_log_never_stores_password_hash(owner, world):
    assert one(owner, "SELECT COUNT(*) FROM audit_log WHERE table_name = 'staff' AND new_data ? 'password_hash'") == 0
    assert one(owner, "SELECT COUNT(*) FROM audit_log WHERE table_name = 'staff'") == 4


def test_related_shipments_same_vehicle(app_db, world, incident):
    other = make_shipment(app_db, world, [("b2", 10)], sensor="s2")
    app_db.execute("SELECT dispatch_shipment(%s, %s)", [other, NOW - timedelta(minutes=40)])
    rows = app_db.execute("SELECT shipment_id, reason FROM related_shipments(%s)", [incident]).fetchall()
    assert rows == [(other, "same vehicle")]
