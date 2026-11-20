-- Triggers: data validation, excursion detection, workflow rules and auditing.

-- ---------------------------------------------------------------- shipment lines
-- Lines can only change while the shipment is planned, and every product on board must share
-- an overlapping storage-temperature range (otherwise no single setting keeps them all in range).
CREATE FUNCTION trg_shipment_batch_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_shipment integer := CASE WHEN TG_OP = 'DELETE' THEN OLD.shipment_id ELSE NEW.shipment_id END;
    v_status   varchar;
    v_min      numeric;
    v_max      numeric;
    p          product%ROWTYPE;
BEGIN
    SELECT shipment_status INTO v_status FROM shipment WHERE shipment_id = v_shipment;
    IF v_status IS DISTINCT FROM 'planned' THEN
        RAISE EXCEPTION 'Shipment % is %; batches can only be changed while it is planned', v_shipment, v_status;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    SELECT pr.* INTO p FROM batch b JOIN product pr ON pr.product_id = b.product_id WHERE b.batch_id = NEW.batch_id;
    SELECT MAX(pr.min_temp), MIN(pr.max_temp) INTO v_min, v_max
    FROM shipment_batch sb
    JOIN batch b ON b.batch_id = sb.batch_id
    JOIN product pr ON pr.product_id = b.product_id
    WHERE sb.shipment_id = NEW.shipment_id AND sb.batch_id <> NEW.batch_id;

    IF v_min IS NOT NULL AND GREATEST(v_min, p.min_temp) >= LEAST(v_max, p.max_temp) THEN
        RAISE EXCEPTION 'Product % needs % to % °C, which does not overlap the shipment''s current range % to % °C',
            p.product_name, p.min_temp, p.max_temp, v_min, v_max;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER shipment_batch_check BEFORE INSERT OR UPDATE OR DELETE ON shipment_batch
    FOR EACH ROW EXECUTE FUNCTION trg_shipment_batch_check();

-- ---------------------------------------------------------------- sensor assignment
CREATE FUNCTION trg_sensor_assignment_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_sensor_status varchar;
    v_ship_status   varchar;
BEGIN
    SELECT installation_status INTO v_sensor_status FROM sensor WHERE sensor_id = NEW.sensor_id;
    IF TG_OP = 'INSERT' AND v_sensor_status <> 'active' THEN
        RAISE EXCEPTION 'Sensor % is %; only active sensors can be assigned', NEW.sensor_id, v_sensor_status;
    END IF;
    IF NEW.shipment_id IS NOT NULL AND TG_OP = 'INSERT' THEN
        SELECT shipment_status INTO v_ship_status FROM shipment WHERE shipment_id = NEW.shipment_id;
        IF v_ship_status IN ('delivered', 'cancelled') THEN
            RAISE EXCEPTION 'Shipment % is %; sensors cannot be assigned to it', NEW.shipment_id, v_ship_status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER sensor_assignment_check BEFORE INSERT OR UPDATE ON sensor_assignment
    FOR EACH ROW EXECUTE FUNCTION trg_sensor_assignment_check();

-- ---------------------------------------------------------------- sensor readings
-- Classify on arrival. Raw values are always stored; implausible ones are only marked.
CREATE FUNCTION trg_reading_classify() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_sensor_status varchar;
BEGIN
    IF (NEW.temperature IS NOT NULL AND (NEW.temperature < -80 OR NEW.temperature > 80))
       OR (NEW.humidity IS NOT NULL AND (NEW.humidity < 0 OR NEW.humidity > 100))
       OR NEW.recorded_at > NEW.ingested_at + interval '5 minutes' THEN
        NEW.quality_status := 'invalid';
    ELSIF NEW.quality_status = 'valid' THEN
        SELECT installation_status INTO v_sensor_status FROM sensor WHERE sensor_id = NEW.sensor_id;
        IF v_sensor_status = 'faulty' THEN
            NEW.quality_status := 'suspicious';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER reading_classify BEFORE INSERT ON sensor_reading
    FOR EACH ROW EXECUTE FUNCTION trg_reading_classify();

-- Original measurements are never changed or deleted; only the quality flag may be updated.
CREATE FUNCTION trg_reading_protect() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Sensor readings cannot be deleted (reading %)', OLD.reading_id;
    END IF;
    IF NEW.sensor_id IS DISTINCT FROM OLD.sensor_id OR NEW.recorded_at IS DISTINCT FROM OLD.recorded_at
       OR NEW.ingested_at IS DISTINCT FROM OLD.ingested_at OR NEW.temperature IS DISTINCT FROM OLD.temperature
       OR NEW.humidity IS DISTINCT FROM OLD.humidity THEN
        RAISE EXCEPTION 'Original values of reading % cannot be changed; only quality_status may be updated',
            OLD.reading_id;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER reading_protect BEFORE UPDATE OR DELETE ON sensor_reading
    FOR EACH ROW EXECUTE FUNCTION trg_reading_protect();

