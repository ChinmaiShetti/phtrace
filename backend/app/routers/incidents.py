"""Incidents, investigations, batch assessments and corrective actions."""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.auth import CurrentUser, Db, require
from app.db import set_context

router = APIRouter(prefix="/api", tags=["incidents"])
Investigators = Depends(require("investigator", "quality_manager"))
QualityManager = Depends(require("quality_manager"))


class IncidentIn(BaseModel):
    incident_type: Literal["temperature_excursion", "humidity_excursion", "sensor_failure", "other"]
    severity: Literal["low", "medium", "high", "critical"]
    shipment_id: int | None = None
    facility_id: int | None = None
    start_time: datetime | None = None
    description: str = Field(min_length=5, max_length=2000)

    @model_validator(mode="after")
    def one_target(self):
        if (self.shipment_id is None) == (self.facility_id is None):
            raise ValueError("Choose exactly one of shipment or facility")
        return self


class IncidentStatus(BaseModel):
    status: Literal["investigating", "resolved", "closed"]
    reason: str = Field(min_length=3, max_length=500)


class InvestigationIn(BaseModel):
    assigned_to: int


class InvestigationUpdate(BaseModel):
    findings: str | None = Field(default=None, max_length=5000)
    investigation_status: Literal["assigned", "in_progress", "completed"] | None = None


class AssessmentIn(BaseModel):
    assessment_status: Literal["pending_review", "under_assessment", "assessed"]
    assessment_note: str | None = Field(default=None, max_length=2000)


class ActionIn(BaseModel):
    assigned_to: int
    action_description: str = Field(min_length=5, max_length=2000)
    due_date: date | None = None


class ActionUpdate(BaseModel):
    action_status: Literal["pending", "in_progress", "completed", "cancelled"]


@router.get("/incidents")
def list_incidents(db: Db, status: str | None = None, incident_type: str | None = None):
    return db.execute("""SELECT * FROM v_incident_summary
                         WHERE (%(s)s::text IS NULL OR incident_status = %(s)s)
                           AND (%(t)s::text IS NULL OR incident_type = %(t)s)
                         ORDER BY (incident_status IN ('open','investigating')) DESC, detected_at DESC""",
                      {"s": status, "t": incident_type}).fetchall()


@router.post("/incidents", status_code=201,
             dependencies=[Depends(require("operator", "investigator", "quality_manager"))])
def report_incident(body: IncidentIn, db: Db, user: CurrentUser):
    return db.execute("""INSERT INTO incident (incident_type, severity, detection_source, shipment_id, facility_id,
                                               reported_by, start_time, description)
                         VALUES (%s, %s, 'manual', %s, %s, %s, %s, %s) RETURNING *""",
                      [body.incident_type, body.severity, body.shipment_id, body.facility_id, user.staff_id,
                       body.start_time, body.description]).fetchone()


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int, db: Db):
    inc = db.execute("SELECT * FROM v_incident_summary WHERE incident_id = %s", [incident_id]).fetchone()
    if inc is None:
        raise HTTPException(404, "Incident not found")
    p = [incident_id]
    linked = db.execute("""SELECT r.*, s.serial_number, ir.relevance_note FROM incident_reading ir
                           JOIN sensor_reading r USING (reading_id) JOIN sensor s USING (sensor_id)
                           WHERE ir.incident_id = %s ORDER BY r.recorded_at""", p).fetchall()
    # context for the chart: readings of the same sensors from 1 hour before to 1 hour after the window
    context = db.execute("""SELECT r.reading_id, r.sensor_id, r.recorded_at, r.temperature, r.humidity, r.quality_status
                            FROM sensor_reading r
                            WHERE r.sensor_id IN (SELECT r2.sensor_id FROM incident_reading ir
                                                  JOIN sensor_reading r2 USING (reading_id) WHERE ir.incident_id = %s)
                              AND r.recorded_at BETWEEN %s::timestamptz - interval '1 hour'
                                                    AND COALESCE(%s::timestamptz, now()) + interval '1 hour'
                            ORDER BY r.recorded_at""",
                         [incident_id, inc["start_time"] or inc["detected_at"], inc["end_time"]]).fetchall()
    limits = None
    if inc["shipment_id"]:
        limits = db.execute("SELECT min_temp, max_temp FROM v_shipment_limits WHERE shipment_id = %s",
                            [inc["shipment_id"]]).fetchone()
    return {
        "incident": inc,
        "limits": limits,
        "readings": linked,
        "context_readings": context,
        "batches": db.execute("""SELECT ib.*, b.batch_number, b.batch_status, b.expiry_date, p.product_name,
                                        p.min_temp, p.max_temp, vs.current_quantity
                                 FROM incident_batch ib JOIN batch b USING (batch_id) JOIN product p USING (product_id)
                                 JOIN v_batch_summary vs USING (batch_id)
                                 WHERE ib.incident_id = %s ORDER BY b.batch_number""", p).fetchall(),
        "investigations": db.execute("""SELECT iv.*, s.staff_name AS assignee FROM investigation iv
                                        JOIN staff s ON s.staff_id = iv.assigned_to
                                        WHERE iv.incident_id = %s ORDER BY iv.started_at""", p).fetchall(),
        "actions": db.execute("""SELECT ca.*, s.staff_name AS assignee FROM corrective_action ca
                                 JOIN investigation iv USING (investigation_id) JOIN staff s ON s.staff_id = ca.assigned_to
                                 WHERE iv.incident_id = %s ORDER BY ca.action_id""", p).fetchall(),
        "related_shipments": db.execute("SELECT * FROM related_shipments(%s)", p).fetchall(),
        # an automatic incident is created by the detection trigger, not by the person whose session stored the reading
        "history": db.execute("""SELECT CASE WHEN auto THEN (a.new_data->>'detected_at')::timestamptz ELSE a.changed_at END
                                            AS changed_at,
                                        a.table_name, a.action,
                                        CASE WHEN auto THEN 'Raised by the database from a sensor reading' ELSE a.reason END
                                            AS reason,
                                        CASE WHEN auto THEN 'automatic detection' ELSE s.staff_name END AS staff_name,
                                        a.old_data->>'incident_status' AS from_status,
                                        a.new_data->>'incident_status' AS to_status
                                 FROM audit_log a LEFT JOIN staff s ON s.staff_id = a.changed_by,
                                      LATERAL (SELECT a.action = 'INSERT'
                                                      AND a.new_data->>'detection_source' = 'automatic' AS auto) x
                                 WHERE a.table_name = 'incident' AND a.row_pk = %s::text
                                   AND (a.action = 'INSERT' OR a.old_data->>'incident_status'
                                        IS DISTINCT FROM a.new_data->>'incident_status')
                                 ORDER BY a.changed_at""", p).fetchall(),
    }


