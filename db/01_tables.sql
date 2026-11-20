-- PharmaTrace relational schema (3NF). Table and column names follow the lab manual, Section 6.5.
-- All timestamps are TIMESTAMPTZ (stored in UTC, shown in local time by the client).

-- ---------------------------------------------------------------- staff
CREATE TABLE staff (
    staff_id        integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    staff_name      varchar(100) NOT NULL,
    email           varchar(254) NOT NULL,
    password_hash   text         NOT NULL,
    role            varchar(20)  NOT NULL
        CHECK (role IN ('operator', 'investigator', 'quality_manager', 'admin')),
    account_status  varchar(10)  NOT NULL DEFAULT 'active'
        CHECK (account_status IN ('active', 'inactive'))
);
CREATE UNIQUE INDEX staff_email_uq ON staff (lower(email));

-- ---------------------------------------------------------------- product and batch
CREATE TABLE product (
    product_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name  varchar(120) NOT NULL UNIQUE,
    product_type  varchar(20)  NOT NULL
        CHECK (product_type IN ('vaccine', 'biologic', 'medicine', 'other')),
    min_temp      numeric(5, 2) NOT NULL,
    max_temp      numeric(5, 2) NOT NULL,
    min_humidity  numeric(5, 2),
    max_humidity  numeric(5, 2),
    CONSTRAINT product_temp_range     CHECK (min_temp < max_temp),
    CONSTRAINT product_humidity_pair  CHECK ((min_humidity IS NULL) = (max_humidity IS NULL)),
    CONSTRAINT product_humidity_range CHECK (
        min_humidity IS NULL OR (min_humidity >= 0 AND max_humidity <= 100 AND min_humidity < max_humidity))
);

CREATE TABLE batch (
    batch_id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_number        varchar(40) NOT NULL UNIQUE,
    product_id          integer     NOT NULL REFERENCES product ON DELETE RESTRICT,
    manufacturing_date  date        NOT NULL,
    expiry_date         date        NOT NULL,
    initial_quantity    integer     NOT NULL CHECK (initial_quantity > 0),
    batch_status        varchar(15) NOT NULL DEFAULT 'available'
        CHECK (batch_status IN ('available', 'on_hold', 'quarantined', 'released', 'returned', 'disposed')),
    CONSTRAINT batch_dates CHECK (expiry_date > manufacturing_date)
);

-- ---------------------------------------------------------------- facility and vehicle
CREATE TABLE facility (
    facility_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    facility_name  varchar(120) NOT NULL UNIQUE,
    facility_type  varchar(25)  NOT NULL
        CHECK (facility_type IN ('warehouse', 'distribution_centre', 'hospital', 'clinic', 'pharmacy')),
    street         varchar(200) NOT NULL,
    city           varchar(80)  NOT NULL,
    pincode        varchar(6)   NOT NULL CHECK (pincode ~ '^[1-9][0-9]{5}$')
);

-- multivalued attribute phone_number of FACILITY
CREATE TABLE facility_phone (
    facility_id   integer     NOT NULL REFERENCES facility ON DELETE CASCADE,
    phone_number  varchar(20) NOT NULL CHECK (phone_number ~ '^[0-9+ -]{6,20}$'),
    PRIMARY KEY (facility_id, phone_number)
);

CREATE TABLE vehicle (
    vehicle_id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    registration_number   varchar(15) NOT NULL UNIQUE,
    vehicle_type          varchar(25) NOT NULL
        CHECK (vehicle_type IN ('refrigerated_van', 'refrigerated_truck', 'insulated_van')),
    refrigeration_status  varchar(12) NOT NULL DEFAULT 'operational'
        CHECK (refrigeration_status IN ('operational', 'degraded', 'faulty'))
);

-- ---------------------------------------------------------------- shipment
CREATE TABLE shipment (
    shipment_id              integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id               integer NOT NULL REFERENCES vehicle ON DELETE RESTRICT,
    origin_facility_id       integer NOT NULL REFERENCES facility ON DELETE RESTRICT,
    destination_facility_id  integer NOT NULL REFERENCES facility ON DELETE RESTRICT,
    dispatch_time            timestamptz,
    expected_arrival         timestamptz NOT NULL,
    actual_arrival           timestamptz,
    shipment_status          varchar(12) NOT NULL DEFAULT 'planned'
        CHECK (shipment_status IN ('planned', 'in_transit', 'delivered', 'cancelled')),
    CONSTRAINT shipment_route CHECK (origin_facility_id <> destination_facility_id),
    CONSTRAINT shipment_status_times CHECK (
           (shipment_status = 'planned'    AND dispatch_time IS NULL     AND actual_arrival IS NULL)
        OR (shipment_status = 'in_transit' AND dispatch_time IS NOT NULL AND actual_arrival IS NULL)
        OR (shipment_status = 'delivered'  AND dispatch_time IS NOT NULL AND actual_arrival IS NOT NULL)
        OR (shipment_status = 'cancelled'  AND actual_arrival IS NULL)),
    CONSTRAINT shipment_arrival_after_dispatch CHECK (actual_arrival IS NULL OR actual_arrival >= dispatch_time)
);