-- ---------------------------------------------------------------- excursion detection
-- Open a new incident or add to the active one for this target, then link the reading and batches.
CREATE FUNCTION record_excursion(p_type varchar, p_shipment integer, p_facility integer, p_reading sensor_reading,
                                 p_deviation numeric, p_batches integer[], p_note text)
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE
    v_id       integer;
    v_severity varchar;
    v_new_sev  varchar := severity_for_deviation(p_deviation);
BEGIN
    -- serialise detection per target so two readings cannot both create an incident
    PERFORM pg_advisory_xact_lock(hashtext('incident:' || p_type || ':' || COALESCE('s' || p_shipment, 'f' || p_facility)));

    SELECT incident_id, severity INTO v_id, v_severity FROM incident
    WHERE incident_type = p_type AND incident_status IN ('open', 'investigating')
      AND ((p_shipment IS NOT NULL AND shipment_id = p_shipment) OR (p_facility IS NOT NULL AND facility_id = p_facility))
    FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO incident (incident_type, severity, detection_source, shipment_id, facility_id,
                              detected_at, start_time, description)
        VALUES (p_type, v_new_sev, 'automatic', p_shipment, p_facility, p_reading.ingested_at, p_reading.recorded_at,
                format('Automatic: %s detected by sensor %s at %s', replace(p_type, '_', ' '),
                       p_reading.sensor_id, to_char(p_reading.recorded_at, 'YYYY-MM-DD HH24:MI TZ')))
        RETURNING incident_id INTO v_id;
    ELSE
        UPDATE incident
        SET severity = CASE WHEN severity_rank(v_new_sev) > severity_rank(severity) THEN v_new_sev ELSE severity END,
            end_time = NULL
        WHERE incident_id = v_id;
    END IF;

    INSERT INTO incident_reading (incident_id, reading_id, relevance_note)
    VALUES (v_id, p_reading.reading_id, p_note) ON CONFLICT DO NOTHING;
    INSERT INTO incident_batch (incident_id, batch_id)
    SELECT v_id, unnest(p_batches) ON CONFLICT DO NOTHING;
    RETURN v_id;
END;
$$;

-- An in-range reading ends an active excursion (end_time) and is linked as evidence of recovery.
CREATE FUNCTION end_excursion(p_type varchar, p_shipment integer, p_facility integer, p_reading sensor_reading)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    v_id integer;
BEGIN
    UPDATE incident SET end_time = p_reading.recorded_at
    WHERE incident_type = p_type AND incident_status IN ('open', 'investigating') AND end_time IS NULL
      AND start_time <= p_reading.recorded_at
      AND ((p_shipment IS NOT NULL AND shipment_id = p_shipment) OR (p_facility IS NOT NULL AND facility_id = p_facility))
    RETURNING incident_id INTO v_id;
    IF v_id IS NOT NULL THEN
        INSERT INTO incident_reading (incident_id, reading_id, relevance_note)
        VALUES (v_id, p_reading.reading_id, 'back within limits') ON CONFLICT DO NOTHING;
    END IF;
END;
$$;

CREATE FUNCTION trg_reading_evaluate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_ship      integer;
    v_fac       integer;
    t_batches   integer[] := '{}';
    t_dev       numeric := 0;
    h_batches   integer[] := '{}';
    h_dev       numeric := 0;
    h_watched   boolean := false;
    r           record;
    d           numeric;
