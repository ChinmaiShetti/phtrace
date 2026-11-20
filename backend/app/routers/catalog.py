"""Master data: products, batches, facilities, vehicles, sensors and staff."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.auth import ROLES, CurrentUser, Db, hasher, require
from app.db import set_context

router = APIRouter(prefix="/api", tags=["catalog"])
Editor = Depends(require("operator", "quality_manager", "admin"))


def not_found(what: str):
    return HTTPException(404, f"{what} not found")


# ---------------------------------------------------------------- products
class ProductIn(BaseModel):
    product_name: str = Field(min_length=2, max_length=120)
    product_type: Literal["vaccine", "biologic", "medicine", "other"]
    min_temp: float = Field(ge=-80, le=80)
    max_temp: float = Field(ge=-80, le=80)
    min_humidity: float | None = Field(default=None, ge=0, le=100)
    max_humidity: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def ranges(self):
        if self.min_temp >= self.max_temp:
            raise ValueError("Minimum temperature must be below maximum temperature")
        if (self.min_humidity is None) != (self.max_humidity is None):
            raise ValueError("Give both humidity limits or neither")
        if self.min_humidity is not None and self.min_humidity >= self.max_humidity:
            raise ValueError("Minimum humidity must be below maximum humidity")
        return self


@router.get("/products")
def list_products(db: Db):
    return db.execute("""SELECT p.*, (SELECT COUNT(*) FROM batch b WHERE b.product_id = p.product_id) AS batches
                         FROM product p ORDER BY product_name""").fetchall()


@router.post("/products", status_code=201, dependencies=[Editor])
def create_product(body: ProductIn, db: Db):
    return db.execute("""INSERT INTO product (product_name, product_type, min_temp, max_temp, min_humidity, max_humidity)
                         VALUES (%(product_name)s, %(product_type)s, %(min_temp)s, %(max_temp)s, %(min_humidity)s,
                                 %(max_humidity)s) RETURNING *""", body.model_dump()).fetchone()


@router.put("/products/{product_id}", dependencies=[Editor])
def update_product(product_id: int, body: ProductIn, db: Db):
    row = db.execute("""UPDATE product SET product_name = %(product_name)s, product_type = %(product_type)s,
                            min_temp = %(min_temp)s, max_temp = %(max_temp)s,
                            min_humidity = %(min_humidity)s, max_humidity = %(max_humidity)s
                        WHERE product_id = %(id)s RETURNING *""", {**body.model_dump(), "id": product_id}).fetchone()
    if row is None:
        raise not_found("Product")
    return row


# ---------------------------------------------------------------- batches
class BatchIn(BaseModel):
    batch_number: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9-_/]+$")
    product_id: int
    manufacturing_date: date
    expiry_date: date
    initial_quantity: int = Field(gt=0, le=10_000_000)
    intake_facility_id: int = Field(description="Facility that receives the batch from the manufacturer")

    @model_validator(mode="after")
    def dates(self):
        if self.expiry_date <= self.manufacturing_date:
            raise ValueError("Expiry date must be after the manufacturing date")
        if self.manufacturing_date > date.today():
            raise ValueError("Manufacturing date cannot be in the future")
        return self


class StatusChange(BaseModel):
    status: str
    reason: str = Field(min_length=3, max_length=500)


@router.get("/batches")
def list_batches(db: Db, q: str | None = None, status: str | None = None):
    return db.execute("""SELECT * FROM v_batch_summary
                         WHERE (%(q)s::text IS NULL OR batch_number ILIKE '%%' || %(q)s || '%%'
                                OR product_name ILIKE '%%' || %(q)s || '%%')
                           AND (%(status)s::text IS NULL OR batch_status = %(status)s)
                         ORDER BY batch_number""", {"q": q, "status": status}).fetchall()


@router.post("/batches", status_code=201, dependencies=[Editor])
def create_batch(body: BatchIn, db: Db):
    """Registers the batch and its intake movement in one transaction."""
    row = db.execute("""INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity)
                        VALUES (%(batch_number)s, %(product_id)s, %(manufacturing_date)s, %(expiry_date)s,
                                %(initial_quantity)s) RETURNING *""", body.model_dump()).fetchone()
    db.execute("""INSERT INTO batch_movement (batch_id, facility_id, movement_type, movement_time, quantity_moved)
                  VALUES (%s, %s, 'received', now(), %s)""",
               [row["batch_id"], body.intake_facility_id, body.initial_quantity])
    return row


@router.get("/batches/{batch_id}/trace")
def trace_batch(batch_id: int, db: Db):
    summary = db.execute("SELECT * FROM v_batch_summary WHERE batch_id = %s", [batch_id]).fetchone()
    if summary is None:
        raise not_found("Batch")
    params = [batch_id]
    return {
        "batch": summary,
        "product": db.execute("SELECT p.* FROM product p JOIN batch b USING (product_id) WHERE b.batch_id = %s",
                              params).fetchone(),
        "stock": db.execute("SELECT facility_id, facility_name, on_hand FROM v_batch_stock WHERE batch_id = %s "
                            "ORDER BY facility_name", params).fetchall(),
        "movements": db.execute("""SELECT m.*, f.facility_name FROM batch_movement m
                                   JOIN facility f USING (facility_id)
                                   WHERE m.batch_id = %s ORDER BY m.movement_time, m.movement_id""", params).fetchall(),
        "shipments": db.execute("""SELECT s.shipment_id, s.shipment_status, s.dispatch_time, s.actual_arrival,
                                          s.origin_name, s.destination_name, s.registration_number, sb.quantity_shipped
                                   FROM shipment_batch sb JOIN v_shipment_summary s USING (shipment_id)
                                   WHERE sb.batch_id = %s ORDER BY s.dispatch_time NULLS LAST""", params).fetchall(),
        "incidents": db.execute("""SELECT i.incident_id, i.incident_code, i.incident_type, i.severity, i.incident_status,
                                          i.detected_at, i.exposure_minutes, i.exposure_seconds, i.peak_temperature,
                                          ib.assessment_status, ib.assessment_note
                                   FROM incident_batch ib JOIN v_incident_summary i USING (incident_id)
                                   WHERE ib.batch_id = %s ORDER BY i.detected_at DESC""", params).fetchall(),
        "status_history": db.execute("""SELECT a.changed_at, a.old_data->>'batch_status' AS from_status,
                                               a.new_data->>'batch_status' AS to_status, a.reason, s.staff_name
                                        FROM audit_log a LEFT JOIN staff s ON s.staff_id = a.changed_by
                                        WHERE a.table_name = 'batch' AND a.row_pk = %s::text AND a.action = 'UPDATE'
                                          AND a.old_data->>'batch_status' IS DISTINCT FROM a.new_data->>'batch_status'
                                        ORDER BY a.changed_at""", params).fetchall(),
    }


@router.post("/batches/{batch_id}/status",
             dependencies=[Depends(require("investigator", "quality_manager"))])
def change_batch_status(batch_id: int, body: StatusChange, db: Db, user: CurrentUser):
    """Allowed transitions per role are enforced by the database (batch_status_transition)."""
    set_context(db, user.staff_id, body.reason)
    row = db.execute("UPDATE batch SET batch_status = %s WHERE batch_id = %s RETURNING *",
                     [body.status, batch_id]).fetchone()
    if row is None:
        raise not_found("Batch")
    return row


@router.get("/batch-transitions")
def batch_transitions(db: Db):
    return db.execute("SELECT * FROM batch_status_transition ORDER BY 1, 2, 3").fetchall()


# ---------------------------------------------------------------- facilities and vehicles
class FacilityIn(BaseModel):
    facility_name: str = Field(min_length=2, max_length=120)
    facility_type: Literal["warehouse", "distribution_centre", "hospital", "clinic", "pharmacy"]
    street: str = Field(min_length=2, max_length=200)
    city: str = Field(min_length=2, max_length=80)
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    phone_numbers: list[Annotated[str, Field(pattern=r"^[0-9+ -]{6,20}$")]] = []


@router.get("/facilities")
def list_facilities(db: Db):
    return db.execute("""SELECT f.*, COALESCE(array_agg(p.phone_number ORDER BY p.phone_number)
                                FILTER (WHERE p.phone_number IS NOT NULL), '{}') AS phone_numbers
                         FROM facility f LEFT JOIN facility_phone p USING (facility_id)
                         GROUP BY f.facility_id ORDER BY f.facility_name""").fetchall()


@router.post("/facilities", status_code=201, dependencies=[Editor])
def create_facility(body: FacilityIn, db: Db):
    row = db.execute("""INSERT INTO facility (facility_name, facility_type, street, city, pincode)
                        VALUES (%(facility_name)s, %(facility_type)s, %(street)s, %(city)s, %(pincode)s)
                        RETURNING *""", body.model_dump()).fetchone()
    for phone in body.phone_numbers:
        db.execute("INSERT INTO facility_phone VALUES (%s, %s)", [row["facility_id"], phone])
    return {**row, "phone_numbers": body.phone_numbers}


class VehicleIn(BaseModel):
    registration_number: str = Field(pattern=r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}$")
    vehicle_type: Literal["refrigerated_van", "refrigerated_truck", "insulated_van"]
    refrigeration_status: Literal["operational", "degraded", "faulty"] = "operational"


@router.get("/vehicles")
def list_vehicles(db: Db):
    return db.execute("""SELECT v.*, (SELECT COUNT(*) FROM shipment s WHERE s.vehicle_id = v.vehicle_id
                                      AND s.shipment_status = 'in_transit') AS active_shipments
                         FROM vehicle v ORDER BY registration_number""").fetchall()


@router.post("/vehicles", status_code=201, dependencies=[Editor])
def create_vehicle(body: VehicleIn, db: Db):
    return db.execute("""INSERT INTO vehicle (registration_number, vehicle_type, refrigeration_status)
                         VALUES (%(registration_number)s, %(vehicle_type)s, %(refrigeration_status)s) RETURNING *""",
                      body.model_dump()).fetchone()


class VehicleStatus(BaseModel):
    refrigeration_status: Literal["operational", "degraded", "faulty"]


@router.patch("/vehicles/{vehicle_id}", dependencies=[Editor])
def update_vehicle(vehicle_id: int, body: VehicleStatus, db: Db):
    row = db.execute("UPDATE vehicle SET refrigeration_status = %s WHERE vehicle_id = %s RETURNING *",
                     [body.refrigeration_status, vehicle_id]).fetchone()
    if row is None:
        raise not_found("Vehicle")
    return row


# ---------------------------------------------------------------- sensors
class SensorIn(BaseModel):
    serial_number: str = Field(min_length=3, max_length=40)
    sensor_type: Literal["temperature", "humidity", "temp_humidity"]
    expected_interval_s: int = Field(default=300, gt=0, le=86400)


class SensorStatus(BaseModel):
    installation_status: Literal["active", "inactive", "faulty"]


class AssignmentIn(BaseModel):
    sensor_id: int
    shipment_id: int | None = None
    facility_id: int | None = None

    @model_validator(mode="after")
    def one_target(self):
        if (self.shipment_id is None) == (self.facility_id is None):
            raise ValueError("Choose exactly one of shipment or facility")
        return self


@router.get("/sensors")
def list_sensors(db: Db):
    return db.execute("""SELECT s.*, a.assignment_id, a.shipment_id, a.facility_id, a.assigned_at, f.facility_name,
                                (SELECT MAX(recorded_at) FROM sensor_reading r WHERE r.sensor_id = s.sensor_id) AS last_reading
                         FROM sensor s
                         LEFT JOIN sensor_assignment a ON a.sensor_id = s.sensor_id AND a.unassigned_at IS NULL
                         LEFT JOIN facility f ON f.facility_id = a.facility_id
                         ORDER BY s.serial_number""").fetchall()


@router.post("/sensors", status_code=201, dependencies=[Editor])
def create_sensor(body: SensorIn, db: Db):
    return db.execute("""INSERT INTO sensor (serial_number, sensor_type, expected_interval_s)
                         VALUES (%(serial_number)s, %(sensor_type)s, %(expected_interval_s)s) RETURNING *""",
                      body.model_dump()).fetchone()


@router.patch("/sensors/{sensor_id}", dependencies=[Editor])
def update_sensor(sensor_id: int, body: SensorStatus, db: Db):
    row = db.execute("UPDATE sensor SET installation_status = %s WHERE sensor_id = %s RETURNING *",
                     [body.installation_status, sensor_id]).fetchone()
    if row is None:
        raise not_found("Sensor")
    return row


@router.post("/sensor-assignments", status_code=201, dependencies=[Editor])
def assign_sensor(body: AssignmentIn, db: Db):
    return db.execute("""INSERT INTO sensor_assignment (sensor_id, shipment_id, facility_id, assigned_at)
                         VALUES (%(sensor_id)s, %(shipment_id)s, %(facility_id)s, now()) RETURNING *""",
                      body.model_dump()).fetchone()


@router.post("/sensor-assignments/{assignment_id}/end", dependencies=[Editor])
def end_assignment(assignment_id: int, db: Db):
    row = db.execute("""UPDATE sensor_assignment SET unassigned_at = now()
                        WHERE assignment_id = %s AND unassigned_at IS NULL RETURNING *""", [assignment_id]).fetchone()
    if row is None:
        raise HTTPException(409, "Assignment not found or already ended")
    return row


# ---------------------------------------------------------------- staff
class StaffIn(BaseModel):
    staff_name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    password: str = Field(min_length=8, max_length=128)
    role: Literal[ROLES]  # type: ignore[valid-type]


class StaffUpdate(BaseModel):
    role: Literal[ROLES] | None = None  # type: ignore[valid-type]
    account_status: Literal["active", "inactive"] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


@router.get("/staff")
def list_staff(db: Db):
    return db.execute("SELECT staff_id, staff_name, email, role, account_status FROM staff ORDER BY staff_name").fetchall()


@router.post("/staff", status_code=201, dependencies=[Depends(require("admin"))])
def create_staff(body: StaffIn, db: Db):
    return db.execute("""INSERT INTO staff (staff_name, email, password_hash, role) VALUES (%s, %s, %s, %s)
                         RETURNING staff_id, staff_name, email, role, account_status""",
                      [body.staff_name, body.email, hasher.hash(body.password), body.role]).fetchone()


@router.patch("/staff/{staff_id}", dependencies=[Depends(require("admin"))])
def update_staff(staff_id: int, body: StaffUpdate, db: Db):
    row = db.execute("""UPDATE staff SET role = COALESCE(%s, role), account_status = COALESCE(%s, account_status),
                               password_hash = COALESCE(%s, password_hash)
                        WHERE staff_id = %s RETURNING staff_id, staff_name, email, role, account_status""",
                     [body.role, body.account_status, hasher.hash(body.password) if body.password else None,
                      staff_id]).fetchone()
    if row is None:
        raise not_found("Staff member")
    return row
