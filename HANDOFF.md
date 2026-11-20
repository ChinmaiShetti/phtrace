# PharmaTrace: handoff for the next agent

Last updated 2026-11-08. Read this file first, then [CLAUDE.md](CLAUDE.md) (short rules) and [README.md](README.md) (how to run). [idea.md](idea.md) is the original concept spec written by the user.

---

## 0. TL;DR

- **What:** a DBMS lab mini-project. PharmaTrace is a PostgreSQL + FastAPI + React app for pharmaceutical cold-chain traceability, plus a separate C++ benchmark comparing a B+ tree with the learned index ALEX.
- **State:** the application, the database and the baseline benchmark are **complete and tested**:
  - 68 automated tests pass, covering all 34 lab-manual test cases;
  - every screen has been checked in a browser as each of the four roles;
  - the full demo scenario has been driven through the UI.
- **Lab-manual submissions 1–7 are written** (two Claude Docs documents, §3).
- **Research extension (ALEX-HB, Phase 4)** was implemented and measured on 2026-11-08 (§10).
- **Remaining work** (§11):
  - the user still has to configure it for their own PostgreSQL;
  - `run.bat` is untested;
  - the table-layout fix needs a visual check;
  - submission 8 write-up, draft report and final report;
  - an optional research extension.
- **User rules:**
  - Work fast and don't keep asking. Batch any approvals into one question.
  - **The user makes git commits themselves. Never commit or push.**
  - Nothing has been committed yet.

---

## 1. The user and the course

| Item | Value |
|---|---|
| Student | Chinmai Kiran Shetti, USN 1RV24CS068 (section not given) |
| Course | Database Management Systems Lab, CD2521A, Dept. of CSE, RV College of Engineering, Bengaluru |
| Team | Solo |
| Deadline | The user originally wanted everything within 5 days of 2026-10-27, i.e. about 2026-11-01. That date has passed, and work is still continuing. Exact due dates for the remaining submissions are unknown, so ask if they matter. |
| Working style | Minimal questions; batch approvals into one ask. A project allowlist exists in `.claude/settings.json` (deny: `git push*`, `rm -rf /*`). |

### Lab manual index (from the photo the user shared)

| # | Submission | Marks | Status |
|---|---|---|---|
| 1 | Synopsis | 5 | Done (lab-manual doc) |
| 2 | Requirement Specification | 5 | Done |
| 3 | ER Diagram (user required **Chen notation**) | 10 | Done |
| 4 | Test | 20 | Done. The "Actual result" and "Status" columns in the doc are still **blank**; fill them from `docs/test-report.md` (all pass). |
| 5 | DFD Level 0, 1, 2 | 10 | Done (Yourdon–DeMarco notation) |
| 6 | Normalized tables up to 3NF | 10 | Done |
| 7 | Midterm Report | 20 | Done (mid-term doc). One screenshot shows an old, clipped table layout. |
| 8 | Design of Forms, Security & Validation | 10 | **Implemented in the app, no write-up yet** |
| 9 | Demo & Draft Report | 30 | Demo works; **draft report not written** |
| | Total 120, reduced to 30 | | |
| 10 | Innovative Experiment | 10 | Baseline benchmark done and written up (`docs/benchmark-report.md`) |
| 11 | CIE Project Demo & Final Report | 10 | **Not started** |

---

## 2. Two deliverables (do not conflate them)

1. **The application.** It lives in `db/`, `backend/` and `frontend/`. It is the graded DBMS project.
2. **The research benchmark (the Innovative Experiment).** It lives in `benchmark/`. It runs on synthetic traces, standalone, in Docker. **It is not integrated with PostgreSQL or the app**, so never claim it is.
   - The app motivates the workload: (sensor, time) keys, plus a burst of inserts and queries during an incident.
   - Suggested phrasing for faculty: "PharmaTrace is our application case; its incident-response behaviour defines a realistic workload which we use to evaluate a learned index against a B+ tree."

**Claims constraints** (from idea.md; the user cares about these):
- The software **records** batch decisions made by authorised staff. It never decides whether a medicine is safe.
- An excursion links only the batches whose own product limits were breached.
- Temperature limits and severity thresholds are **illustrative**.
- Make no novelty claims for cold-chain monitoring or learned indexing.
- Report benchmark results as measured, including where ALEX loses.

---

## 3. Documents already produced (outside the repo)

Both are **Claude Docs** documents, private to the user unless they share them:

| Doc | URL | Contents |
|---|---|---|
| PharmaTrace – DBMS Mini Project Lab Manual (Submissions 1–6) | https://claude.ai/artifact/XXxJuLG3UYvTGNFpniihi2 | §1 Synopsis, §2 Requirements (19 FRs, 8 NFRs, business rules, HW/SW), §3 Chen ER diagram + notation, entity and relationship tables, §4 test strategy + TC01–TC34 table, §5 DFD L0/L1/L2 (processes 5.0 and 6.0) + process and store tables, §6 UNF→1NF→2NF→3NF with the final 18-table schema, candidate keys and FDs |
| PharmaTrace: Mid-Term Report | https://claude.ai/artifact/Ui3c4hAmrnCLnqL6J28LmR | Abstract, introduction, objectives with status, literature survey (14 references, sources verified), design (ER and DFD images), implementation progress (object counts), 3 screenshots, testing status, benchmark preliminary results, work remaining, conclusion |

