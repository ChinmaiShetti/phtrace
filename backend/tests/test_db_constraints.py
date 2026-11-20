"""TC01-TC10 and related: keys, constraints and validation enforced by the database."""

from datetime import date

import psycopg
import pytest
from psycopg import errors

from tests.conftest import NOW, make_shipment, one


def test_tc01_valid_product_saved(app_db):
    pid = one(app_db, "INSERT INTO product (product_name, product_type, min_temp, max_temp) "
                      "VALUES ('New Vaccine','vaccine',2.00,8.00) RETURNING product_id")
    assert pid > 0


def test_tc02_invalid_temperature_range_rejected(app_db):
    with pytest.raises(errors.CheckViolation, match="product_temp_range"):
        app_db.execute("INSERT INTO product (product_name, product_type, min_temp, max_temp) VALUES ('Bad','vaccine',8,2)")


def test_humidity_limits_must_come_in_pairs(app_db):
    with pytest.raises(errors.CheckViolation, match="product_humidity_pair"):
        app_db.execute("INSERT INTO product (product_name, product_type, min_temp, max_temp, min_humidity) "
                       "VALUES ('Half','medicine',15,25,30)")


def test_tc03_duplicate_batch_number_rejected(app_db, world):
    with pytest.raises(errors.UniqueViolation):
        app_db.execute("INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
                       "VALUES ('B1',%s,'2025-01-01','2027-01-01',10)", [world["vaccine"]])


def test_tc04_expiry_before_manufacture_rejected(app_db, world):
    with pytest.raises(errors.CheckViolation, match="batch_dates"):
        app_db.execute("INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
                       "VALUES ('X1',%s,'2026-05-01','2026-04-01',10)", [world["vaccine"]])


def test_tc05_quantity_boundary(app_db, world):
    sql = ("INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
           "VALUES (%s,%s,'2025-01-01','2027-01-01',%s)")
    with pytest.raises(errors.CheckViolation):
        app_db.execute(sql, ["Q0", world["vaccine"], 0])
    app_db.execute(sql, ["Q1", world["vaccine"], 1])


def test_tc06_product_with_batches_cannot_be_deleted(owner, world):
    with pytest.raises(errors.RestrictViolation):   # ON DELETE RESTRICT
        owner.execute("DELETE FROM product WHERE product_id = %s", [world["vaccine"]])


def test_tc07_nonexistent_vehicle_rejected(app_db, world):
    with pytest.raises(errors.ForeignKeyViolation):
        app_db.execute("INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival) "
                       "VALUES (999,%s,%s,now())", [world["wh"], world["dc"]])


def test_tc08_same_origin_and_destination_rejected(app_db, world):
    with pytest.raises(errors.CheckViolation, match="shipment_route"):
        app_db.execute("INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival) "
                       "VALUES (%s,%s,%s,now())", [world["van"], world["wh"], world["wh"]])


def test_tc09_add_batch_to_shipment(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 1000)])
    assert one(app_db, "SELECT quantity_shipped FROM shipment_batch WHERE shipment_id = %s", [sid]) == 1000


def test_tc10_same_batch_twice_rejected(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 100)])
    with pytest.raises(errors.UniqueViolation):
        app_db.execute("INSERT INTO shipment_batch VALUES (%s,%s,50)", [sid, world["b1"]])


def test_incompatible_storage_ranges_rejected(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 100)])          # vaccine 2-8 °C
    with pytest.raises(errors.RaiseException, match="does not overlap"):
        app_db.execute("INSERT INTO shipment_batch VALUES (%s,%s,10)", [sid, world["b4"]])   # tablet 15-25 °C
    app_db.execute("INSERT INTO shipment_batch VALUES (%s,%s,10)", [sid, world["b3"]])       # syrup 2-25 °C overlaps


def test_status_and_timestamps_must_agree(app_db, world):
    with pytest.raises(errors.CheckViolation, match="shipment_status_times"):
        app_db.execute("INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival, "
                       "shipment_status) VALUES (%s,%s,%s,now(),'in_transit')", [world["van"], world["wh"], world["dc"]])


def test_tc16_overlapping_sensor_assignment_rejected(app_db, world):
    s1 = make_shipment(app_db, world, [("b1", 10)], sensor="s1")
    s2 = make_shipment(app_db, world, [("b2", 10)], sensor=None)
    with pytest.raises(errors.ExclusionViolation):
        app_db.execute("INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (%s,%s,%s)",
                       [world["s1"], s2, NOW])
    assert s1 != s2


def test_assignment_needs_exactly_one_target(app_db, world):
    with pytest.raises(errors.CheckViolation, match="assignment_one_target"):
        app_db.execute("INSERT INTO sensor_assignment (sensor_id, assigned_at) VALUES (%s, now())", [world["s1"]])


def test_tc28_app_role_cannot_delete_readings_or_audit(app_db, world):
    app_db.execute("INSERT INTO sensor_reading (sensor_id, recorded_at, temperature) VALUES (%s, now(), 5)", [world["s1"]])
    with pytest.raises(errors.InsufficientPrivilege):
        app_db.execute("DELETE FROM sensor_reading")
    with pytest.raises(errors.InsufficientPrivilege):
        app_db.execute("INSERT INTO audit_log (table_name, row_pk, action) VALUES ('x','1','INSERT')")
    with pytest.raises(errors.InsufficientPrivilege):
        app_db.execute("UPDATE sensor_reading SET temperature = 1")


def test_pincode_format(app_db):
    with pytest.raises(errors.CheckViolation):
        app_db.execute("INSERT INTO facility (facility_name, facility_type, street, city, pincode) "
                       "VALUES ('F','clinic','s','c','12ab')")


def test_unique_email_case_insensitive(app_db, world):
    with pytest.raises(errors.UniqueViolation):
        app_db.execute("INSERT INTO staff (staff_name, email, password_hash, role) "
                       "VALUES ('Dup','OPERATOR@test.local','x','operator')")


def test_check_constraints_use_dates(app_db, world):
    # boundary: expiry one day after manufacture is allowed
    app_db.execute("INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
                   "VALUES ('EDGE',%s,%s,%s,1)", [world["vaccine"], date(2026, 1, 1), date(2026, 1, 2)])
    assert isinstance(app_db, psycopg.Connection)
