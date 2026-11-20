# 5. Implementation

## 5.1 Technology stack and project structure

| Layer | Technology | Location |
|---|---|---|
| Database | PostgreSQL 18; SQL and PL/pgSQL scripts applied in order | `db/00_extensions.sql` … `db/06_grants.sql` |
| Backend | Python 3.12, FastAPI, psycopg 3 (connection pool), Pydantic 2, PyJWT, pwdlib (Argon2) | `backend/app/` |
| Frontend | React 19, TypeScript, Vite, Mantine 8, TanStack Query 5, React Router 7, Recharts | `frontend/src/` |
| Tooling | uv, ruff, pytest; Playwright with Microsoft Edge; Docker | `backend/tests/`, `tools/e2e/` |
| Launchers | `run.bat` (set up and start), `stop.bat` (stop) | repository root |

![Project size](figures/project_size.png){width=100%}

*Figure 5.1: Database and API objects, and lines of code by part of the project.*

`backend/scripts/reset_db.py` builds the whole database from the SQL scripts:

1. It creates two roles: `pharmatrace_owner`, which owns the schema, and `pharmatrace_app`, which the API uses.
2. It drops and recreates the database.
3. It creates the `btree_gist` extension.
4. It applies `db/*.sql` in order.
5. It loads deterministic demonstration data. The data's timestamps are relative to the time the script is run.

## 5.2 Database implementation

### Tables and constraints (`01_tables.sql`)

There are 20 tables. Every primary key is an identity column, apart from the composite keys of the junction tables and of the weak entity. Foreign keys use `ON DELETE RESTRICT`, except where a child row has no meaning without its parent (phone numbers, shipment lines, checkpoints, incident links), which use `ON DELETE CASCADE`.

| Constraint (name) | Rule |
|---|---|
| `product_temp_range`, `product_humidity_pair`, `product_humidity_range` | min < max; humidity limits given both-or-neither, within 0–100 |
| `batch_dates`, quantity CHECK, `batch_status` CHECK | Expiry after manufacture; quantity > 0; status from a fixed list |
| `shipment_route` | Origin ≠ destination |
| `shipment_status_times` | Planned ⇒ no dispatch or arrival time; in transit ⇒ dispatched, not arrived; delivered ⇒ both |
| `shipment_arrival_after_dispatch` | actual_arrival ≥ dispatch_time |
| `movement_dispatch_needs_shipment` | A dispatch movement must name its shipment |
| `assignment_one_target`, `incident_one_target` | Exactly one of shipment or facility (`num_nonnulls(...) = 1`) |
| `assignment_no_overlap` | `EXCLUDE USING gist (sensor_id WITH =, tstzrange(assigned_at, unassigned_at) WITH &&)` |
| `reading_unique_per_sensor`, `reading_has_value` | No duplicate (sensor, time); at least one measured value |
| `incident_manual_reporter`, `incident_period` | Manual incidents need a reporter; end ≥ start |
| `incident_active_shipment_uq`, `incident_active_facility_uq` | Partial unique indexes: one active incident per target and type |
| `assessed_needs_note` | An assessed batch needs a note |
| `investigation_completion`, `investigation_findings` | Completed ⇔ completed_at set; completed needs findings |
| `action_completion` | Completed ⇔ completed_at set |
| `staff_email_uq` | Unique `lower(email)` |
| pincode, phone, registration formats | Regular-expression CHECKs |

### Indexes (`02_indexes.sql`)

There are 24 explicit indexes in this file, plus the 3 unique indexes created in `01_tables.sql`:

- B-tree indexes on every foreign key used in joins;
- partial indexes serving the dashboard (shipments in transit, active incidents, open corrective actions);
- a **BRIN** index on `sensor_reading(recorded_at)`, which is small and suits the append-only time series.

Per-sensor lookups use the `UNIQUE (sensor_id, recorded_at)` B-tree.

### Functions and transactions (`03_functions.sql`)

