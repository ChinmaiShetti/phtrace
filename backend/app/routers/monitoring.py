"""Sensor readings: ingest (idempotent) and query for the monitoring screen."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator

from app.auth import Db, require

router = APIRouter(prefix="/api/readings", tags=["monitoring"])


class ReadingIn(BaseModel):
    sensor_id: int
    recorded_at: datetime
    temperature: float | None = Field(default=None, ge=-999.99, le=9999.99)
    humidity: float | None = Field(default=None, ge=-999.99, le=9999.99)

    @model_validator(mode="after")
    def has_value(self):
        if self.temperature is None and self.humidity is None:
            raise ValueError("A reading needs a temperature or a humidity value")
        return self


@router.post("", dependencies=[Depends(require("operator", "admin"))])
def ingest(readings: list[ReadingIn], db: Db):
    """Duplicates (same sensor and timestamp) are skipped and counted, so a gateway can safely retry."""
    before = db.execute("SELECT COUNT(*) AS n FROM incident").fetchone()["n"]
    inserted = 0
    for r in readings:
        inserted += db.execute("""INSERT INTO sensor_reading (sensor_id, recorded_at, temperature, humidity)
                                  VALUES (%s, %s, %s, %s) ON CONFLICT (sensor_id, recorded_at) DO NOTHING""",
                               [r.sensor_id, r.recorded_at, r.temperature, r.humidity]).rowcount
    after = db.execute("SELECT COUNT(*) AS n FROM incident").fetchone()["n"]
    return {"received": len(readings), "inserted": inserted, "duplicates": len(readings) - inserted,
            "incidents_opened": after - before}


@router.get("")
def query(db: Db,
          sensor_id: int | None = None,
          shipment_id: int | None = None,
          start: datetime | None = Query(default=None, alias="from"),
          end: datetime | None = Query(default=None, alias="to"),
          quality: str | None = None,
          out_of_limits: bool = False,
          limit: int = Query(default=500, le=5000)):
    """Readings with the limits that applied to them. For a shipment, all its sensors' readings."""
    return db.execute("""
        WITH r AS (
            SELECT r.*, s.serial_number, a.shipment_id, a.facility_id,
                   COALESCE(l.min_temp, fl.min_temp) AS min_temp, COALESCE(l.max_temp, fl.max_temp) AS max_temp
            FROM sensor_reading r
            JOIN sensor s USING (sensor_id)
            LEFT JOIN sensor_assignment a ON a.sensor_id = r.sensor_id AND a.assigned_at <= r.recorded_at
                 AND (a.unassigned_at IS NULL OR r.recorded_at < a.unassigned_at)
            LEFT JOIN v_shipment_limits l ON l.shipment_id = a.shipment_id
            LEFT JOIN LATERAL (
                SELECT MAX(p.min_temp) AS min_temp, MIN(p.max_temp) AS max_temp
                FROM batches_at_target(NULL, a.facility_id, r.recorded_at) t JOIN batch b USING (batch_id)
                JOIN product p USING (product_id)) fl ON a.facility_id IS NOT NULL
            WHERE (%(sensor)s::int IS NULL OR r.sensor_id = %(sensor)s)
              AND (%(ship)s::int IS NULL OR a.shipment_id = %(ship)s)
              AND (%(start)s::timestamptz IS NULL OR r.recorded_at >= %(start)s)
              AND (%(end)s::timestamptz IS NULL OR r.recorded_at <= %(end)s)
              AND (%(quality)s::text IS NULL OR r.quality_status = %(quality)s)
        )
        SELECT *, (temperature < min_temp OR temperature > max_temp) AS out_of_limits
        FROM r
        WHERE NOT %(ool)s OR (temperature < min_temp OR temperature > max_temp)
        ORDER BY recorded_at DESC
        LIMIT %(limit)s""",
        {"sensor": sensor_id, "ship": shipment_id, "start": start, "end": end, "quality": quality,
         "ool": out_of_limits, "limit": limit}).fetchall()
