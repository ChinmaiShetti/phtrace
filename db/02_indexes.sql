-- Foreign keys used in joins (PostgreSQL does not index FKs automatically)
CREATE INDEX batch_product_idx              ON batch (product_id);
CREATE INDEX movement_batch_time_idx        ON batch_movement (batch_id, movement_time);
CREATE INDEX movement_facility_idx          ON batch_movement (facility_id, batch_id);
CREATE INDEX movement_shipment_idx          ON batch_movement (shipment_id);
CREATE INDEX shipment_vehicle_idx           ON shipment (vehicle_id);
CREATE INDEX shipment_origin_idx            ON shipment (origin_facility_id);
CREATE INDEX shipment_destination_idx       ON shipment (destination_facility_id);
CREATE INDEX shipment_batch_batch_idx       ON shipment_batch (batch_id);
CREATE INDEX assignment_sensor_idx          ON sensor_assignment (sensor_id, assigned_at);
CREATE INDEX assignment_shipment_idx        ON sensor_assignment (shipment_id);
CREATE INDEX assignment_facility_idx        ON sensor_assignment (facility_id);
CREATE INDEX incident_shipment_idx          ON incident (shipment_id);
CREATE INDEX incident_facility_idx          ON incident (facility_id);
CREATE INDEX incident_reading_reading_idx   ON incident_reading (reading_id);
CREATE INDEX incident_batch_batch_idx       ON incident_batch (batch_id);
CREATE INDEX investigation_incident_idx     ON investigation (incident_id);
CREATE INDEX investigation_assignee_idx     ON investigation (assigned_to);
CREATE INDEX action_investigation_idx       ON corrective_action (investigation_id);
CREATE INDEX action_assignee_idx            ON corrective_action (assigned_to);
CREATE INDEX audit_row_idx                  ON audit_log (table_name, row_pk);

-- Partial indexes for the dashboard
CREATE INDEX shipment_in_transit_idx  ON shipment (expected_arrival) WHERE shipment_status = 'in_transit';
CREATE INDEX incident_active_idx      ON incident (detected_at) WHERE incident_status IN ('open', 'investigating');
CREATE INDEX action_open_idx          ON corrective_action (due_date) WHERE action_status IN ('pending', 'in_progress');

-- Readings are appended in time order: a BRIN index on recorded_at is tiny and suits time-window scans.
-- Point and per-sensor lookups use the UNIQUE (sensor_id, recorded_at) B-tree.
CREATE INDEX reading_recorded_brin ON sensor_reading USING brin (recorded_at);