@router.post("/incidents/{incident_id}/status", dependencies=[Investigators])
def change_incident_status(incident_id: int, body: IncidentStatus, db: Db, user: CurrentUser):
    """Allowed transitions and closing rules are enforced by the database trigger."""
    set_context(db, user.staff_id, body.reason)
    row = db.execute("UPDATE incident SET incident_status = %s WHERE incident_id = %s RETURNING *",
                     [body.status, incident_id]).fetchone()
    if row is None:
        raise HTTPException(404, "Incident not found")
    return row


@router.post("/incidents/{incident_id}/investigations", status_code=201, dependencies=[QualityManager])
def assign_investigator(incident_id: int, body: InvestigationIn, db: Db):
    return db.execute("""INSERT INTO investigation (incident_id, assigned_to) VALUES (%s, %s) RETURNING *""",
                      [incident_id, body.assigned_to]).fetchone()


@router.patch("/investigations/{investigation_id}", dependencies=[Investigators])
def update_investigation(investigation_id: int, body: InvestigationUpdate, db: Db, user: CurrentUser):
    iv = db.execute("SELECT * FROM investigation WHERE investigation_id = %s", [investigation_id]).fetchone()
    if iv is None:
        raise HTTPException(404, "Investigation not found")
    if user.role == "investigator" and iv["assigned_to"] != user.staff_id:
        raise HTTPException(403, "Only the assigned investigator or a quality manager can update this investigation")
    status = body.investigation_status or iv["investigation_status"]
    return db.execute("""UPDATE investigation
                         SET findings = COALESCE(%s, findings), investigation_status = %s,
                             completed_at = CASE WHEN %s::text = 'completed' THEN COALESCE(completed_at, now()) END
                         WHERE investigation_id = %s RETURNING *""",
                      [body.findings, status, status, investigation_id]).fetchone()


@router.patch("/incidents/{incident_id}/batches/{batch_id}", dependencies=[Investigators])
def assess_batch(incident_id: int, batch_id: int, body: AssessmentIn, db: Db):
    row = db.execute("""UPDATE incident_batch SET assessment_status = %s, assessment_note = COALESCE(%s, assessment_note)
                        WHERE incident_id = %s AND batch_id = %s RETURNING *""",
                     [body.assessment_status, body.assessment_note, incident_id, batch_id]).fetchone()
    if row is None:
        raise HTTPException(404, "Batch is not linked to this incident")
    return row


@router.post("/investigations/{investigation_id}/actions", status_code=201, dependencies=[Investigators])
def add_action(investigation_id: int, body: ActionIn, db: Db):
    return db.execute("""INSERT INTO corrective_action (investigation_id, assigned_to, action_description, due_date)
                         VALUES (%s, %s, %s, %s) RETURNING *""",
                      [investigation_id, body.assigned_to, body.action_description, body.due_date]).fetchone()


@router.patch("/actions/{action_id}")
def update_action(action_id: int, body: ActionUpdate, db: Db, user: CurrentUser):
    ca = db.execute("SELECT * FROM corrective_action WHERE action_id = %s", [action_id]).fetchone()
    if ca is None:
        raise HTTPException(404, "Corrective action not found")
    if user.role not in ("investigator", "quality_manager") and ca["assigned_to"] != user.staff_id:
        raise HTTPException(403, "Only the responsible person, an investigator or a quality manager can update this action")
    return db.execute("""UPDATE corrective_action SET action_status = %s,
                             completed_at = CASE WHEN %s::text = 'completed' THEN COALESCE(completed_at, now()) END
                         WHERE action_id = %s RETURNING *""",
                      [body.action_status, body.action_status, action_id]).fetchone()