To edit them you need the Claude Docs connector (read before editing; people may have edited them). If the connector is unavailable, tell the user.

**Figures in the repo:**
- `docs/lab-manual/diagrams/*.png|pdf`: the Chen ER diagram, DFD L0, L1, L2 (5.0), L2 (6.0).
- They were generated with matplotlib scripts (a custom Chen layout and DFD renderer) kept in a temp scratchpad that **no longer exists**.
- If a diagram must change, either redraw it (e.g. in draw.io) or rewrite a generator. The model they encode is the schema in §6 plus the relationship list in the lab-manual doc §3.4.

**Other docs in the repo:**
- `docs/test-report.md`: generated by `backend/scripts/test_report.py`. It maps TC01–TC34 to pytest names; all pass.
- `docs/benchmark-report.md`: the Innovative Experiment write-up.

**Original planning file:** `C:\Users\chinm\.claude\plans\ideate-properly-and-develop-jiggly-lerdorf.md`. This is a 4-week plan, later compressed. Where it differs from the code, the code wins (see §6.4).

---

## 4. Machine and environment (Windows 11): gotchas that cost time

- **Shells:** the Bash tool is Git Bash (POSIX). PowerShell is not available as a tool in this session.
- **Python:** use `py` (3.12.5). `python3` is a Microsoft Store alias.
- **uv 0.11.8:** the user's shell sets `UV_PROJECT_ENVIRONMENT=D:\tools\uv-tools\conv-dev` (a shared venv). **Always set `UV_PROJECT_ENVIRONMENT=.venv`** when running uv in `backend/`, or packages go into the wrong environment. The project venv is `backend/.venv`.
- **Node:** 22.16 with npm 10.9. Frontend dependency versions: React 19, Vite 8, TypeScript 7, Mantine 8.3, TanStack Query 5, React Router 7, Recharts 3.
- **Local PostgreSQL 18.3** is installed as the Windows service `postgresql-x64-18` on port 5432.
  - `psql` is at `C:\Program Files\PostgreSQL\18\bin\psql.exe` and is **not on PATH**.
  - The `postgres` password is **unknown to us**: the user must put it in `.env`.
  - **The app has never been run against this local server.** All testing used the Docker dev DB below.
- **Docker Desktop 29.2** must be started manually: `"/c/Program Files/Docker/Docker/Docker Desktop.exe" & disown`. Then poll `docker info`. It stops when sessions restart.
  - **Dev database container:** `pharmatrace-pg-dev` (image `postgres:18`), host port **5433**, password **devpass**. Start it with `docker start pharmatrace-pg-dev`.
  - Point the tools at it with `PG_PORT=5433 PG_ADMIN_PASSWORD=devpass` as environment variables. These override `.env`.
  - To run psql against it: `docker exec -i pharmatrace-pg-dev psql -U postgres -d pharmatrace`.
  - Volume mounts from Git Bash need `MSYS_NO_PATHCONV=1` and Windows paths, e.g. `-v "D:/DBMSEL/benchmark/traces:/traces"`.
  - A failed build with "parent snapshot ... does not exist" is a build-cache error; rebuild with `--no-cache`.