-- M:N between SHIPMENT and BATCH (relationship CONTAINS)
CREATE TABLE shipment_batch (
    shipment_id       integer NOT NULL REFERENCES shipment ON DELETE CASCADE,
    batch_id          integer NOT NULL REFERENCES batch ON DELETE RESTRICT,
    quantity_shipped  integer NOT NULL CHECK (quantity_shipped > 0),
    PRIMARY KEY (shipment_id, batch_id)
);

-- weak entity: identified by its shipment plus checkpoint_no
CREATE TABLE shipment_checkpoint (
    shipment_id           integer      NOT NULL REFERENCES shipment ON DELETE CASCADE,
    checkpoint_no         integer      NOT NULL CHECK (checkpoint_no > 0),
    checkpoint_time       timestamptz  NOT NULL,
    event_type            varchar(15)  NOT NULL
        CHECK (event_type IN ('departure', 'transit_scan', 'inspection', 'delay', 'arrival')),
    location_description  varchar(200) NOT NULL,
    PRIMARY KEY (shipment_id, checkpoint_no)
);

-- movement history; current stock is derived from it (never stored)
CREATE TABLE batch_movement (
    movement_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id        integer     NOT NULL REFERENCES batch ON DELETE RESTRICT,
    facility_id     integer     NOT NULL REFERENCES facility ON DELETE RESTRICT,
    shipment_id     integer     REFERENCES shipment ON DELETE RESTRICT,
    movement_type   varchar(12) NOT NULL
        CHECK (movement_type IN ('received', 'dispatched', 'returned', 'disposed')),
    movement_time   timestamptz NOT NULL,
    quantity_moved  integer     NOT NULL CHECK (quantity_moved > 0),
    CONSTRAINT movement_dispatch_needs_shipment CHECK (movement_type <> 'dispatched' OR shipment_id IS NOT NULL)
);

-- ---------------------------------------------------------------- sensors and readings
CREATE TABLE sensor (
    sensor_id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    serial_number        varchar(40) NOT NULL UNIQUE,
    sensor_type          varchar(15) NOT NULL
        CHECK (sensor_type IN ('temperature', 'humidity', 'temp_humidity')),
    installation_status  varchar(10) NOT NULL DEFAULT 'active'
        CHECK (installation_status IN ('active', 'inactive', 'faulty')),
    expected_interval_s  integer     NOT NULL DEFAULT 300 CHECK (expected_interval_s > 0)
);

CREATE TABLE sensor_assignment (
    assignment_id  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor_id      integer     NOT NULL REFERENCES sensor ON DELETE RESTRICT,
    shipment_id    integer     REFERENCES shipment ON DELETE RESTRICT,
    facility_id    integer     REFERENCES facility ON DELETE RESTRICT,
    assigned_at    timestamptz NOT NULL,
    unassigned_at  timestamptz,
    CONSTRAINT assignment_one_target CHECK (num_nonnulls(shipment_id, facility_id) = 1),
    CONSTRAINT assignment_period     CHECK (unassigned_at IS NULL OR unassigned_at > assigned_at),
    -- the same sensor can never be in two places at once
    CONSTRAINT assignment_no_overlap EXCLUDE USING gist (
        sensor_id WITH =,
        tstzrange(assigned_at, unassigned_at, '[)') WITH &&)
);

CREATE TABLE sensor_reading (
    reading_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor_id       integer      NOT NULL REFERENCES sensor ON DELETE RESTRICT,
    recorded_at     timestamptz  NOT NULL,
    ingested_at     timestamptz  NOT NULL DEFAULT now(),
    temperature     numeric(6, 2),
    humidity        numeric(6, 2),
    quality_status  varchar(10)  NOT NULL DEFAULT 'valid'
        CHECK (quality_status IN ('valid', 'suspicious', 'invalid')),
    CONSTRAINT reading_unique_per_sensor UNIQUE (sensor_id, recorded_at),
    CONSTRAINT reading_has_value CHECK (num_nonnulls(temperature, humidity) >= 1)
);

-- ---------------------------------------------------------------- incidents
CREATE TABLE incident (
    incident_id       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_type     varchar(25) NOT NULL
        CHECK (incident_type IN ('temperature_excursion', 'humidity_excursion', 'sensor_failure', 'other')),
    severity          varchar(10) NOT NULL DEFAULT 'medium'
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    detection_source  varchar(10) NOT NULL CHECK (detection_source IN ('automatic', 'manual')),
    shipment_id       integer REFERENCES shipment ON DELETE RESTRICT,
    facility_id       integer REFERENCES facility ON DELETE RESTRICT,
    reported_by       integer REFERENCES staff ON DELETE RESTRICT,
    detected_at       timestamptz NOT NULL DEFAULT now(),
    start_time        timestamptz,
    end_time          timestamptz,
    incident_status   varchar(15) NOT NULL DEFAULT 'open'
        CHECK (incident_status IN ('open', 'investigating', 'resolved', 'closed')),
    description       text NOT NULL DEFAULT '',
    CONSTRAINT incident_one_target   CHECK (num_nonnulls(shipment_id, facility_id) = 1),
    CONSTRAINT incident_period       CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time),
    CONSTRAINT incident_manual_reporter CHECK (detection_source <> 'manual' OR reported_by IS NOT NULL)
);
-- at most one active incident of each type per shipment / per facility
CREATE UNIQUE INDEX incident_active_shipment_uq ON incident (shipment_id, incident_type)
    WHERE shipment_id IS NOT NULL AND incident_status IN ('open', 'investigating');
