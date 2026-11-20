"""TC17-TC24: reading classification, excursion detection and tracing."""

from datetime import timedelta

import pytest
from psycopg import errors

from tests.conftest import NOW, make_shipment, one


def read(conn, sensor, minutes_ago, temp):
    return one(conn, "INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) VALUES (%s,%s,%s) "
                     "RETURNING reading_id", [sensor, NOW - timedelta(minutes=minutes_ago), temp])


@pytest.fixture
def in_transit(app_db, world):
    """Shipment carrying vaccine (2-8 °C) and syrup (2-25 °C), monitored by S1, dispatched."""
    sid = make_shipment(app_db, world, [("b1", 100), ("b3", 50)])
    app_db.execute("SELECT dispatch_shipment(%s, %s)", [sid, NOW - timedelta(minutes=50)])
    return sid


def test_tc17_valid_reading_in_range_no_incident(app_db, world, in_transit):
    rid = read(app_db, world["s1"], 30, 5.2)
    assert one(app_db, "SELECT quality_status FROM sensor_reading WHERE reading_id = %s", [rid]) == "valid"
    assert one(app_db, "SELECT COUNT(*) FROM incident") == 0


def test_tc18_out_of_limit_reading_creates_incident(app_db, world, in_transit):
    read(app_db, world["s1"], 30, 5.2)
    rid = read(app_db, world["s1"], 25, 8.6)
    inc = app_db.execute("SELECT incident_id, incident_type, shipment_id, detection_source, incident_status, severity "
                         "FROM incident").fetchall()
    assert len(inc) == 1
    incident_id, itype, ship, source, status, severity = inc[0]
    assert (itype, ship, source, status, severity) == ("temperature_excursion", in_transit, "automatic", "open", "low")
    assert one(app_db, "SELECT COUNT(*) FROM incident_reading WHERE incident_id = %s AND reading_id = %s",
               [incident_id, rid]) == 1


def test_tc24_only_breached_batches_are_linked(app_db, world, in_transit):
    read(app_db, world["s1"], 25, 10.1)          # breaches vaccine (max 8) but not syrup (max 25)
    linked = [r[0] for r in app_db.execute("SELECT batch_id FROM incident_batch")]
    assert linked == [world["b1"]]


def test_tc19_repeated_breach_appends_and_escalates(app_db, world, in_transit):
    read(app_db, world["s1"], 25, 8.6)            # 0.6 over -> low
    read(app_db, world["s1"], 20, 12.5)           # 4.5 over -> high
    assert one(app_db, "SELECT COUNT(*) FROM incident") == 1
    assert one(app_db, "SELECT severity FROM incident") == "high"
    assert one(app_db, "SELECT COUNT(*) FROM incident_reading") == 2


def test_recovery_sets_end_time_and_new_breach_reopens_window(app_db, world, in_transit):
    read(app_db, world["s1"], 25, 9.0)
    read(app_db, world["s1"], 20, 6.0)
    assert one(app_db, "SELECT end_time FROM incident") == NOW - timedelta(minutes=20)
    assert one(app_db, "SELECT exposure_minutes FROM v_incident_exposure") == 5
    read(app_db, world["s1"], 15, 9.5)
    assert one(app_db, "SELECT end_time FROM incident") is None


def test_tc20_duplicate_reading_rejected(app_db, world, in_transit):
    read(app_db, world["s1"], 30, 5.0)
    with pytest.raises(errors.UniqueViolation):
        read(app_db, world["s1"], 30, 5.0)


def test_tc21_future_timestamp_stored_as_invalid_without_incident(app_db, world, in_transit):
    rid = one(app_db, "INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) "
                      "VALUES (%s, now() + interval '2 hours', 20) RETURNING reading_id", [world["s1"]])
    assert one(app_db, "SELECT quality_status FROM sensor_reading WHERE reading_id = %s", [rid]) == "invalid"
    assert one(app_db, "SELECT COUNT(*) FROM incident") == 0


def test_implausible_value_kept_but_invalid(app_db, world, in_transit):
    rid = read(app_db, world["s1"], 10, 999)
    assert one(app_db, "SELECT (temperature, quality_status)::text FROM sensor_reading WHERE reading_id = %s",
               [rid]) == "(999.00,invalid)"
    assert one(app_db, "SELECT COUNT(*) FROM incident") == 0


def test_faulty_sensor_readings_are_suspicious(app_db, world):
    app_db.execute("UPDATE sensor SET installation_status = 'faulty' WHERE sensor_id = %s", [world["s3"]])
    rid = read(app_db, world["s3"], 5, 5.0)
    assert one(app_db, "SELECT quality_status FROM sensor_reading WHERE reading_id = %s", [rid]) == "suspicious"


def test_tc22_gap_appears_in_quality_report(app_db, world, in_transit):
    for minutes in (45, 40, 35, 5, 0):            # 30-minute hole between 35 and 5
        read(app_db, world["s1"], minutes, 5.0)
    row = app_db.execute("SELECT gaps, longest_gap_minutes FROM v_report_sensor_quality WHERE serial_number = 'S1'"
                         ).fetchone()
    assert row == (1, 30)


def test_tc23_original_reading_values_are_protected(owner, world, in_transit):
    rid = read(owner, world["s1"], 30, 5.0)
    with pytest.raises(errors.RaiseException, match="cannot be changed"):
        owner.execute("UPDATE sensor_reading SET temperature = 4 WHERE reading_id = %s", [rid])
    with pytest.raises(errors.RaiseException, match="cannot be deleted"):
        owner.execute("DELETE FROM sensor_reading WHERE reading_id = %s", [rid])
    owner.execute("UPDATE sensor_reading SET quality_status = 'suspicious' WHERE reading_id = %s", [rid])


def test_facility_excursion_uses_stock_at_that_time(app_db, world):
    app_db.execute("INSERT INTO sensor_assignment (sensor_id, facility_id, assigned_at) VALUES (%s,%s,%s)",
                   [world["s2"], world["wh"], NOW - timedelta(days=3)])
    read(app_db, world["s2"], 10, 30.0)           # breaches every product stored at the warehouse
    assert one(app_db, "SELECT facility_id FROM incident") == world["wh"]
    assert one(app_db, "SELECT COUNT(*) FROM incident_batch") == 5


def test_reading_from_unassigned_sensor_is_stored_only(app_db, world):
    read(app_db, world["s3"], 5, 30.0)
    assert one(app_db, "SELECT COUNT(*) FROM incident") == 0