- **C++:** the only host compiler is MinGW g++ 6.3, too old for ALEX and tlx. The benchmark builds inside Docker `gcc:14`.
- **Browser automation:** Microsoft Edge is installed at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`. `tools/e2e` uses `playwright-core` with `channel: "msedge"`, so no browser download is needed.
- **Batch files** need CRLF line endings. After writing one, run `sed -i 's/\r$//; s/$/\r/' file.bat`.
- **Seed data is relative to "now".** Re-run `reset_db` before any demo; after a few hours the in-transit shipments show as overdue (correct behaviour).

---

## 5. How to run

**One-click:** `run.bat` (repo root). It is **written but never executed end to end**; my test of it was interrupted. What it does:
1. If `.env` is missing, it copies `.env.example`, opens Notepad and stops. It also stops if `PG_ADMIN_PASSWORD` is still `CHANGE_ME`.
2. It checks that `uv` and `npm` exist.
3. On the first run it runs `uv sync` (backend) and `npm install` (frontend).
4. On the first run, or with `run.bat reset`, it builds and seeds the DB. The marker file is `backend\.db_ready` (gitignored).
5. It starts two windows (the API on :8000 and Vite on :5173), waits 6 s and opens http://localhost:5173.
6. `run.bat setup` installs dependencies and builds the DB without starting anything.

**Manual:**
```
copy .env.example .env          (set PG_ADMIN_PASSWORD)
cd backend
set UV_PROJECT_ENVIRONMENT=.venv
uv sync
uv run python -m scripts.reset_db            (drop + rebuild + seed; --no-seed for empty; --db NAME for another DB)
uv run uvicorn app.main:app --port 8000      (Swagger at /docs)
cd ..\frontend
npm install
npm run dev                                  (http://localhost:5173; Vite proxies /api to 127.0.0.1:8000)
```

**`.env` keys** (see `.env.example`):

| Key | Default |
|---|---|
| `PG_HOST` | localhost |
| `PG_PORT` | 5432 |
| `PG_ADMIN_USER` | postgres |
| `PG_ADMIN_PASSWORD` | must be set |
| `DB_NAME` | pharmatrace |
| `PG_OWNER_PASSWORD` | |
| `PG_APP_PASSWORD` | |
| `JWT_SECRET` | defaults in `app/config.py` are dev-only |
| `JWT_EXPIRE_MINUTES` | 480 |
| `CORS_ORIGINS` | http://localhost:5173 |

**Demo logins** (seeded; password = local part of the email + "123"):

| Role | Name | Email | Password |
|---|---|---|---|
| Administrator | Asha Rao | admin@pharmatrace.local | admin123 |
| Operator | Ravi Kumar | operator@pharmatrace.local | operator123 |
| Investigator | Meera Nair | investigator@pharmatrace.local | investigator123 |
| Investigator | Vikram Shah | investigator2@pharmatrace.local | investigator2123 |
| Quality manager | Priya Menon | qm@pharmatrace.local | qm123 |

Staff ids follow the seed order: 1 admin, 2 operator, 3 investigator, 4 investigator2, 5 qm. `db/queries/demo.sql` relies on staff 2 being the operator.

---

## 6. Architecture

### 6.1 Principle: a thin API over a smart database

Integrity and workflow are enforced **in PostgreSQL**, because that is what the course grades. To change a rule, edit the SQL, not Python.

- FastAPI does authentication, role checks and input-shape validation.
- The database re-enforces the rules: constraints, triggers, row locks and privileges.
- Each API request is **one transaction** running as the least-privileged role `pharmatrace_app` (`backend/app/db.py`). Its first statement is:
  `SELECT set_config('app.current_staff_id', <id>, true), set_config('app.change_reason', <reason>, true)`
- SQL reads the acting user back with `current_staff_id()`, using `NULLIF(... ,'')` because pooled connections return `''` after a local setting ends. `current_staff_role()` returns that staff member's role.
- `audit_log.reason` comes from `app.change_reason`. The batch-status and incident-status endpoints set it from the user's "reason" field.

### 6.2 Database files (`db/`, applied in name order by `reset_db.py`)

| File | Contents |
|---|---|
| `00_extensions.sql` | `btree_gist` (needed by the EXCLUDE constraint) |
| `01_tables.sql` | 20 tables plus seed rows for `batch_status_transition` |
| `02_indexes.sql` | FK indexes, partial dashboard indexes, BRIN on `sensor_reading(recorded_at)` |
| `03_functions.sql` | Helpers, `dispatch_shipment`, `receive_shipment`, `shipment_timeline`, `related_shipments` |
| `04_triggers.sql` | Validation, excursion detection, workflow rules, audit |
| `05_views.sql` | Derived data, dashboard and report views |
| `06_grants.sql` | Privileges for `pharmatrace_app` |
| `queries/demo.sql` | Curated queries for the demo's database scene |

`reset_db.py` connects as the superuser from `.env`. It creates or alters the roles `pharmatrace_owner` and `pharmatrace_app` (passwords from `.env`), drops the DB with FORCE and recreates it owned by `pharmatrace_owner`, creates `btree_gist` as superuser, and revokes PUBLIC access. It then applies each SQL file as `pharmatrace_owner` (one multi-statement `execute` per file) and seeds.

**Counts:**

| Object | Count | Notes |
|---|---|---|
| Tables | 20 | |
| Foreign keys | 27 | |
| CHECK / EXCLUDE constraints | about 50 | |
| Indexes | 27 | 24 in `02_indexes.sql` plus 3 in `01` |
| Functions | 24 | |
| Triggers | 18 | |
| Views | 14 | |

### 6.3 Tables (names match lab-manual §6.5; keep them in sync with the ER and normalisation docs)

| Table | Notes |
|---|---|
| `staff` | role ∈ operator/investigator/quality_manager/admin; unique `lower(email)`; argon2 `password_hash`; `account_status` |
| `product` | `product_name` unique; `min_temp < max_temp`; humidity limits both-or-neither, 0–100 |
| `batch` | `batch_number` unique; expiry > manufacture; qty > 0; `batch_status` ∈ available/on_hold/quarantined/released/returned/disposed ("expired" is derived, never stored) |
| `facility` | type ∈ warehouse/distribution_centre/hospital/clinic/pharmacy; address split into street/city/pincode (6 digits, not starting with 0) |
| `facility_phone` | (facility_id, phone_number): the multivalued attribute |
| `vehicle` | `registration_number` unique; `refrigeration_status` ∈ operational/degraded/faulty |
| `shipment` | origin ≠ destination; status ∈ planned/in_transit/delivered/cancelled, with a CHECK tying status to dispatch/arrival timestamps; arrival ≥ dispatch |
| `shipment_batch` | PK (shipment_id, batch_id); qty > 0. Trigger: lines change only while the shipment is planned, and every product's temperature range must overlap |
| `shipment_checkpoint` | **Weak entity**: PK (shipment_id, checkpoint_no); event ∈ departure/transit_scan/inspection/delay/arrival; free-text `location_description` (no facility FK) |
| `batch_movement` | **Movement history** (chain of custody); type ∈ received/dispatched/returned/disposed; dispatched requires a shipment. Stock is always derived from this table |
| `sensor` | `serial_number` unique; type ∈ temperature/humidity/temp_humidity; status active/inactive/faulty; `expected_interval_s` (default 300) |
| `sensor_assignment` | Exactly one of shipment/facility; `EXCLUDE USING gist` prevents overlapping periods for the same sensor; trigger: only active sensors, not to delivered or cancelled shipments |
| `sensor_reading` | BIGINT id; `UNIQUE(sensor_id, recorded_at)`; `ingested_at`; at least one value; `quality_status` valid/suspicious/invalid; raw values never range-checked, so originals are always kept |
| `incident` | type ∈ temperature_excursion/humidity_excursion/sensor_failure/other; severity low/medium/high/critical; source automatic/manual (manual requires `reported_by`); exactly one of shipment/facility; status open → investigating → resolved → closed (resolved → investigating allowed); partial unique indexes allow one active incident per (target, type). **No `sensor_id` column**: the sensor is derived from linked readings |
| `incident_reading` | PK (incident_id, reading_id), `relevance_note` ("back within limits" marks the recovery reading) |
| `incident_batch` | PK (incident_id, batch_id); assessment pending_review/under_assessment/assessed; assessed requires a note |
| `investigation` | `assigned_to` (must be an active investigator or QM); completed ⇔ `completed_at` set, and completed requires findings. **No `assigned_by`**: who assigned it is in `audit_log` |
| `corrective_action` | `assigned_to`; completed ⇔ `completed_at`; status pending/in_progress/completed/cancelled |
| `batch_status_transition` | PK (from, to, role): **this table is the workflow rule set** |
| `audit_log` | table, row_pk, action, old_data/new_data JSONB (password_hash stripped), `changed_by`, reason, `changed_at` |

**Batch transitions** (seeded):
- available → on_hold (investigator, QM)
- available / on_hold → quarantined (QM)
- on_hold / quarantined → released (QM)
- on_hold / quarantined → returned / disposed (QM)
- released → on_hold (investigator, QM)

Returned and disposed are terminal.

### 6.4 Deviations from idea.md and the original plan (intentional)

- **Derived values are never stored:** current quantity, location, exposure and expiry state are views (a good 3NF talking point).
- **Excursion limits are per batch:** each reading is evaluated against each batch's product limits, so a 2–25 °C syrup is not flagged at 10 °C.
- **Columns added beyond idea.md:**
  - Incident: `facility_id`, `detection_source`, `reported_by`.
  - Staff: `password_hash`.
  - Sensor: `expected_interval_s`.
  - Reading: `ingested_at`.
- `BatchLocation` was renamed `batch_movement`. `facility_phone` was added for the multivalued attribute.
- **Three FKs were dropped while drawing the Chen ER diagram:** checkpoint → facility, incident → sensor, investigation → assigned_by. The ER diagram, the 3NF schema, the code and the plan were all updated to match.
- **All timestamps** are TIMESTAMPTZ.

### 6.5 Key database logic

- **`dispatch_shipment(id, at)`:** a single atomic function.
  1. Locks the shipment row, then the batch rows **in batch_id order** (no deadlocks, no overselling; the second session waits, then fails on stock).
  2. Requires the status to be planned, at least one line, an active sensor assignment and a vehicle that isn't faulty.
  3. Checks each batch is available or released and not expired, and that stock at the origin (`batch_stock_at`) is enough.
  4. Inserts the dispatched movements and a departure checkpoint, and sets the shipment in transit.

  Any RAISE rolls back everything.
- **`receive_shipment(id, at)`:** inserts the received movements at the destination and an arrival checkpoint, ends the sensor assignments and sets the shipment delivered.
- **Readings:**
  - **Classification** (`trg_reading_classify`, before insert): a reading is **invalid** if its temperature is outside −80…80, its humidity outside 0…100, or its `recorded_at` is more than 5 minutes after `ingested_at`. It is suspicious if the sensor is faulty.
  - **Protection** (`trg_reading_protect`): blocks DELETE and any change except `quality_status`.
- **Detection** (`trg_reading_evaluate`, after insert, valid readings only):
  1. Finds the sensor's assignment at `recorded_at`. Readings from unassigned sensors, or recorded **before** the assignment started, are stored but not evaluated.
  2. `batches_at_target`: the shipment's lines, or the facility's stock at that time.
  3. Computes each batch's deviation from its product limits.
  4. On a breach, `record_excursion`: takes an advisory lock per target, finds or creates the active incident (start_time = the first breach, detected_at = `ingested_at`), links the reading and the breached batches, and escalates severity, never downgrading it. It also clears `end_time`.
  5. On an in-range reading, `end_excursion` sets `end_time` and links the reading as "back within limits".

  Illustrative severity thresholds, by deviation beyond the limit: ≤1 °C low, ≤3 medium, ≤5 high, >5 critical. Humidity counts 5 % RH as 1 °C.
- **Workflow triggers:**
  - `trg_batch_status_check`: the transition must exist for `current_staff_role()`, else `insufficient_privilege`.
  - `trg_incident_lifecycle`: enforces the allowed state moves. **Resolved** requires at least one investigation, with all completed. **Closed** requires a quality manager, no pending or in-progress actions, and all batches assessed.
  - `trg_investigation_check`, `trg_investigation_opened`: the first investigation moves the incident from open to investigating.
  - `trg_action_check`.
- **`trg_audit`:** `SECURITY DEFINER` with the search_path pinned, so the app role needs no INSERT on `audit_log`. It is attached to batch, shipment, incident, incident_batch, investigation, corrective_action, staff and sensor_reading (updates only).
- **Views:**
  - Stock and shipment: `v_batch_stock`, `v_batch_in_transit`, `v_batch_summary`, `v_shipment_limits` (tightest range on board), `v_shipment_summary` (with an `overdue` flag).
  - Incidents: `v_incident_exposure` (`exposure_minutes` **and** `exposure_seconds`, peak, breach count), `v_incident_summary`.
  - Dashboard and reports: `v_dashboard` (7 counters), `v_report_incidents_by_type_severity`, `v_report_batch_incidents`, `v_report_vehicle_repeat_incidents` (HAVING > 1), `v_report_pending_actions`, `v_report_expiring_batches` (≤ 60 days), `v_report_sensor_quality` (gaps found with LAG).
- **Grants:** the app role has SELECT on everything and INSERT/UPDATE on business tables. It has DELETE only on `shipment_batch` and `facility_phone`. On `sensor_reading` it has INSERT plus UPDATE of `quality_status` only. It has no write access to `audit_log` or `batch_status_transition`.

### 6.6 Backend (`backend/app/`)

| File | Contents |
|---|---|
| `config.py` | pydantic-settings, reads `ROOT/.env` |
| `db.py` | `psycopg_pool.ConnectionPool` with `dict_row`; `transaction(staff_id)` |
| `auth.py` | argon2 via pwdlib, JWT HS256 via PyJWT; `current_user`; `require(*roles)`; `Db` dependency = a transaction as the current user |
| `errors.py` | Maps psycopg errors to HTTP codes, with friendly text per constraint name |
| `simulator.py` | `backfill()` fills normal readings for active assignments up to now. `run_excursion()` sends 14 readings, one every 2.5 s, rising to the peak and recovering, on a background thread |
| `main.py` | `/api/auth/login` (OAuth2 form), `/api/auth/me`, `/api/health`, plus the routers below |

Error mapping in `errors.py`: insufficient_privilege → 403, no_data_found → 404, unique/exclusion/FK/restrict → 409, check/not-null → 422, RAISE → 409.

**Routers** (about 50 endpoints; see `/docs`):

| Router | Endpoints and notes |
|---|---|
| `catalog.py` | Products; batches (`GET ?q=` search, POST also writes the intake movement, `GET /batches/{id}/trace`, `POST /batches/{id}/status` with a reason); `/batch-transitions`; facilities with phones; vehicles (+ PATCH status); sensors (+ PATCH status); `/sensor-assignments` (+ `/end`); staff (admin only) |
| `shipments.py` | Create (lines + optional sensor in one transaction), detail (lines, limits, sensors, checkpoints, timeline, incidents), add/remove line, dispatch, receive, cancel, checkpoints |
| `monitoring.py` | `POST /readings` (idempotent; returns counts of received, inserted, duplicates and incidents opened); `GET /readings` with filters for sensor, shipment, from/to, quality and out_of_limits |
| `incidents.py` | List, manual report, detail (readings, ±1 h context readings, limits, batches, investigations, actions, related shipments, history), status change, assign investigator (QM), update investigation (assignee or QM), assess batch, add action, update action (assignee, investigator or QM) |
| `reports.py` | `/dashboard`, `/reports`, `/reports/{key}` (whitelisted view names), `/audit` (QM and admin), `/admin/simulate-excursion` (admin), `/admin/backfill` |

In the incident history, an automatically created incident is shown as "automatic detection" at `detected_at`, not as whoever's session stored the reading.

**Role matrix:**
- **Operator:** master data, dispatch, receive, checkpoints, manual incident reports.
- **Investigator:** findings, assessments, put a batch on hold, corrective actions.
- **QM:** assigns investigators, quarantine, release, return or dispose, closing incidents, audit log.
- **Admin:** staff management, simulator, audit log.
- Everyone can read everything except the audit log.

### 6.7 Frontend (`frontend/src/`)

| File | Contents |
|---|---|
| `api.ts` | fetch wrapper; token stored in localStorage (try/catch); `useApi` (React Query, optional polling); `useAction` (mutation + toast + invalidate all) |
| `auth.tsx` | Auth context; `can(...roles)` for showing and hiding UI (the server still enforces) |
| `ui.tsx` | `DataTable` (default `minWidth = 0`, the latest fix), `StatusBadge`, `PageHeader` (subtitle is a div, which fixed invalid HTML nesting), `Section`, `fmtTime`, `fmtDate`, `fmtDuration`, `code.shipment` (SH001) and `code.incident` (INC0001) |
| `TempChart.tsx` | Mantine LineChart with min/max reference lines; shows seconds on the time axis when the span is under 3 h |
| `pages/` | Login (demo-account helper), Dashboard (7 tiles, admin simulator panel, in-transit list, recent incidents), Shipments + ShipmentDetail, Batches + BatchTrace (stock, decisions, chain of custody, shipments, incidents; DecisionModal), Products, Monitoring, Incidents + IncidentDetail (main demo screen), Reports (tabs), Admin (facilities, vehicles, sensors, staff, audit log for QM and admin) |

Display codes such as SH001 and INC0001 are formatted from integer ids and never stored.

---

## 7. Seed data (`backend/scripts/seed.py`, deterministic, relative to now)

| Item | Seeded |
|---|---|
| Products | Vaccine A, Insulin B, Biologic C (2–8 °C); Tablet D (15–25 °C, 30–65 % RH) |
| Facilities | Central Warehouse (Bengaluru), Regional DC Mysuru, City General Hospital, Mysuru District Hospital, Tumakuru Community Clinic, Hubballi Care Pharmacy |
| Vehicles | KA01AB1234, KA05CD5678, KA09EF9012 (degraded), KA03GH3456 |
| Batches | B001–B012, all received at the warehouse 20 days ago. B011 has already expired; B012 expires in 20 days |
| Sensors | TL-1001 to TL-1010. TL-1001 is installed at the DC; TL-1006 measures temperature and humidity; TL-1009 is inactive; TL-1010 is faulty, unassigned, with suspicious readings |

**Shipments** (ids 1–6):

| Shipment | Route | Vehicle | Status and notes |
|---|---|---|---|
| SH001 | Warehouse → DC | | Delivered |
| SH002 | Warehouse → City General | KA09EF9012 | Delivered. Excursion **INC0001 is closed**: B004 released, B003 disposed, 2 actions done |
| SH003 | DC → Mysuru District | KA09EF9012 | Delivered. **INC0002 is investigating**: B005 on hold, 1 overdue action. Gives the vehicle repeat-incident report a row |
| SH004 | Warehouse → Tumakuru | KA05CD5678 | In transit; the demo simulator target |
| SH005 | Warehouse → Hubballi | KA03GH3456 | In transit; Tablet D |
| SH006 | | | Planned; ready to demo dispatch |

**Readings:** about 6,000. They include a 40-minute gap on TL-1001 and one corrupt 999 °C reading (stored as invalid).

---

## 8. Tests

- **Command:** `cd backend && set UV_PROJECT_ENVIRONMENT=.venv && uv run pytest` (add `PG_PORT=5433 PG_ADMIN_PASSWORD=devpass` for the Docker DB).
- **Database setup:** `conftest.py` rebuilds `pharmatrace_test` once per session and TRUNCATEs before each test. The `world` fixture provides 4 staff, 3 products (vaccine 2–8, syrup 2–25, tablet 15–25), 3 facilities, 1 van, batches B1–B4 plus BEXP (expired) and sensors S1–S3.
- **Files and counts:**

| File | Tests | Covers |
|---|---|---|
| `test_db_constraints.py` | 19 | TC01–TC10, TC16, TC28 |
| `test_db_transactions.py` | 10 | TC11–TC15, including a real two-connection concurrency test |
| `test_db_monitoring.py` | 13 | TC17–TC24 |
| `test_db_workflow.py` | 15 | TC26, TC29–TC33 |
| `test_api.py` | 11 | TC25, TC26, TC27, TC34, plus an end-to-end HTTP workflow |

- **Total:** 68, all passing at the last run. `uv run ruff check .` is clean, and `npm run build` succeeds (with a harmless bundle-size warning).
- **`uv run python -m scripts.test_report`** reruns pytest and regenerates `docs/test-report.md`.
- **Browser checks** (`tools/e2e/`, copied from scratch on 2026-11-08):
  - Setup: `npm install`, `mkdir shots`.
  - `node check.mjs shots`: logs in as each role, opens 13 pages, and fails on console errors or HTTP 5xx.
  - `node demo.mjs shots`: drives the full demo scenario through the UI and needs **freshly seeded** data (it expects the new incident to be INC0003 on SH004).
  - Both expect the API on :8000 and Vite on :5173.
  - Last results: all 52 page/role combinations clean; the demo flow is clean.

---

## 9. Demo script (scenes from idea.md §13)

1. **Normal operation:** log in as admin; the dashboard shows live counters.
2. **Failure:** pick SH004 in the dashboard's simulator panel, set the peak to 11.5 °C and press **Simulate failure**. A reading arrives every 2.5 s, for about 35 s.
3. **Incident:** INC0003 appears, raised by the database, with a readings chart, exposure, peak and **only the breached batches** (B002, B006, B007).
4. **Trace:** open a batch to see its chain of custody, stock per facility and incidents.
5. **Investigate:**
   - The QM assigns Meera Nair.
   - The investigator assesses each batch (a note is required), puts one on hold with a reason, adds a corrective action and records findings → "Complete investigation".
6. **Resolve:**
   - The QM marks it resolved.
   - Closing now is **refused by the database** ("corrective actions that are not finished").
   - The operator completes the action; the QM releases the batch and closes the incident.
   - The history shows each step with names and reasons.
7. **Database:** run `db/queries/demo.sql` in psql. It shows a 5-table join, a trace query, HAVING, a correlated subquery, a window-function gap query, constraint errors, a transaction rollback (dispatch fails on B010 after B009, leaving no movements), a role rule refused inside the DB, and EXPLAIN ANALYZE.
8. **Research:** show `benchmark/results/figures/*.png` and `docs/benchmark-report.md`.

---

## 10. Benchmark (Innovative Experiment)

**Code:**
- `workload/gen.py` (numpy, fixed seed 7): writes `traces/bulk.bin` (8.64 M keys = 1,000 sensors × 30 days × 5 min; key = `sensor_id << 40 | epoch_s`) and `traces/phases.bin` (six phases × 1 M operations; 13-byte packed records of kind, key and arg), plus `meta.json` with sha256 hashes. The traces are about 150 MB and gitignored, so regenerate them.
- **Phases:**
  - P1 stable: 80 % lookups, 10 % inserts, 10 % 1-h ranges.
  - P2 ingestion spike: 60 % inserts.
  - P3 localised incident: 10 hot sensors at 1-s cadence; 50 % inserts.
  - P4 investigation: Zipf(0.99) over incident keys; half 10-minute ranges.
  - P5 recovery: the same mix as P1.
  - P6 combined shift: new hot sensors; 50 % inserts, 50 % lookups of their newest keys.
- `src/bench.cpp`: adapters for tlx `btree_map` and `alex::Alex`. Each operation is timed with steady_clock. Per phase and operation type it reports p50, p95, p99, p99.9, max, mean, tail-time share, throughput, RSS above baseline, found count, checksum and ALEX stats. Each run is one index in one process.
- **Pinned commits:** ALEX `4370da6aa8b509fdc9b0d2c49faa0624b0078589`, tlx `2dd63ab839909f0b43cd02108a1869c4670b2c8e` (Dockerfile ARGs).
- **Build:** `Dockerfile` uses gcc:14 and cmake with `-O3 -march=native`. `run_all.sh` runs REPS=5, alternating the order, and writes `results/environment.txt` and `results/results.csv`.
- `analysis/analyze.py` writes `results/summary.md` and `results/figures/{throughput,latency,memory}.png`.

**Run** (about 10 minutes; keep the machine otherwise idle):
```
py -I benchmark/workload/gen.py
docker build -t pharmatrace-bench benchmark
MSYS_NO_PATHCONV=1 docker run --rm -e REPS=5 -v "D:/DBMSEL/benchmark/traces:/traces" -v "D:/DBMSEL/benchmark/results:/results" pharmatrace-bench
py -I benchmark/analysis/analyze.py
```

**Results** (AMD Ryzen 5 7535HS, Docker on WSL2, 5 repetitions):

| Phase | B+ tree throughput | ALEX throughput | ALEX / B+ tree |
|---|---|---|---|
| P1 stable | 1.89 M ops/s | 2.14 M ops/s | 1.13× |
| P2 ingestion spike | 2.48 M | 2.20 M | 0.89× |
| P3 localised incident | 2.64 M | 2.76 M | 1.04× |
| P4 investigation | 0.46 M | 1.53 M | 3.30× |
| P5 recovery | 1.80 M | 3.31 M | 1.84× |
| P6 combined shift | 7.12 M | 3.81 M | 0.54× |

- The replay check passed: hits and checksums were identical across indexes and repetitions.
- **Lookups:** ALEX median 230 ns against 461 ns (P1).
- **P4 range scans:** 791 ns against 3,607 ns.
- **ALEX inserts:** usually fast, but in P1, P3 and P6 the slowest 1 % took 80–83 % of all insert time. Worst pauses were 3–27 ms in P1/P2/P3/P6, against at most 0.65 ms for the B+ tree.
- **ALEX adaptation counters** (expand + scale): 0 → 206 → 619 → 1,008 across phases; retrains 3 → 576.
- **Memory:** ALEX 190 MB after load and 510 MB after P6, against 158 and 244 MB for the B+ tree.
- **Bulk load:** 105 against 21 ns per key.
- **Interpretation:** ALEX does its adaptation synchronously inside the insert that triggers it.
- **Phase 4 (ALEX-HB), done 2026-11-08:** a hot-range B+ tree buffer in front of ALEX with deferred migration. See `docs/experiment-phase4.md` (design and progress log) and `docs/benchmark-report.md` §6 (results). Code: `HotBufferAlex` in `bench.cpp`, index names `alexhb` and `alexhb-nomig`, flags `--hb-window/--hb-hot/--hb-migrate`. `run_all.sh` takes the `INDEXES` and `HB_ARGS` env vars.
  - **Results** (4 configs × 5 reps, `benchmark/results/`):
    - P3: ALEX-HB 4.35 M vs ALEX 2.66 M ops/s; worst insert pause 0.10 ms vs 37.5 ms.
    - P6: 8.49 M vs 3.57 M, beating the B+ tree (6.98 M).
    - P4: halved (0.89 M vs 1.79 M), because migration overlaps the investigation queries.
    - Migrating more slowly (M=1, `results_m1/`) made P4 worse (0.63 M).
  - **Baseline-only results** were preserved in `benchmark/results_baseline/`.

---

## 11. What is left (prioritised)

1. **User actions:**
   - Create `.env` with the local `postgres` password.
   - Run `run.bat` once (or the manual steps). Confirm the DB builds on the local server and that both windows start and the browser opens.
   - If `run.bat` misbehaves, check its quoting in the `start ... cmd /k` lines and the CRLF line endings.
2. **Verify the table-fit fix:** `DataTable` defaults to `minWidth = 0` in `ui.tsx`. It type-checks but **has not been looked at in a browser**. It should fix clipped right-hand columns on half-width cards (e.g. Batch Trace's "On hand", status columns).
   - Run `tools/e2e/check.mjs`.
   - Look at the screenshots of Batch Trace, Shipment detail, Incident detail and Dashboard.
3. **Retake screenshots** and replace Figure 6.3 (shipment detail) in the mid-term doc. Optionally add Batch Trace.
4. **Lab-manual doc, submission 4:** fill in the "Actual Result" and "Status" columns (all Pass) from `docs/test-report.md`.
5. **Submission 8 (Design of Forms, Security & Validation):** write a document covering:
   - each form (fields, client-side checks in Mantine `useForm`, server-side Pydantic, database constraints);
   - authentication (argon2, JWT);
   - the role matrix;
   - database-level enforcement (transition table, triggers, least-privilege grants, SECURITY DEFINER audit);
   - SQL-injection safety (parameterised queries, whitelisted report views);
   - audit trail.

   Material: `backend/app/routers/*.py` models, `frontend/src/pages/*` forms, `db/04_triggers.sql`, `db/06_grants.sql`, tests TC25–TC28 and TC34.
6. **Submission 9 draft report and submission 11 final report:** a full report built from the lab-manual doc, the mid-term doc, `docs/test-report.md` and `docs/benchmark-report.md`. It needs updated screenshots and a user-manual / installation section (from README).
7. **Git:** nothing is committed. Suggest the user commit; don't do it yourself.
   - Decide whether to include `.claude/` (allowlist) and `.vscode/`.
   - `frontend/dist/`, `.pytest_cache/`, `.ruff_cache/`, `benchmark/traces/`, `.env` and `backend/.db_ready` are gitignored.
   - `benchmark/results_run.log` and `traces_gen.log` are run logs and can be deleted or kept.
8. **Research extension:** the first iteration (ALEX-HB) is done. Optional follow-ups (bulk or query-aware migration, parameter sweep, literature check on XIndex and FINEdex) are listed in `docs/experiment-phase4.md` §6. The mid-term doc still shows only the baseline; add ALEX-HB to the draft and final reports.
9. **Minor ideas, not required:**
   - code-splitting to silence Vite's chunk-size warning;
   - a `run.bat stop` mode;
   - BRIN vs B-tree EXPLAIN comparison on `sensor_reading` as an in-app indexing mini-study (listed as optional in the original plan).

---

## 12. Lessons and fixes already made (don't re-break these)

- Deleting a referenced row raises **RestrictViolation** (not ForeignKeyViolation), because the FKs use ON DELETE RESTRICT.
- Readings recorded before a sensor's assignment start are not evaluated. Tests must use timestamps after the assignment.
- Audit rows never contain `password_hash`.
- In incident history, automatic incidents are attributed to "automatic detection".
- Exposure under a minute is shown in seconds (`exposure_seconds`). Live simulator readings are 2.5 s apart.
- The admin page's Audit tab is mounted only for QM and admin (otherwise investigators and operators get 403 noise).
- PageHeader subtitles render as a `div` (a `p` containing a `div` was invalid HTML).
- The dashboard's two tables stack until the `xl` breakpoint.
- CASE expressions comparing a bind parameter need `%s::text` casts in psycopg 3.
- JWT secret defaults must be at least 32 bytes (PyJWT warns otherwise).
- When editing Claude Docs documents, read before editing. In table cells use `find` replacements, not whole-table rewrites.
