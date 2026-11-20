-- Least privilege for the application role (pharmatrace_app). The schema owner runs migrations.
-- Notably: no DELETE on readings, incidents or the audit log, and no TRUNCATE anywhere.

GRANT USAGE ON SCHEMA public TO pharmatrace_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pharmatrace_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pharmatrace_app;

GRANT INSERT, UPDATE ON
    staff, product, batch, facility, facility_phone, vehicle,
    shipment, shipment_batch, shipment_checkpoint, batch_movement,
    sensor, sensor_assignment,
    incident, incident_reading, incident_batch,
    investigation, corrective_action
TO pharmatrace_app;

-- removing a line from a planned shipment, or a facility phone number
GRANT DELETE ON shipment_batch, facility_phone TO pharmatrace_app;

-- readings: insert, and change only the quality flag
GRANT INSERT ON sensor_reading TO pharmatrace_app;
GRANT UPDATE (quality_status) ON sensor_reading TO pharmatrace_app;

-- the audit log and workflow rules are read-only to the application
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON audit_log, batch_status_transition FROM pharmatrace_app;
