-- Derived data and reports. Nothing here is stored; every number comes from the base tables.

-- Stock on hand per batch per facility
CREATE VIEW v_batch_stock AS
SELECT m.batch_id, m.facility_id, f.facility_name,
       SUM(movement_sign(m.movement_type) * m.quantity_moved)::integer AS on_hand
FROM batch_movement m JOIN facility f ON f.facility_id = m.facility_id
GROUP BY m.batch_id, m.facility_id, f.facility_name
HAVING SUM(movement_sign(m.movement_type) * m.quantity_moved) <> 0;

-- Quantity of each batch currently on the road
CREATE VIEW v_batch_in_transit AS
SELECT sb.batch_id, sb.shipment_id, sb.quantity_shipped AS quantity
FROM shipment_batch sb JOIN shipment s ON s.shipment_id = sb.shipment_id
WHERE s.shipment_status = 'in_transit';

CREATE VIEW v_batch_summary AS
SELECT b.batch_id, b.batch_number, b.product_id, p.product_name, p.product_type,
       b.manufacturing_date, b.expiry_date, b.initial_quantity, b.batch_status,
       COALESCE(st.on_hand, 0)                              AS on_hand,
       COALESCE(tr.in_transit, 0)                           AS in_transit,
       COALESCE(st.on_hand, 0) + COALESCE(tr.in_transit, 0) AS current_quantity,
       (b.expiry_date - CURRENT_DATE)                       AS days_to_expiry,
       (b.expiry_date <= CURRENT_DATE)                      AS is_expired,
       COALESCE(ic.open_incidents, 0)                       AS open_incidents
FROM batch b
JOIN product p ON p.product_id = b.product_id
LEFT JOIN (SELECT batch_id, SUM(on_hand) AS on_hand FROM v_batch_stock GROUP BY batch_id) st ON st.batch_id = b.batch_id
LEFT JOIN (SELECT batch_id, SUM(quantity) AS in_transit FROM v_batch_in_transit GROUP BY batch_id) tr ON tr.batch_id = b.batch_id
LEFT JOIN (SELECT ib.batch_id, COUNT(*) AS open_incidents
           FROM incident_batch ib JOIN incident i ON i.incident_id = ib.incident_id
           WHERE i.incident_status IN ('open', 'investigating', 'resolved')
           GROUP BY ib.batch_id) ic ON ic.batch_id = b.batch_id;

-- Effective storage range of a shipment: the tightest range that satisfies every product on board
CREATE VIEW v_shipment_limits AS
SELECT sb.shipment_id, MAX(p.min_temp) AS min_temp, MIN(p.max_temp) AS max_temp,
       MAX(p.min_humidity) AS min_humidity, MIN(p.max_humidity) AS max_humidity
FROM shipment_batch sb JOIN batch b ON b.batch_id = sb.batch_id JOIN product p ON p.product_id = b.product_id
GROUP BY sb.shipment_id;

CREATE VIEW v_shipment_summary AS
SELECT s.*, v.registration_number, o.facility_name AS origin_name, d.facility_name AS destination_name,
       COALESCE(l.lines, 0) AS batch_lines, COALESCE(l.units, 0) AS units,
       (s.shipment_status = 'in_transit' AND s.expected_arrival < now()) AS overdue
FROM shipment s
JOIN vehicle v ON v.vehicle_id = s.vehicle_id
JOIN facility o ON o.facility_id = s.origin_facility_id
JOIN facility d ON d.facility_id = s.destination_facility_id
LEFT JOIN (SELECT shipment_id, COUNT(*) AS lines, SUM(quantity_shipped) AS units
           FROM shipment_batch GROUP BY shipment_id) l ON l.shipment_id = s.shipment_id;

-- Exposure of each incident, computed from its linked breaching readings
CREATE VIEW v_incident_exposure AS
SELECT i.incident_id,
       i.start_time,
       COALESCE(i.end_time, CASE WHEN i.incident_status IN ('open', 'investigating') THEN now() END) AS effective_end,
       ROUND(EXTRACT(EPOCH FROM (COALESCE(i.end_time, now()) - i.start_time)) / 60)::integer       AS exposure_minutes,
       ROUND(EXTRACT(EPOCH FROM (COALESCE(i.end_time, now()) - i.start_time)))::integer            AS exposure_seconds,
       COUNT(r.reading_id) FILTER (WHERE ir.relevance_note IS DISTINCT FROM 'back within limits')  AS breach_readings,
       MAX(r.temperature) FILTER (WHERE ir.relevance_note IS DISTINCT FROM 'back within limits')   AS peak_temperature,
       MIN(r.temperature) FILTER (WHERE ir.relevance_note IS DISTINCT FROM 'back within limits')   AS lowest_temperature
FROM incident i
LEFT JOIN incident_reading ir ON ir.incident_id = i.incident_id
LEFT JOIN sensor_reading r ON r.reading_id = ir.reading_id
GROUP BY i.incident_id;

CREATE VIEW v_incident_summary AS
SELECT i.*, 'INC' || lpad(i.incident_id::text, 4, '0') AS incident_code,
       e.exposure_minutes, e.exposure_seconds, e.breach_readings, e.peak_temperature,
       f.facility_name, s.vehicle_id,
       (SELECT COUNT(*) FROM incident_batch ib WHERE ib.incident_id = i.incident_id) AS affected_batches,
       (SELECT string_agg(DISTINCT st.staff_name, ', ')
        FROM investigation iv JOIN staff st ON st.staff_id = iv.assigned_to
        WHERE iv.incident_id = i.incident_id) AS investigators
