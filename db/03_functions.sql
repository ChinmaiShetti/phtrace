-- Helper functions and the multi-step transactions (dispatch, receive).
-- Every function here runs with the caller's privileges.

-- ---------------------------------------------------------------- request context
-- The API sets app.current_staff_id per transaction with set_config(..., true).
-- After such a transaction ends, a pooled connection returns '' (not NULL), hence NULLIF.
CREATE FUNCTION current_staff_id() RETURNS integer
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.current_staff_id', true), '')::integer
$$;

CREATE FUNCTION current_staff_role() RETURNS varchar
LANGUAGE sql STABLE AS $$
    SELECT role FROM staff WHERE staff_id = current_staff_id() AND account_status = 'active'
$$;

CREATE FUNCTION severity_rank(p_severity varchar) RETURNS integer
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_severity WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'high' THEN 3 WHEN 'critical' THEN 4 END
$$;

-- Illustrative thresholds: how far beyond the configured limit a reading is.
CREATE FUNCTION severity_for_deviation(p_deviation numeric) RETURNS varchar
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN p_deviation <= 1 THEN 'low'
                WHEN p_deviation <= 3 THEN 'medium'
                WHEN p_deviation <= 5 THEN 'high'
                ELSE 'critical' END
$$;

-- ---------------------------------------------------------------- stock (derived from movements)
CREATE FUNCTION movement_sign(p_type varchar) RETURNS integer
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN p_type = 'received' THEN 1 ELSE -1 END
$$;

CREATE FUNCTION batch_stock_at(p_batch_id integer, p_facility_id integer, p_at timestamptz DEFAULT now())
RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT COALESCE(SUM(movement_sign(movement_type) * quantity_moved), 0)::integer
    FROM batch_movement
    WHERE batch_id = p_batch_id AND facility_id = p_facility_id AND movement_time <= p_at
$$;

-- Batches physically at a monitored target at a given time.
CREATE FUNCTION batches_at_target(p_shipment_id integer, p_facility_id integer, p_at timestamptz)
RETURNS TABLE (batch_id integer) LANGUAGE sql STABLE AS $$
    SELECT sb.batch_id FROM shipment_batch sb
    WHERE p_shipment_id IS NOT NULL AND sb.shipment_id = p_shipment_id
    UNION
    SELECT m.batch_id FROM batch_movement m
    WHERE p_facility_id IS NOT NULL AND m.facility_id = p_facility_id AND m.movement_time <= p_at
    GROUP BY m.batch_id
    HAVING SUM(movement_sign(m.movement_type) * m.quantity_moved) > 0
$$;

-- ---------------------------------------------------------------- shipment transactions
-- Dispatch: validate every line, lock the batches, record movements and a departure checkpoint,
-- and mark the shipment in transit. Any failure raises and rolls back the whole call.
CREATE FUNCTION dispatch_shipment(p_shipment_id integer, p_at timestamptz DEFAULT now())
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    s        shipment%ROWTYPE;
    v_origin facility.facility_name%TYPE;
    v_fridge vehicle.refrigeration_status%TYPE;
    line     record;
    v_stock  integer;
BEGIN
    SELECT * INTO s FROM shipment WHERE shipment_id = p_shipment_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Shipment % does not exist', p_shipment_id USING ERRCODE = 'no_data_found';
    END IF;
    IF s.shipment_status <> 'planned' THEN
        RAISE EXCEPTION 'Shipment % is %; only planned shipments can be dispatched', p_shipment_id, s.shipment_status;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM shipment_batch WHERE shipment_id = p_shipment_id) THEN
        RAISE EXCEPTION 'Shipment % has no batches', p_shipment_id;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM sensor_assignment WHERE shipment_id = p_shipment_id AND unassigned_at IS NULL) THEN
        RAISE EXCEPTION 'Shipment % has no active monitoring sensor', p_shipment_id;
    END IF;
    SELECT refrigeration_status INTO v_fridge FROM vehicle WHERE vehicle_id = s.vehicle_id;
    IF v_fridge = 'faulty' THEN
        RAISE EXCEPTION 'Vehicle refrigeration is faulty; shipment % cannot be dispatched', p_shipment_id;
    END IF;

    -- Lock batch rows in a fixed order so two concurrent dispatches cannot deadlock or both
    -- consume the same stock: the second waits, then sees the first one's movements.
    PERFORM 1 FROM batch b JOIN shipment_batch sb ON sb.batch_id = b.batch_id
    WHERE sb.shipment_id = p_shipment_id ORDER BY b.batch_id FOR UPDATE OF b;

    FOR line IN
        SELECT sb.batch_id, sb.quantity_shipped, b.batch_number, b.batch_status, b.expiry_date
        FROM shipment_batch sb JOIN batch b ON b.batch_id = sb.batch_id
        WHERE sb.shipment_id = p_shipment_id ORDER BY sb.batch_id
    LOOP
        IF line.batch_status NOT IN ('available', 'released') THEN
            RAISE EXCEPTION 'Batch % is %; it cannot be dispatched', line.batch_number, line.batch_status;
        END IF;
        IF line.expiry_date <= p_at::date THEN
            RAISE EXCEPTION 'Batch % expired on %; it cannot be dispatched', line.batch_number, line.expiry_date;
        END IF;
        v_stock := batch_stock_at(line.batch_id, s.origin_facility_id, p_at);
        IF v_stock < line.quantity_shipped THEN
            RAISE EXCEPTION 'Insufficient stock of batch %: % at origin, % requested',
                line.batch_number, v_stock, line.quantity_shipped;
        END IF;
        INSERT INTO batch_movement (batch_id, facility_id, shipment_id, movement_type, movement_time, quantity_moved)
        VALUES (line.batch_id, s.origin_facility_id, p_shipment_id, 'dispatched', p_at, line.quantity_shipped);
    END LOOP;

    SELECT facility_name INTO v_origin FROM facility WHERE facility_id = s.origin_facility_id;
    INSERT INTO shipment_checkpoint (shipment_id, checkpoint_no, checkpoint_time, event_type, location_description)
    SELECT p_shipment_id, COALESCE(MAX(checkpoint_no), 0) + 1, p_at, 'departure', 'Departed ' || v_origin
    FROM shipment_checkpoint WHERE shipment_id = p_shipment_id;

    UPDATE shipment SET shipment_status = 'in_transit', dispatch_time = p_at WHERE shipment_id = p_shipment_id;