BEGIN
    IF NEW.quality_status <> 'valid' THEN
        RETURN NULL;
    END IF;
    SELECT shipment_id, facility_id INTO v_ship, v_fac FROM sensor_assignment
    WHERE sensor_id = NEW.sensor_id AND assigned_at <= NEW.recorded_at
      AND (unassigned_at IS NULL OR NEW.recorded_at < unassigned_at);
    IF NOT FOUND THEN
        RETURN NULL;   -- reading from an unassigned sensor: stored, but nothing to evaluate
    END IF;

    FOR r IN
        SELECT t.batch_id, p.min_temp, p.max_temp, p.min_humidity, p.max_humidity
        FROM batches_at_target(v_ship, v_fac, NEW.recorded_at) t
        JOIN batch b ON b.batch_id = t.batch_id
        JOIN product p ON p.product_id = b.product_id
    LOOP
        IF NEW.temperature IS NOT NULL THEN
            d := GREATEST(NEW.temperature - r.max_temp, r.min_temp - NEW.temperature, 0);
            IF d > 0 THEN
                t_batches := t_batches || r.batch_id;
                t_dev := GREATEST(t_dev, d);
            END IF;
        END IF;
        IF NEW.humidity IS NOT NULL AND r.min_humidity IS NOT NULL THEN
            h_watched := true;
            d := GREATEST(NEW.humidity - r.max_humidity, r.min_humidity - NEW.humidity, 0);
            IF d > 0 THEN
                h_batches := h_batches || r.batch_id;
                h_dev := GREATEST(h_dev, d / 5);   -- 5 % RH counted like 1 °C for severity
            END IF;
        END IF;
    END LOOP;

    IF NEW.temperature IS NOT NULL THEN
        IF cardinality(t_batches) > 0 THEN
            PERFORM record_excursion('temperature_excursion', v_ship, v_fac, NEW, t_dev, t_batches,
                format('%s °C, %s °C outside limit', NEW.temperature, t_dev));
        ELSE
            PERFORM end_excursion('temperature_excursion', v_ship, v_fac, NEW);
        END IF;
    END IF;
    IF h_watched THEN
        IF cardinality(h_batches) > 0 THEN
            PERFORM record_excursion('humidity_excursion', v_ship, v_fac, NEW, h_dev, h_batches,
                format('%s %% RH outside limit', NEW.humidity));
        ELSE
            PERFORM end_excursion('humidity_excursion', v_ship, v_fac, NEW);
        END IF;
    END IF;
    RETURN NULL;
END;
$$;
CREATE TRIGGER reading_evaluate AFTER INSERT ON sensor_reading
    FOR EACH ROW EXECUTE FUNCTION trg_reading_evaluate();

-- ---------------------------------------------------------------- batch status workflow
-- A status change must be listed in batch_status_transition for the acting staff member's role.
CREATE FUNCTION trg_batch_status_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_role varchar := current_staff_role();
BEGIN
    IF NEW.batch_status IS DISTINCT FROM OLD.batch_status THEN
        IF v_role IS NULL THEN
            RAISE EXCEPTION 'Batch status changes require an authenticated staff member';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM batch_status_transition
                       WHERE from_status = OLD.batch_status AND to_status = NEW.batch_status AND role = v_role) THEN
            RAISE EXCEPTION 'Role % may not change batch % from % to %',
                v_role, OLD.batch_number, OLD.batch_status, NEW.batch_status
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER batch_status_check BEFORE UPDATE OF batch_status ON batch
    FOR EACH ROW EXECUTE FUNCTION trg_batch_status_check();

-- ---------------------------------------------------------------- incident lifecycle
CREATE FUNCTION trg_incident_lifecycle() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.incident_status IS NOT DISTINCT FROM OLD.incident_status THEN
        RETURN NEW;
    END IF;
    IF (OLD.incident_status, NEW.incident_status) NOT IN
       (('open', 'investigating'), ('investigating', 'resolved'), ('resolved', 'closed'), ('resolved', 'investigating')) THEN
        RAISE EXCEPTION 'Incident % cannot move from % to %', OLD.incident_id, OLD.incident_status, NEW.incident_status;
    END IF;

    IF NEW.incident_status = 'resolved' THEN
        IF NOT EXISTS (SELECT 1 FROM investigation WHERE incident_id = NEW.incident_id) THEN
            RAISE EXCEPTION 'Incident % has no investigation', NEW.incident_id;
        END IF;
        IF EXISTS (SELECT 1 FROM investigation WHERE incident_id = NEW.incident_id
                   AND investigation_status <> 'completed') THEN
            RAISE EXCEPTION 'Incident % still has an investigation that is not completed', NEW.incident_id;
        END IF;
    END IF;

    IF NEW.incident_status = 'closed' THEN
        IF current_staff_role() IS DISTINCT FROM 'quality_manager' THEN
            RAISE EXCEPTION 'Only a quality manager can close an incident' USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF EXISTS (SELECT 1 FROM corrective_action ca JOIN investigation iv ON iv.investigation_id = ca.investigation_id
                   WHERE iv.incident_id = NEW.incident_id AND ca.action_status IN ('pending', 'in_progress')) THEN
            RAISE EXCEPTION 'Incident % has corrective actions that are not finished', NEW.incident_id;
        END IF;
        IF EXISTS (SELECT 1 FROM incident_batch WHERE incident_id = NEW.incident_id
                   AND assessment_status <> 'assessed') THEN
            RAISE EXCEPTION 'Incident % has affected batches that are not assessed', NEW.incident_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER incident_lifecycle BEFORE UPDATE OF incident_status ON incident
    FOR EACH ROW EXECUTE FUNCTION trg_incident_lifecycle();

-- ---------------------------------------------------------------- investigation and action rules
CREATE FUNCTION trg_investigation_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_status varchar;
    v_role   varchar;
