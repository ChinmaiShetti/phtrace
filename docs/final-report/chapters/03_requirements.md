# 3. Requirement Specification

## 3.1 Users and roles

| Role | Responsibilities |
|---|---|
| Operator | Registers products, batches, facilities, vehicles and sensors; creates, dispatches and receives shipments; records checkpoints; reports manual incidents; completes corrective actions assigned to them |
| Investigator | Records investigation findings; assesses affected batches; places batches on hold; adds corrective actions |
| Quality manager | Assigns investigators; quarantines, releases, returns or disposes of batches; resolves and closes incidents; reads the audit log |
| Administrator | Manages staff accounts and roles; runs the reading simulator; reads the audit log |

## 3.2 Functional requirements

| ID | Requirement | Implemented by |
|---|---|---|
| FR-01 | Authenticate staff by email and password, and restrict every action by role | `/api/auth/login`, JWT, `require()` checks, database triggers |
| FR-02 | Register products with configured minimum and maximum storage temperature (and optional humidity) limits | `product` table and form |
| FR-03 | Register batches with a unique batch number, manufacturing date, expiry date and initial quantity | `batch` table; intake movement recorded in the same transaction |
| FR-04 | Maintain facilities (warehouse, distribution centre, hospital, clinic, pharmacy) and refrigerated vehicles | `facility`, `facility_phone`, `vehicle` |
| FR-05 | Create a shipment with vehicle, origin, destination and expected arrival, and attach batches with quantities | `shipment`, `shipment_batch` |
| FR-06 | Dispatch a shipment in one transaction: verify stock and batch status, record dispatch movements and a departure checkpoint, set status in transit | `dispatch_shipment()` |
| FR-07 | Receive a shipment in one transaction: record received movements and an arrival checkpoint, set status delivered | `receive_shipment()` |
| FR-08 | Record every batch movement as history, and derive current stock per facility from it | `batch_movement`, `v_batch_stock` |
| FR-09 | Assign sensors to a shipment or facility for a period, and prevent overlapping assignments of one sensor | `sensor_assignment` with an EXCLUDE constraint |
| FR-10 | Store each reading with timestamp and quality status, and never overwrite original values | `sensor_reading`, `trg_reading_protect` |
| FR-11 | Compare each valid reading with the limits of the products present, and raise or update an incident on a breach | `trg_reading_evaluate`, `record_excursion()` |
| FR-12 | Link an incident to its shipment or facility, the relevant readings and the potentially affected batches | `incident_reading`, `incident_batch` |
| FR-13 | Let a quality manager assign an investigator, and the investigator record findings | `investigation` |
| FR-14 | Record batch decisions (hold, quarantine, release, return, dispose), with user, time and reason | `batch_status_transition`, `audit_log` |
| FR-15 | Record corrective actions with a responsible person, due date and status | `corrective_action` |
| FR-16 | Close an incident only when every investigation and corrective action is complete and every affected batch is assessed | `trg_incident_lifecycle` |
| FR-17 | Trace a batch: product, shipments, facilities, readings, incidents and current status | `/api/batches/{id}/trace`, Batch Trace page |
| FR-18 | Show a dashboard: active shipments, open incidents, batches under investigation, overdue actions, recent excursions, overdue arrivals | `v_dashboard` |
| FR-19 | Generate reports: incidents by type and severity, batches in incidents, repeated incidents per vehicle, pending actions, expiring batches, sensor data quality | Six `v_report_*` views |

## 3.3 Non-functional requirements

| ID | Category | Requirement | How it is met |
|---|---|---|---|
| NFR-01 | Integrity | All relationships enforced by keys and constraints | 20 primary keys, 27 foreign keys, 50 CHECK constraints, 1 EXCLUDE constraint, UNIQUE keys |
| NFR-02 | Consistency | Multi-step operations are atomic | PL/pgSQL functions; one transaction per API request |
| NFR-03 | Concurrency | Concurrent dispatches never make stock negative | Row locks taken in batch_id order (TC14) |
| NFR-04 | Security | Hashed passwords; role-based access; parameterised SQL; least-privilege database role | Argon2, JWT, `require()`, database triggers, `pharmatrace_app` grants |
| NFR-05 | Auditability | Status changes logged with user, time, old and new values and reason | Generic `trg_audit` trigger (SECURITY DEFINER) |
| NFR-06 | Performance | Dashboard and incident pages load within 2 s on the demonstration data set | Views with indexes; measured interactively |
| NFR-07 | Usability | Web forms with field-level validation messages; works in a modern browser | Mantine forms (Chapter 6) |
| NFR-08 | Maintainability | Schema kept as version-controlled SQL scripts; database rebuildable from them | `db/*.sql`, `reset_db.py` |

## 3.4 Business rules enforced in the database

1. A batch's expiry date must be after its manufacturing date, and quantities must be positive.
2. A shipment's origin and destination must differ. The shipment's status must agree with its dispatch and arrival times.
3. An expired, quarantined, on-hold or disposed batch cannot be dispatched. Stock at the origin must cover the requested quantity.
4. All products on one shipment must have overlapping temperature ranges.
5. A sensor assignment targets exactly one shipment or one facility. A sensor's assignment periods cannot overlap.
6. Only one active incident is allowed per shipment (or facility) per incident type. Repeated breaches are appended to it.
7. A reading with the same sensor and timestamp as an existing reading is a duplicate and is rejected. A reading's original values can never be changed or deleted.
8. Batch status changes must follow the transitions allowed for the acting staff member's role.
9. An incident moves open → investigating → resolved → closed. It may be reopened from resolved to investigating. Closing requires a quality manager, no pending corrective actions, and every affected batch assessed.

## 3.5 Hardware and software

| Type | Used / required |
|---|---|
| Processor | Any x86-64 (developed on AMD Ryzen 5 7535HS) |
| Memory | 8 GB recommended |
| Operating system | Windows 10/11 (developed on Windows 11); also runs on Linux and macOS |
| Database | PostgreSQL 18 (18.3) with the btree_gist extension |
| Backend | Python 3.12, FastAPI, psycopg 3, Pydantic 2, PyJWT, pwdlib (Argon2); managed with uv |
| Frontend | Node.js 22, React 19, TypeScript, Vite, Mantine 8, TanStack Query 5, React Router 7, Recharts |
| Testing | pytest, ruff; Playwright (driving Microsoft Edge) for browser checks |
| Benchmark | Docker (gcc:14 image, CMake), C++17, tlx, ALEX; Python with numpy and matplotlib |
| Browser | Current Chrome, Edge or Firefox |

## 3.6 Assumptions and constraints

- Sensor readings are simulated: every 5 minutes for normal operation, and every 2.5 seconds during the live failure demonstration.
- Temperature limits and severity thresholds are illustrative, configured values.
- The software records decisions; it does not decide whether a medicine is usable.
- All timestamps are stored as `timestamptz` (UTC) and shown in the browser's local time.
