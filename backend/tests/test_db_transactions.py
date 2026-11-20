"""TC11-TC15: dispatch and receive transactions, rollback and concurrency."""

import threading
import time

import pytest
from psycopg import errors

from tests.conftest import as_staff, make_shipment, one


def stock(conn, batch, facility):
    return one(conn, "SELECT batch_stock_at(%s, %s)", [batch, facility])


def test_tc11_dispatch_records_movements_checkpoint_and_status(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 400), ("b2", 100)])
    app_db.execute("SELECT dispatch_shipment(%s)", [sid])
    assert one(app_db, "SELECT shipment_status FROM shipment WHERE shipment_id = %s", [sid]) == "in_transit"
    assert one(app_db, "SELECT COUNT(*) FROM batch_movement WHERE shipment_id = %s AND movement_type = 'dispatched'",
               [sid]) == 2
    assert one(app_db, "SELECT event_type FROM shipment_checkpoint WHERE shipment_id = %s", [sid]) == "departure"
    assert stock(app_db, world["b1"], world["wh"]) == 600


def test_tc12_partial_failure_rolls_back_everything(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 100), ("b2", 9999)])   # b2 has only 500 in stock
    with pytest.raises(errors.RaiseException, match="Insufficient stock of batch B2"):
        app_db.execute("SELECT dispatch_shipment(%s)", [sid])
    # b1 was processed first, but its movement must not survive the failed call
    assert one(app_db, "SELECT COUNT(*) FROM batch_movement WHERE shipment_id = %s", [sid]) == 0
    assert one(app_db, "SELECT shipment_status FROM shipment WHERE shipment_id = %s", [sid]) == "planned"
    assert stock(app_db, world["b1"], world["wh"]) == 1000


def test_tc13_expired_batch_cannot_be_dispatched(app_db, world):
    sid = make_shipment(app_db, world, [("bexp", 10)])
    with pytest.raises(errors.RaiseException, match="expired"):
        app_db.execute("SELECT dispatch_shipment(%s)", [sid])


def test_tc13_quarantined_batch_cannot_be_dispatched(app_db, world):
    as_staff(app_db, world["quality_manager"])
    app_db.execute("UPDATE batch SET batch_status = 'quarantined' WHERE batch_id = %s", [world["b1"]])
    sid = make_shipment(app_db, world, [("b1", 10)])
    with pytest.raises(errors.RaiseException, match="quarantined"):
        app_db.execute("SELECT dispatch_shipment(%s)", [sid])


def test_dispatch_requires_sensor(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 10)], sensor=None)
    with pytest.raises(errors.RaiseException, match="no active monitoring sensor"):
        app_db.execute("SELECT dispatch_shipment(%s)", [sid])


def test_dispatch_blocked_for_faulty_vehicle(app_db, world):
    app_db.execute("UPDATE vehicle SET refrigeration_status = 'faulty'")
    sid = make_shipment(app_db, world, [("b1", 10)])
    with pytest.raises(errors.RaiseException, match="faulty"):
        app_db.execute("SELECT dispatch_shipment(%s)", [sid])


def test_lines_frozen_after_dispatch(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 10)])
    app_db.execute("SELECT dispatch_shipment(%s)", [sid])
    with pytest.raises(errors.RaiseException, match="only be changed while it is planned"):
        app_db.execute("INSERT INTO shipment_batch VALUES (%s,%s,5)", [sid, world["b2"]])


def test_tc14_concurrent_dispatches_cannot_oversell(world, connect):
    """Two sessions each dispatch 800 of the 1000 units of B1. One must fail; stock never goes negative."""
    setup = connect("app", autocommit=True)
    a = make_shipment(setup, world, [("b1", 800)], sensor="s1")
    b = make_shipment(setup, world, [("b1", 800)], sensor="s2")

    first, second = connect(), connect()
    first.execute("SELECT dispatch_shipment(%s)", [a])        # holds the lock on B1, not yet committed
    outcome = {}

    def run_second():
        try:
            second.execute("SELECT dispatch_shipment(%s)", [b])
            second.commit()
            outcome["ok"] = True
        except Exception as exc:  # noqa: BLE001 - the error is the result under test
            second.rollback()
            outcome["error"] = str(exc)

    t = threading.Thread(target=run_second)
    t.start()
    time.sleep(0.5)
    assert t.is_alive(), "second dispatch should be waiting for the row lock"
    first.commit()
    t.join(10)

    assert "Insufficient stock" in outcome.get("error", "")
    assert one(setup, "SELECT batch_stock_at(%s, %s)", [world["b1"], world["wh"]]) == 200


def test_tc15_receive_moves_stock_and_closes_assignment(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 300)])
    app_db.execute("SELECT dispatch_shipment(%s)", [sid])
    app_db.execute("SELECT receive_shipment(%s)", [sid])
    assert one(app_db, "SELECT shipment_status FROM shipment WHERE shipment_id = %s", [sid]) == "delivered"
    assert stock(app_db, world["b1"], world["dc"]) == 300
    assert one(app_db, "SELECT COUNT(*) FROM sensor_assignment WHERE shipment_id = %s AND unassigned_at IS NULL",
               [sid]) == 0
    events = [r[0] for r in app_db.execute("SELECT event_kind FROM shipment_timeline(%s)", [sid])]
    assert "checkpoint:departure" in events and "checkpoint:arrival" in events


def test_receive_requires_in_transit(app_db, world):
    sid = make_shipment(app_db, world, [("b1", 10)])
    with pytest.raises(errors.RaiseException, match="only shipments in transit"):
        app_db.execute("SELECT receive_shipment(%s)", [sid])
