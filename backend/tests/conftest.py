"""Test fixtures: a separate pharmatrace_test database rebuilt once per run, emptied before each test."""

from datetime import UTC, date, datetime, timedelta

import psycopg
import pytest

from app.config import get_settings
from scripts.reset_db import apply_schema, create_roles_and_db

TEST_DB = "pharmatrace_test"
TABLES = ("audit_log, corrective_action, investigation, incident_batch, incident_reading, incident, "
          "sensor_reading, sensor_assignment, sensor, batch_movement, shipment_checkpoint, shipment_batch, "
          "shipment, vehicle, facility_phone, facility, batch, product, staff")


@pytest.fixture(scope="session")
def test_db():
    create_roles_and_db(TEST_DB)
    apply_schema(TEST_DB)
    return TEST_DB


def _connect(role: str, autocommit=True):
    s = get_settings()
    password = s.pg_owner_password if role == "owner" else s.pg_app_password
    return psycopg.connect(s.url(f"pharmatrace_{role}", password, TEST_DB), autocommit=autocommit)


@pytest.fixture
def owner(test_db):
    conn = _connect("owner")
    conn.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    yield conn
    conn.close()


@pytest.fixture
def app_db(owner):
    """A connection as the least-privileged application role (autocommit)."""
    conn = _connect("app")
    yield conn
    conn.close()


@pytest.fixture
def connect():
    """Factory for extra connections (concurrency tests)."""
    opened = []

    def make(role="app", autocommit=False):
        c = _connect(role, autocommit)
        opened.append(c)
        return c

    yield make
    for c in opened:
        c.close()


def as_staff(conn, staff_id):
    conn.execute("SELECT set_config('app.current_staff_id', %s, false)", [str(staff_id)])


def one(conn, query, params=()):
    return conn.execute(query, params).fetchone()[0]


NOW = datetime.now(UTC).replace(microsecond=0)


@pytest.fixture
def world(owner):
    """Minimal consistent data set shared by most tests."""
    w = {}
    for role in ("operator", "investigator", "quality_manager", "admin"):
        w[role] = one(owner, "INSERT INTO staff (staff_name, email, password_hash, role) VALUES (%s,%s,'x',%s) "
                             "RETURNING staff_id", [role.title(), f"{role}@test.local", role])
    w["vaccine"] = one(owner, "INSERT INTO product (product_name, product_type, min_temp, max_temp) "
                              "VALUES ('Vaccine A','vaccine',2,8) RETURNING product_id")
    w["syrup"] = one(owner, "INSERT INTO product (product_name, product_type, min_temp, max_temp) "
                            "VALUES ('Syrup E','medicine',2,25) RETURNING product_id")
    w["tablet"] = one(owner, "INSERT INTO product (product_name, product_type, min_temp, max_temp) "
                             "VALUES ('Tablet D','medicine',15,25) RETURNING product_id")
    for key, name in (("wh", "Warehouse"), ("dc", "Distribution Centre"), ("hosp", "Hospital")):
        w[key] = one(owner, "INSERT INTO facility (facility_name, facility_type, street, city, pincode) "
                            "VALUES (%s,'warehouse','1 Road','Bengaluru','560001') RETURNING facility_id", [name])
    w["van"] = one(owner, "INSERT INTO vehicle (registration_number, vehicle_type) "
                          "VALUES ('KA01AA0001','refrigerated_van') RETURNING vehicle_id")
    for key, product, qty, expiry in (("b1", "vaccine", 1000, date(2030, 1, 1)), ("b2", "vaccine", 500, date(2030, 1, 1)),
                                      ("b3", "syrup", 300, date(2030, 1, 1)), ("b4", "tablet", 200, date(2030, 1, 1)),
                                      ("bexp", "vaccine", 100, date.today() - timedelta(days=1))):
        w[key] = one(owner, "INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity) "
                            "VALUES (%s,%s,%s,%s,%s) RETURNING batch_id",
                     [key.upper(), w[product], date(2024, 1, 1), expiry, qty])
        owner.execute("INSERT INTO batch_movement (batch_id, facility_id, movement_type, movement_time, quantity_moved) "
                      "VALUES (%s,%s,'received',%s,%s)", [w[key], w["wh"], NOW - timedelta(days=2), qty])
    for i in (1, 2, 3):
        w[f"s{i}"] = one(owner, "INSERT INTO sensor (serial_number, sensor_type) VALUES (%s,'temperature') "
                                "RETURNING sensor_id", [f"S{i}"])
    return w


def make_shipment(conn, w, lines, sensor="s1", origin="wh", dest="dc"):
    sid = one(conn, "INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival) "
                    "VALUES (%s,%s,%s,%s) RETURNING shipment_id", [w["van"], w[origin], w[dest], NOW + timedelta(hours=6)])
    for batch, qty in lines:
        conn.execute("INSERT INTO shipment_batch VALUES (%s,%s,%s)", [sid, w[batch], qty])
    if sensor:
        conn.execute("INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (%s,%s,%s)",
                     [w[sensor], sid, NOW - timedelta(hours=1)])
    return sid