| Function | Purpose |
|---|---|
| `current_staff_id()`, `current_staff_role()` | Read the acting user from the transaction setting `app.current_staff_id` |
| `batch_stock_at(batch, facility, time)` | Stock derived from the movement history |
| `batches_at_target(shipment, facility, time)` | Batches present at a monitored place and time |
| **`dispatch_shipment(id, time)`** | Atomic dispatch (described below) |
| **`receive_shipment(id, time)`** | Atomic receipt: received movements, arrival checkpoint, sensor assignments ended, status delivered |
| `shipment_timeline(id)` | Checkpoints, movements and incidents merged in time order (`UNION ALL`) |
| `related_shipments(incident)` | Other shipments on the same vehicle or at the same facility during the incident window |
| `severity_rank`, `severity_for_deviation`, `movement_sign` | Helper functions |

`dispatch_shipment` runs as one transaction:

1. It locks the shipment row.
2. It checks the status (planned), that at least one batch is on board, that an active sensor is attached, and that the vehicle's refrigeration is not faulty.
3. It locks the batch rows **in batch_id order**.
4. For each line, it checks the batch status, expiry and stock at the origin.
5. It inserts the dispatch movements and a departure checkpoint, and sets the shipment in transit.

Any failure raises an exception that undoes every step. The fixed locking order means two concurrent dispatches of the same stock cannot deadlock. The second waits for the first, then fails on stock (TC14). The full listing is in Appendix D.

### Triggers (`04_triggers.sql`)

| Trigger | Table and timing | Purpose |
|---|---|---|
| `shipment_batch_check` | shipment_batch, before insert/update/delete | Lines change only while the shipment is planned; product temperature ranges must overlap |
| `sensor_assignment_check` | sensor_assignment, before insert/update | Only active sensors; not on delivered or cancelled shipments |
| `reading_classify` | sensor_reading, before insert | Marks implausible values (outside −80…80 °C or 0…100 % RH) or future timestamps as invalid, and readings from faulty sensors as suspicious; the raw value is always kept |
| `reading_protect` | sensor_reading, before update/delete | Original values can never change; only `quality_status` may |
| `reading_evaluate` | sensor_reading, after insert | **Excursion detection** (described below) |
| `batch_status_check` | batch, before update of batch_status | The transition must be listed in BATCH_STATUS_TRANSITION for the acting user's role |
| `incident_lifecycle` | incident, before update of incident_status | Allowed state moves; the rules for resolving and closing |
| `investigation_check`, `investigation_opened` | investigation | Assignee must be an active investigator or QM; the first investigation moves the incident to investigating |
| `action_check` | corrective_action | No new actions on closed incidents; active assignee |
| `audit_*` (8 triggers) | batch, shipment, incident, incident_batch, investigation, corrective_action, staff, sensor_reading | The generic `trg_audit()`, a SECURITY DEFINER function, writes old and new rows (without password hashes), the acting user and the reason |

**Excursion detection.** For every valid reading, `reading_evaluate` does the following:

1. Finds the sensor's assignment at the reading's time.
2. Finds the batches present there: the shipment's lines, or the facility's stock at that time.
3. Compares the reading with **each batch's own product limits**.
4. **On a breach,** `record_excursion()`:
   - takes an advisory lock per target, so two readings cannot both open an incident;
   - finds or creates the active incident;
   - links the reading and the breached batches;
   - raises the severity, never lowering it.

   The illustrative severity thresholds, by distance beyond the limit, are: up to 1 °C low, up to 3 °C medium, up to 5 °C high, above 5 °C critical.
5. **When readings return within limits,** `end_excursion()` records the end time.

### Views (`05_views.sql`)

There are 14 views, so every derived number comes from SQL:

| Group | Views |
|---|---|
| Stock and status | `v_batch_stock`, `v_batch_in_transit`, `v_batch_summary` (on hand, in transit, days to expiry, open incidents) |
| Shipments | `v_shipment_limits` (tightest range on board), `v_shipment_summary` (with an overdue flag) |
| Incidents | `v_incident_exposure` (exposure from the linked readings, peak, number of breaching readings), `v_incident_summary` |
| Dashboard | `v_dashboard` (seven counters) |
| Reports | `v_report_incidents_by_type_severity`, `v_report_batch_incidents`, `v_report_vehicle_repeat_incidents` (`HAVING COUNT > 1`), `v_report_pending_actions`, `v_report_expiring_batches`, `v_report_sensor_quality` (gaps found with `LAG()`) |

### Privileges (`06_grants.sql`)

The application role `pharmatrace_app`:

- has SELECT on all tables;
- has INSERT and UPDATE on business tables;
- can DELETE only shipment lines and facility phone numbers;
- on readings, can INSERT and can UPDATE only `quality_status`;
- has **no** write access to `audit_log` or `batch_status_transition`.

## 5.3 Backend implementation

| Module | Responsibility |
|---|---|
| `config.py` | Settings from `.env` (pydantic-settings) |
| `db.py` | Connection pool; one transaction per request; `set_context()` sets `app.current_staff_id` and `app.change_reason` |
| `auth.py` | Argon2 password check; JWT (HS256) issue and verify; `require(*roles)`; the `Db` dependency |
| `errors.py` | Maps PostgreSQL errors to HTTP (403, 404, 409, 422) with readable messages |
| `routers/catalog.py` | Products, batches (including trace and status), facilities, vehicles, sensors, assignments, staff |
| `routers/shipments.py` | Create, add or remove lines, dispatch, receive, cancel, checkpoints, timeline |
| `routers/monitoring.py` | Idempotent reading ingestion; filtered reading queries |
| `routers/incidents.py` | Incidents, investigations, batch assessments, corrective actions, status changes |
| `routers/reports.py` | Dashboard, reports (whitelisted view names), audit log, simulator |
| `simulator.py` | Normal readings for active sensors; a scripted refrigeration failure (14 readings, 2.5 s apart) |

All 50 endpoints are listed in Appendix B.

## 5.4 Frontend implementation

The frontend has 12 pages behind a role-aware navigation bar:

| Page | Function |
|---|---|
| Login | Email and password, with validation; demonstration-account helper |
| Dashboard | Seven live counters, shipments in transit, recent incidents; administrator simulator panel |
| Shipments / Shipment detail | List, create (with lines and sensor), dispatch, receive, cancel, checkpoints, timeline, incidents |
| Batches / Batch trace | Search and register; stock per facility, chain of custody, shipments, incidents, decision history, decision form |
| Products | List and register with limits |
| Monitoring | Readings by sensor or shipment, time window, quality filter, out-of-limits filter, chart with limit lines |
| Incidents / Incident detail | List and manual report; chart, exposure, affected batches, assessments, decisions, investigation, actions, related shipments, audit history, status changes |
| Reports | Six tabbed SQL reports |
| Facilities & admin | Facilities (with phones), vehicles, sensors (with installation), staff (admin only), audit log (QM and admin only) |

Display codes such as SH001 and INC0001 are formatted from integer keys and never stored.

## 5.5 Demonstration data

`scripts/seed.py` loads the following:

| Data | Contents |
|---|---|
| Staff | Five staff members across all four roles |
| Products | Four products: three at 2–8 °C, and Tablet D at 15–25 °C, 30–65 % RH |
| Facilities | Six facilities across Karnataka |
| Vehicles | Four vehicles, one with degraded refrigeration |
| Batches | Twelve batches, one already expired and one expiring within 20 days |
| Sensors | Ten sensors: one installed at a distribution centre, one inactive, one faulty |
| Shipments | Six shipments covering every status |
| Readings | About 6,000, including a 40-minute gap and one corrupt value |

The data also includes two incidents:

- **INC0001** is closed. Its investigation is complete, batch B004 was released and B003 disposed, and two corrective actions are done.
- **INC0002** is under investigation, with batch B005 on hold and one overdue corrective action.

Every step of the demonstration data was created through the same functions and triggers the application uses.