BEGIN
    SELECT incident_status INTO v_status FROM incident WHERE incident_id = NEW.incident_id;
    IF TG_OP = 'INSERT' AND v_status = 'closed' THEN
        RAISE EXCEPTION 'Incident % is closed', NEW.incident_id;
    END IF;
    SELECT role INTO v_role FROM staff WHERE staff_id = NEW.assigned_to AND account_status = 'active';
    IF v_role IS NULL OR v_role NOT IN ('investigator', 'quality_manager') THEN
        RAISE EXCEPTION 'Staff % cannot be assigned an investigation', NEW.assigned_to;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER investigation_check BEFORE INSERT OR UPDATE OF assigned_to ON investigation
    FOR EACH ROW EXECUTE FUNCTION trg_investigation_check();

-- Assigning the first investigation moves the incident from open to investigating.
CREATE FUNCTION trg_investigation_opened() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE incident SET incident_status = 'investigating'
    WHERE incident_id = NEW.incident_id AND incident_status = 'open';
    RETURN NULL;
END;
$$;
CREATE TRIGGER investigation_opened AFTER INSERT ON investigation
    FOR EACH ROW EXECUTE FUNCTION trg_investigation_opened();

CREATE FUNCTION trg_action_check() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM investigation iv JOIN incident i ON i.incident_id = iv.incident_id
               WHERE iv.investigation_id = NEW.investigation_id AND i.incident_status = 'closed') THEN
        RAISE EXCEPTION 'The incident for investigation % is closed', NEW.investigation_id;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM staff WHERE staff_id = NEW.assigned_to AND account_status = 'active') THEN
        RAISE EXCEPTION 'Staff % is not an active user', NEW.assigned_to;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER action_check BEFORE INSERT OR UPDATE ON corrective_action
    FOR EACH ROW EXECUTE FUNCTION trg_action_check();

-- ---------------------------------------------------------------- audit log
-- SECURITY DEFINER: runs as the schema owner, so the application role needs no INSERT on audit_log.
-- Trigger arguments name the primary-key columns.
CREATE FUNCTION trg_audit() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_row  jsonb := to_jsonb(CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END);
    v_old  jsonb := to_jsonb(OLD) - 'password_hash';   -- never copy password hashes into the log
    v_new  jsonb := to_jsonb(NEW) - 'password_hash';
    v_pk   text := '';
    i      integer;
BEGIN
    IF TG_OP = 'UPDATE' AND to_jsonb(NEW) = to_jsonb(OLD) THEN
        RETURN NULL;
    END IF;
    FOR i IN 0 .. TG_NARGS - 1 LOOP
        v_pk := v_pk || CASE WHEN i > 0 THEN ',' ELSE '' END || (v_row ->> TG_ARGV[i]);
    END LOOP;
    INSERT INTO audit_log (table_name, row_pk, action, old_data, new_data, changed_by, reason)
    VALUES (TG_TABLE_NAME, v_pk, TG_OP,
            CASE WHEN TG_OP <> 'INSERT' THEN v_old END,
            CASE WHEN TG_OP <> 'DELETE' THEN v_new END,
            current_staff_id(), NULLIF(current_setting('app.change_reason', true), ''));
    RETURN NULL;
END;
$$;

CREATE TRIGGER audit_batch             AFTER INSERT OR UPDATE OR DELETE ON batch
    FOR EACH ROW EXECUTE FUNCTION trg_audit('batch_id');
CREATE TRIGGER audit_shipment          AFTER INSERT OR UPDATE OR DELETE ON shipment
    FOR EACH ROW EXECUTE FUNCTION trg_audit('shipment_id');
CREATE TRIGGER audit_incident          AFTER INSERT OR UPDATE OR DELETE ON incident
    FOR EACH ROW EXECUTE FUNCTION trg_audit('incident_id');
CREATE TRIGGER audit_incident_batch    AFTER INSERT OR UPDATE OR DELETE ON incident_batch
    FOR EACH ROW EXECUTE FUNCTION trg_audit('incident_id', 'batch_id');
CREATE TRIGGER audit_investigation     AFTER INSERT OR UPDATE OR DELETE ON investigation
    FOR EACH ROW EXECUTE FUNCTION trg_audit('investigation_id');
CREATE TRIGGER audit_corrective_action AFTER INSERT OR UPDATE OR DELETE ON corrective_action
    FOR EACH ROW EXECUTE FUNCTION trg_audit('action_id');
CREATE TRIGGER audit_sensor_reading    AFTER UPDATE ON sensor_reading
    FOR EACH ROW EXECUTE FUNCTION trg_audit('reading_id');
CREATE TRIGGER audit_staff             AFTER INSERT OR UPDATE OR DELETE ON staff
    FOR EACH ROW EXECUTE FUNCTION trg_audit('staff_id');
