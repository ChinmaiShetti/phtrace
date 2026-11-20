"""Shipments: create, load batches, dispatch and receive (database transactions), checkpoints, timeline."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.auth import Db, require

router = APIRouter(prefix="/api/shipments", tags=["shipments"])
Operator = Depends(require("operator", "admin"))
Editor = Depends(require("operator", "quality_manager", "admin"))


class Line(BaseModel):
    batch_id: int
    quantity_shipped: int = Field(gt=0, le=10_000_000)


class ShipmentIn(BaseModel):
    vehicle_id: int
    origin_facility_id: int
    destination_facility_id: int
    expected_arrival: datetime
    lines: list[Line] = []
    sensor_id: int | None = Field(default=None, description="Monitoring sensor to attach now (optional)")

    @field_validator("expected_arrival")
    @classmethod
    def in_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        if v <= datetime.now(UTC):
            raise ValueError("Expected arrival must be in the future")
        return v


class CheckpointIn(BaseModel):
    event_type: Literal["transit_scan", "inspection", "delay"]
    location_description: str = Field(min_length=2, max_length=200)


@router.get("")
def list_shipments(db: Db, status: str | None = None):
    return db.execute("""SELECT * FROM v_shipment_summary WHERE (%(s)s::text IS NULL OR shipment_status = %(s)s)
                         ORDER BY (shipment_status = 'in_transit') DESC, COALESCE(dispatch_time, expected_arrival) DESC""",
                      {"s": status}).fetchall()


@router.post("", status_code=201, dependencies=[Editor])
def create_shipment(body: ShipmentIn, db: Db):
    """Shipment, its lines and its sensor assignment are created in one transaction."""
    row = db.execute("""INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival)
                        VALUES (%s, %s, %s, %s) RETURNING *""",
                     [body.vehicle_id, body.origin_facility_id, body.destination_facility_id,
                      body.expected_arrival]).fetchone()
    for line in body.lines:
        db.execute("INSERT INTO shipment_batch VALUES (%s, %s, %s)",
                   [row["shipment_id"], line.batch_id, line.quantity_shipped])
    if body.sensor_id:
        db.execute("INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (%s, %s, now())",
                   [body.sensor_id, row["shipment_id"]])
    return row


def _get(db, shipment_id: int):
    row = db.execute("SELECT * FROM v_shipment_summary WHERE shipment_id = %s", [shipment_id]).fetchone()
    if row is None:
        raise HTTPException(404, "Shipment not found")
    return row


@router.get("/{shipment_id}")
def get_shipment(shipment_id: int, db: Db):
    p = [shipment_id]
    return {
        "shipment": _get(db, shipment_id),
        "lines": db.execute("""SELECT sb.*, b.batch_number, b.batch_status, b.expiry_date, pr.product_name,
                                      pr.min_temp, pr.max_temp
                               FROM shipment_batch sb JOIN batch b USING (batch_id) JOIN product pr USING (product_id)
                               WHERE sb.shipment_id = %s ORDER BY b.batch_number""", p).fetchall(),
        "limits": db.execute("SELECT * FROM v_shipment_limits WHERE shipment_id = %s", p).fetchone(),
        "sensors": db.execute("""SELECT a.*, s.serial_number, s.sensor_type FROM sensor_assignment a
                                 JOIN sensor s USING (sensor_id) WHERE a.shipment_id = %s ORDER BY a.assigned_at""",
                              p).fetchall(),
        "checkpoints": db.execute("SELECT * FROM shipment_checkpoint WHERE shipment_id = %s ORDER BY checkpoint_no",
                                  p).fetchall(),
        "timeline": db.execute("SELECT * FROM shipment_timeline(%s)", p).fetchall(),
        "incidents": db.execute("""SELECT incident_id, incident_code, incident_type, severity, incident_status, detected_at
                                   FROM v_incident_summary WHERE shipment_id = %s ORDER BY detected_at DESC""",
                                p).fetchall(),
    }


@router.post("/{shipment_id}/batches", status_code=201, dependencies=[Editor])
def add_line(shipment_id: int, line: Line, db: Db):
    return db.execute("INSERT INTO shipment_batch VALUES (%s, %s, %s) RETURNING *",
                      [shipment_id, line.batch_id, line.quantity_shipped]).fetchone()


@router.delete("/{shipment_id}/batches/{batch_id}", status_code=204, dependencies=[Editor])
def remove_line(shipment_id: int, batch_id: int, db: Db):
    if db.execute("DELETE FROM shipment_batch WHERE shipment_id = %s AND batch_id = %s",
                  [shipment_id, batch_id]).rowcount == 0:
        raise HTTPException(404, "Line not found")


@router.post("/{shipment_id}/dispatch", dependencies=[Operator])
def dispatch(shipment_id: int, db: Db):
    db.execute("SELECT dispatch_shipment(%s)", [shipment_id])
    return _get(db, shipment_id)


@router.post("/{shipment_id}/receive", dependencies=[Operator])
def receive(shipment_id: int, db: Db):
    db.execute("SELECT receive_shipment(%s)", [shipment_id])
    return _get(db, shipment_id)


@router.post("/{shipment_id}/cancel", dependencies=[Operator])
def cancel(shipment_id: int, db: Db):
    row = db.execute("""UPDATE shipment SET shipment_status = 'cancelled'
                        WHERE shipment_id = %s AND shipment_status = 'planned' RETURNING shipment_id""",
                     [shipment_id]).fetchone()
    if row is None:
        raise HTTPException(409, "Only planned shipments can be cancelled")
    db.execute("UPDATE sensor_assignment SET unassigned_at = now() WHERE shipment_id = %s AND unassigned_at IS NULL",
               [shipment_id])
    return _get(db, shipment_id)


@router.post("/{shipment_id}/checkpoints", status_code=201, dependencies=[Operator])
def add_checkpoint(shipment_id: int, body: CheckpointIn, db: Db):
    status = _get(db, shipment_id)["shipment_status"]
    if status != "in_transit":
        raise HTTPException(409, "Checkpoints can only be added while the shipment is in transit")
    return db.execute("""INSERT INTO shipment_checkpoint (shipment_id, checkpoint_no, checkpoint_time, event_type,
                                                          location_description)
                         SELECT %s, COALESCE(MAX(checkpoint_no), 0) + 1, now(), %s, %s
                         FROM shipment_checkpoint WHERE shipment_id = %s RETURNING *""",
                      [shipment_id, body.event_type, body.location_description, shipment_id]).fetchone()
