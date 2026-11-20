"""Turn database errors into clear HTTP responses. The database message is shown to the user,
because constraint names and trigger messages are written to be readable."""

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg import errors

FRIENDLY = {
    "product_temp_range": "Minimum temperature must be below maximum temperature.",
    "product_humidity_pair": "Give both humidity limits or neither.",
    "product_humidity_range": "Humidity limits must be between 0 and 100, minimum below maximum.",
    "batch_dates": "Expiry date must be after the manufacturing date.",
    "shipment_route": "Origin and destination must be different facilities.",
    "assignment_no_overlap": "This sensor is already assigned somewhere during that period.",
    "assignment_one_target": "Assign the sensor to exactly one shipment or facility.",
    "reading_unique_per_sensor": "A reading for this sensor at this time already exists.",
    "assessed_needs_note": "An assessment note is required when marking a batch as assessed.",
    "investigation_findings": "Findings are required to complete an investigation.",
    "incident_active_shipment_uq": "An open incident of this type already exists for this shipment.",
    "incident_active_facility_uq": "An open incident of this type already exists for this facility.",
}

STATUS = [
    (errors.InsufficientPrivilege, 403),
    (errors.NoDataFound, 404),
    (errors.UniqueViolation, 409),
    (errors.ExclusionViolation, 409),
    (errors.ForeignKeyViolation, 409),
    (errors.RestrictViolation, 409),
    (errors.CheckViolation, 422),
    (errors.NotNullViolation, 422),
    (errors.InvalidTextRepresentation, 422),
    (errors.NumericValueOutOfRange, 422),
    (errors.StringDataRightTruncation, 422),
    (errors.RaiseException, 409),
]


def register(app: FastAPI) -> None:
    @app.exception_handler(psycopg.Error)
    async def db_error(_: Request, exc: psycopg.Error) -> JSONResponse:
        code = next((c for cls, c in STATUS if isinstance(exc, cls)), 500)
        diag = exc.diag
        message = FRIENDLY.get(diag.constraint_name or "") or diag.message_primary or "Database error"
        if code == 500:
            message = "Unexpected database error"
        return JSONResponse(status_code=code, content={"detail": message})