FROM incident i
JOIN v_incident_exposure e ON e.incident_id = i.incident_id
LEFT JOIN facility f ON f.facility_id = i.facility_id
LEFT JOIN shipment s ON s.shipment_id = i.shipment_id;

-- ---------------------------------------------------------------- dashboard (one row)
CREATE VIEW v_dashboard AS
SELECT
    (SELECT COUNT(*) FROM shipment WHERE shipment_status = 'in_transit')                       AS active_shipments,
    (SELECT COUNT(*) FROM incident WHERE incident_status IN ('open', 'investigating'))         AS open_incidents,
    (SELECT COUNT(DISTINCT ib.batch_id) FROM incident_batch ib JOIN incident i ON i.incident_id = ib.incident_id
      WHERE i.incident_status IN ('open', 'investigating', 'resolved'))                        AS batches_under_investigation,
    (SELECT COUNT(*) FROM corrective_action
      WHERE action_status IN ('pending', 'in_progress') AND due_date < CURRENT_DATE)           AS overdue_actions,
    (SELECT COUNT(*) FROM incident WHERE incident_type IN ('temperature_excursion', 'humidity_excursion')
      AND detected_at >= now() - interval '7 days')                                            AS excursions_last_7_days,
    (SELECT COUNT(*) FROM shipment WHERE shipment_status = 'in_transit' AND expected_arrival < now())
                                                                                               AS overdue_arrivals,
    (SELECT COUNT(*) FROM batch WHERE batch_status IN ('on_hold', 'quarantined'))              AS batches_on_hold;

-- ---------------------------------------------------------------- reports
CREATE VIEW v_report_incidents_by_type_severity AS
SELECT incident_type, severity, COUNT(*) AS incidents,
       COUNT(*) FILTER (WHERE incident_status IN ('open', 'investigating')) AS still_active
FROM incident
GROUP BY incident_type, severity
ORDER BY incident_type, severity_rank(severity) DESC;

CREATE VIEW v_report_batch_incidents AS
SELECT b.batch_number, p.product_name, b.batch_status, COUNT(ib.incident_id) AS incidents,
       MAX(i.detected_at) AS last_incident,
       string_agg(DISTINCT ib.assessment_status, ', ') AS assessment_states
FROM incident_batch ib
JOIN batch b ON b.batch_id = ib.batch_id
JOIN product p ON p.product_id = b.product_id
JOIN incident i ON i.incident_id = ib.incident_id
GROUP BY b.batch_number, p.product_name, b.batch_status
ORDER BY incidents DESC, last_incident DESC;

CREATE VIEW v_report_vehicle_repeat_incidents AS
SELECT v.registration_number, v.vehicle_type, v.refrigeration_status, COUNT(i.incident_id) AS incidents,
       MIN(i.detected_at) AS first_incident, MAX(i.detected_at) AS last_incident
FROM incident i
JOIN shipment s ON s.shipment_id = i.shipment_id
JOIN vehicle v ON v.vehicle_id = s.vehicle_id
GROUP BY v.registration_number, v.vehicle_type, v.refrigeration_status
HAVING COUNT(i.incident_id) > 1
ORDER BY incidents DESC;

CREATE VIEW v_report_pending_actions AS
SELECT ca.action_id, 'INC' || lpad(iv.incident_id::text, 4, '0') AS incident_code, ca.action_description,
       st.staff_name AS assigned_to, ca.due_date, ca.action_status,
       (ca.due_date < CURRENT_DATE) AS overdue
FROM corrective_action ca
JOIN investigation iv ON iv.investigation_id = ca.investigation_id
JOIN staff st ON st.staff_id = ca.assigned_to
WHERE ca.action_status IN ('pending', 'in_progress')
ORDER BY ca.due_date NULLS LAST;

CREATE VIEW v_report_expiring_batches AS
SELECT batch_number, product_name, expiry_date, days_to_expiry, current_quantity, batch_status
FROM v_batch_summary
WHERE days_to_expiry <= 60 AND current_quantity > 0
ORDER BY expiry_date;

-- Gaps: consecutive readings further apart than twice the sensor's expected interval
CREATE VIEW v_report_sensor_quality AS
WITH ordered AS (
    SELECT r.sensor_id, r.quality_status,
           EXTRACT(EPOCH FROM r.recorded_at - LAG(r.recorded_at) OVER (PARTITION BY r.sensor_id ORDER BY r.recorded_at)) AS gap_s
    FROM sensor_reading r
)
SELECT s.serial_number, s.sensor_type, s.installation_status, s.expected_interval_s,
       COUNT(o.sensor_id)                                                  AS readings,
       COUNT(*) FILTER (WHERE o.quality_status = 'invalid')                AS invalid,
       COUNT(*) FILTER (WHERE o.quality_status = 'suspicious')             AS suspicious,
       COUNT(*) FILTER (WHERE o.gap_s > 2 * s.expected_interval_s)         AS gaps,
       ROUND(COALESCE(MAX(o.gap_s), 0) / 60)::integer                      AS longest_gap_minutes
FROM sensor s LEFT JOIN ordered o ON o.sensor_id = s.sensor_id
GROUP BY s.sensor_id, s.serial_number, s.sensor_type, s.installation_status, s.expected_interval_s
ORDER BY gaps DESC, invalid DESC, s.serial_number;
