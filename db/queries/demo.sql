-- PharmaTrace: queries to run live in the demo (Scene 7). Run in psql connected to the pharmatrace database.
--   psql -h localhost -U postgres -d pharmatrace -f db/queries/demo.sql      (or paste section by section)

-- 1. Join across five tables: which batches are on which shipment, from where to where
SELECT 'SH' || lpad(s.shipment_id::text, 3, '0') AS shipment, o.facility_name AS origin, d.facility_name AS destination,
       b.batch_number, p.product_name, sb.quantity_shipped, s.shipment_status
FROM shipment s
JOIN facility o ON o.facility_id = s.origin_facility_id
JOIN facility d ON d.facility_id = s.destination_facility_id
JOIN shipment_batch sb ON sb.shipment_id = s.shipment_id
JOIN batch b ON b.batch_id = sb.batch_id
JOIN product p ON p.product_id = b.product_id
ORDER BY s.shipment_id, b.batch_number;

-- 2. Trace an incident: affected batches and where each batch is now (derived from movement history)
SELECT i.incident_code, b.batch_number, ib.assessment_status, st.facility_name, st.on_hand
FROM v_incident_summary i
JOIN incident_batch ib ON ib.incident_id = i.incident_id
JOIN batch b ON b.batch_id = ib.batch_id
LEFT JOIN v_batch_stock st ON st.batch_id = b.batch_id
ORDER BY i.incident_id, b.batch_number;

-- 3. Aggregation with HAVING: vehicles involved in more than one incident
SELECT * FROM v_report_vehicle_repeat_incidents;

-- 4. Correlated subquery: batches whose current stock is below 50 % of the initial quantity
SELECT b.batch_number, b.initial_quantity,
       (SELECT COALESCE(SUM(on_hand), 0) FROM v_batch_stock s WHERE s.batch_id = b.batch_id) AS on_hand
FROM batch b
WHERE (SELECT COALESCE(SUM(on_hand), 0) FROM v_batch_stock s WHERE s.batch_id = b.batch_id) < b.initial_quantity / 2;

-- 5. Window function: gaps in a sensor's readings longer than twice its expected interval
SELECT serial_number, recorded_at, gap
FROM (SELECT s.serial_number, r.recorded_at, s.expected_interval_s,
             r.recorded_at - LAG(r.recorded_at) OVER (PARTITION BY r.sensor_id ORDER BY r.recorded_at) AS gap
      FROM sensor_reading r JOIN sensor s USING (sensor_id)) g
WHERE gap > make_interval(secs => 2 * expected_interval_s)
ORDER BY gap DESC LIMIT 10;

-- 6. Constraint demos (each statement fails with a clear error)
INSERT INTO product (product_name, product_type, min_temp, max_temp) VALUES ('Bad', 'vaccine', 8, 2);     -- CHECK
INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival)
VALUES (999, 1, 2, now() + interval '1 day');                                                             -- FOREIGN KEY
UPDATE sensor_reading SET temperature = 4 WHERE reading_id = 1;                                            -- trigger: readings are immutable

-- 7. Transaction rollback: dispatch fails on the second batch, so the first batch's movement is undone too
BEGIN;
INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival)
VALUES (1, 1, 2, now() + interval '1 day') RETURNING shipment_id \gset
INSERT INTO shipment_batch VALUES (:shipment_id, 9, 100), (:shipment_id, 10, 99999);   -- B009 fine, B010 short
INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (8, :shipment_id, now());
SELECT dispatch_shipment(:shipment_id);          -- ERROR: Insufficient stock of batch B010
ROLLBACK;
SELECT COUNT(*) AS leftover_movements FROM batch_movement WHERE shipment_id = :shipment_id;   -- 0

-- 8. Role rule enforced inside the database, not only in the app
BEGIN;
SELECT set_config('app.current_staff_id', '2', true);   -- staff 2 = operator
UPDATE batch SET batch_status = 'released' WHERE batch_number = 'B005';   -- ERROR: Role operator may not change batch
ROLLBACK;

-- 9. Index use: the per-sensor lookup uses the UNIQUE (sensor_id, recorded_at) B-tree
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM sensor_reading WHERE sensor_id = 1 AND recorded_at BETWEEN now() - interval '1 day' AND now();
