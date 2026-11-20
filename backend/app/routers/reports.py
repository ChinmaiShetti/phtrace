"""Dashboard, reports, audit trail and the demo simulator."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import simulator
from app.auth import CurrentUser, Db, require

router = APIRouter(prefix="/api", tags=["reports"])

REPORTS = {
    "incidents-by-type": ("Incidents by type and severity", "v_report_incidents_by_type_severity"),
    "batch-incidents": ("Batches involved in incidents", "v_report_batch_incidents"),
    "vehicle-repeats": ("Vehicles with repeated incidents", "v_report_vehicle_repeat_incidents"),
    "pending-actions": ("Corrective actions pending completion", "v_report_pending_actions"),
    "expiring-batches": ("Batches expiring within 60 days", "v_report_expiring_batches"),
    "sensor-quality": ("Sensor data-quality problems", "v_report_sensor_quality"),
}


@router.get("/dashboard")
def dashboard(db: Db):
    return {
        "counts": db.execute("SELECT * FROM v_dashboard").fetchone(),
        "recent_incidents": db.execute("""SELECT incident_id, incident_code, incident_type, severity, incident_status,
                                                 detected_at, shipment_id, facility_name, peak_temperature
                                          FROM v_incident_summary ORDER BY detected_at DESC LIMIT 6""").fetchall(),
        "active_shipments": db.execute("""SELECT shipment_id, origin_name, destination_name, registration_number,
                                                 dispatch_time, expected_arrival, overdue, units
                                          FROM v_shipment_summary WHERE shipment_status = 'in_transit'
                                          ORDER BY expected_arrival""").fetchall(),
    }


@router.get("/reports")
def list_reports():
    return [{"key": k, "title": t} for k, (t, _) in REPORTS.items()]


@router.get("/reports/{key}")
def report(key: str, db: Db):
    if key not in REPORTS:
        raise HTTPException(404, "Unknown report")
    title, view = REPORTS[key]
    return {"title": title, "rows": db.execute(f"SELECT * FROM {view}").fetchall()}   # view name from a fixed whitelist


@router.get("/audit", dependencies=[Depends(require("quality_manager", "admin"))])
def audit(db: Db, table: str | None = None, limit: int = 200):
    return db.execute("""SELECT a.audit_id, a.table_name, a.row_pk, a.action, a.reason, a.changed_at, s.staff_name,
                                a.old_data, a.new_data
                         FROM audit_log a LEFT JOIN staff s ON s.staff_id = a.changed_by
                         WHERE %(t)s::text IS NULL OR a.table_name = %(t)s
                         ORDER BY a.audit_id DESC LIMIT %(l)s""", {"t": table, "l": min(limit, 1000)}).fetchall()


class SimulateIn(BaseModel):
    shipment_id: int
    peak_temperature: float = Field(default=11.5, ge=-50, le=60)


@router.post("/admin/simulate-excursion", status_code=202, dependencies=[Depends(require("admin"))])
def simulate(body: SimulateIn, db: Db, user: CurrentUser):
    row = db.execute("""SELECT 1 FROM sensor_assignment a JOIN shipment s USING (shipment_id)
                        WHERE a.shipment_id = %s AND a.unassigned_at IS NULL AND s.shipment_status = 'in_transit'""",
                     [body.shipment_id]).fetchone()
    if row is None:
        raise HTTPException(409, "Shipment must be in transit with an active sensor")
    simulator.start_excursion(body.shipment_id, body.peak_temperature, user.staff_id)
    return {"started": True, "readings": len(simulator.excursion_profile(0, 1)), "interval_seconds": 2.5}


@router.post("/admin/backfill", dependencies=[Depends(require("admin", "operator"))])
def backfill(user: CurrentUser):
    return {"inserted": simulator.backfill(user.staff_id)}