END;
$$;

-- Receive: record stock arriving at the destination, an arrival checkpoint, end the sensor
-- assignments and mark the shipment delivered.
CREATE FUNCTION receive_shipment(p_shipment_id integer, p_at timestamptz DEFAULT now())
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    s      shipment%ROWTYPE;
    v_dest facility.facility_name%TYPE;
BEGIN
    SELECT * INTO s FROM shipment WHERE shipment_id = p_shipment_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Shipment % does not exist', p_shipment_id USING ERRCODE = 'no_data_found';
    END IF;
    IF s.shipment_status <> 'in_transit' THEN
        RAISE EXCEPTION 'Shipment % is %; only shipments in transit can be received', p_shipment_id, s.shipment_status;
    END IF;
    IF p_at < s.dispatch_time THEN
        RAISE EXCEPTION 'Arrival time % is before dispatch time %', p_at, s.dispatch_time;
    END IF;

    INSERT INTO batch_movement (batch_id, facility_id, shipment_id, movement_type, movement_time, quantity_moved)
    SELECT sb.batch_id, s.destination_facility_id, p_shipment_id, 'received', p_at, sb.quantity_shipped
    FROM shipment_batch sb WHERE sb.shipment_id = p_shipment_id;

    SELECT facility_name INTO v_dest FROM facility WHERE facility_id = s.destination_facility_id;
    INSERT INTO shipment_checkpoint (shipment_id, checkpoint_no, checkpoint_time, event_type, location_description)
    SELECT p_shipment_id, COALESCE(MAX(checkpoint_no), 0) + 1, p_at, 'arrival', 'Arrived at ' || v_dest
    FROM shipment_checkpoint WHERE shipment_id = p_shipment_id;

    UPDATE sensor_assignment SET unassigned_at = p_at
    WHERE shipment_id = p_shipment_id AND unassigned_at IS NULL;

    UPDATE shipment SET shipment_status = 'delivered', actual_arrival = p_at WHERE shipment_id = p_shipment_id;
END;
$$;

-- ---------------------------------------------------------------- tracing queries
-- Everything that happened to a shipment, in time order.
CREATE FUNCTION shipment_timeline(p_shipment_id integer)
RETURNS TABLE (event_time timestamptz, event_kind text, detail text) LANGUAGE sql STABLE AS $$
    SELECT c.checkpoint_time, 'checkpoint:' || c.event_type, c.location_description
    FROM shipment_checkpoint c WHERE c.shipment_id = p_shipment_id
    UNION ALL
    SELECT m.movement_time, 'movement:' || m.movement_type,
           format('%s units of batch %s at %s', m.quantity_moved, b.batch_number, f.facility_name)
    FROM batch_movement m JOIN batch b ON b.batch_id = m.batch_id JOIN facility f ON f.facility_id = m.facility_id
    WHERE m.shipment_id = p_shipment_id
    UNION ALL
    SELECT i.detected_at, 'incident:' || i.incident_type,
           format('INC%s %s (%s)', lpad(i.incident_id::text, 4, '0'), i.incident_status, i.severity)
    FROM incident i WHERE i.shipment_id = p_shipment_id
    ORDER BY 1, 2
$$;

-- Other shipments that may be affected by the same problem: same vehicle, or same origin or
-- destination as the incident's facility, overlapping the incident window.
CREATE FUNCTION related_shipments(p_incident_id integer)
RETURNS TABLE (shipment_id integer, reason text, shipment_status varchar, dispatch_time timestamptz)
LANGUAGE sql STABLE AS $$
    WITH i AS (
        SELECT inc.*, COALESCE(inc.start_time, inc.detected_at) AS w_start, COALESCE(inc.end_time, now()) AS w_end,
               s.vehicle_id AS inc_vehicle
        FROM incident inc LEFT JOIN shipment s ON s.shipment_id = inc.shipment_id
        WHERE inc.incident_id = p_incident_id
    )
    SELECT s.shipment_id,
           CASE WHEN s.vehicle_id = i.inc_vehicle THEN 'same vehicle'
                ELSE 'same facility' END,
           s.shipment_status, s.dispatch_time
    FROM i JOIN shipment s
      ON (s.vehicle_id = i.inc_vehicle
          OR s.origin_facility_id = i.facility_id OR s.destination_facility_id = i.facility_id)
    WHERE s.shipment_id IS DISTINCT FROM i.shipment_id
      AND s.dispatch_time IS NOT NULL
      AND s.dispatch_time <= i.w_end
      AND COALESCE(s.actual_arrival, now()) >= i.w_start
    ORDER BY s.dispatch_time
$$;