CREATE UNIQUE INDEX incident_active_facility_uq ON incident (facility_id, incident_type)
    WHERE facility_id IS NOT NULL AND incident_status IN ('open', 'investigating');

-- M:N between INCIDENT and SENSOR_READING (relationship EVIDENCED_BY)
CREATE TABLE incident_reading (
    incident_id     integer NOT NULL REFERENCES incident ON DELETE CASCADE,
    reading_id      bigint  NOT NULL REFERENCES sensor_reading ON DELETE RESTRICT,
    relevance_note  varchar(200),
    PRIMARY KEY (incident_id, reading_id)
);

-- M:N between INCIDENT and BATCH (relationship AFFECTS)
CREATE TABLE incident_batch (
    incident_id        integer NOT NULL REFERENCES incident ON DELETE CASCADE,
    batch_id           integer NOT NULL REFERENCES batch ON DELETE RESTRICT,
    assessment_status  varchar(20) NOT NULL DEFAULT 'pending_review'
        CHECK (assessment_status IN ('pending_review', 'under_assessment', 'assessed')),
    assessment_note    text,
    PRIMARY KEY (incident_id, batch_id),
    CONSTRAINT assessed_needs_note CHECK (assessment_status <> 'assessed' OR assessment_note IS NOT NULL)
);

-- ---------------------------------------------------------------- investigation and corrective action
CREATE TABLE investigation (
    investigation_id      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id           integer     NOT NULL REFERENCES incident ON DELETE RESTRICT,
    assigned_to           integer     NOT NULL REFERENCES staff ON DELETE RESTRICT,
    started_at            timestamptz NOT NULL DEFAULT now(),
    completed_at          timestamptz,
    findings              text,
    investigation_status  varchar(12) NOT NULL DEFAULT 'assigned'
        CHECK (investigation_status IN ('assigned', 'in_progress', 'completed')),
    CONSTRAINT investigation_completion CHECK ((investigation_status = 'completed') = (completed_at IS NOT NULL)),
    CONSTRAINT investigation_findings   CHECK (investigation_status <> 'completed' OR findings IS NOT NULL),
    CONSTRAINT investigation_period     CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE corrective_action (
    action_id           integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    investigation_id    integer     NOT NULL REFERENCES investigation ON DELETE RESTRICT,
    assigned_to         integer     NOT NULL REFERENCES staff ON DELETE RESTRICT,
    action_description  text        NOT NULL CHECK (length(trim(action_description)) > 0),
    due_date            date,
    completed_at        timestamptz,
    action_status       varchar(12) NOT NULL DEFAULT 'pending'
        CHECK (action_status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    CONSTRAINT action_completion CHECK ((action_status = 'completed') = (completed_at IS NOT NULL))
);

-- ---------------------------------------------------------------- supporting tables
-- workflow rules: which role may move a batch from one status to another
CREATE TABLE batch_status_transition (
    from_status  varchar(15) NOT NULL,
    to_status    varchar(15) NOT NULL,
    role         varchar(20) NOT NULL CHECK (role IN ('operator', 'investigator', 'quality_manager', 'admin')),
    PRIMARY KEY (from_status, to_status, role),
    CHECK (from_status <> to_status)
);

CREATE TABLE audit_log (
    audit_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_name  text        NOT NULL,
    row_pk      text        NOT NULL,
    action      varchar(6)  NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data    jsonb,
    new_data    jsonb,
    changed_by  integer REFERENCES staff ON DELETE SET NULL,
    reason      text,
    changed_at  timestamptz NOT NULL DEFAULT now()
);

INSERT INTO batch_status_transition (from_status, to_status, role) VALUES
    ('available',   'on_hold',     'investigator'),
    ('available',   'on_hold',     'quality_manager'),
    ('available',   'quarantined', 'quality_manager'),
    ('on_hold',     'quarantined', 'quality_manager'),
    ('on_hold',     'released',    'quality_manager'),
    ('quarantined', 'released',    'quality_manager'),
    ('on_hold',     'returned',    'quality_manager'),
    ('on_hold',     'disposed',    'quality_manager'),
    ('quarantined', 'returned',    'quality_manager'),
    ('quarantined', 'disposed',    'quality_manager'),
    ('released',    'on_hold',     'investigator'),
    ('released',    'on_hold',     'quality_manager');
