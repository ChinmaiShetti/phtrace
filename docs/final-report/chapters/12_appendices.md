# Appendix A. Installation and User Guide

**Requirements:**

- Windows 10/11 with PostgreSQL 18 installed as a service;
- Python 3.12 with uv;
- Node.js 22;
- Docker, only for the benchmark.

**First run:**

1. Copy `.env.example` to `.env`, and set `PG_ADMIN_PASSWORD` to the local PostgreSQL `postgres` password.
2. Double-click **`run.bat`**. On the first run it:
   - installs the backend and frontend dependencies;
   - builds the `pharmatrace` database with demonstration data;
   - starts the API (port 8000) and the web application (port 5173) in two windows;
   - opens the browser at http://localhost:5173.
3. **`run.bat reset`** rebuilds the database with fresh demonstration data. Do this shortly before a demonstration, because the data's times are relative to when it was loaded.
4. **`stop.bat`** stops the API and the web application. The database service keeps running.

**Demonstration accounts:**

| Role | Email | Password |
|---|---|---|
| Administrator | admin@pharmatrace.local | admin123 |
| Operator | operator@pharmatrace.local | operator123 |
| Investigator | investigator@pharmatrace.local | investigator123 |
| Investigator | investigator2@pharmatrace.local | investigator2123 |
| Quality manager | qm@pharmatrace.local | qm123 |

**Manual commands** (for developers):

```
cd backend
set UV_PROJECT_ENVIRONMENT=.venv
uv sync
uv run python -m scripts.reset_db          # build and seed the database
uv run uvicorn app.main:app --port 8000    # API; interactive docs at /docs
uv run pytest                              # 68 automated tests
uv run python -m scripts.evidence          # TC01–TC34 evidence run
cd ..\frontend
npm install
npm run dev                                # web app at http://localhost:5173
```

**Using the system:**

1. **Shipment lifecycle (operator).** Shipments → New shipment, with origin, destination, vehicle, arrival, sensor and batches. Then open the shipment and press Dispatch, and later Confirm arrival.
2. **Simulate a failure (administrator).** Dashboard → choose an in-transit shipment → Simulate failure.
3. **Investigate (quality manager, then investigator).** On the incident page:
   - the quality manager assigns an investigator;
   - the investigator assesses each batch, records a decision (for example, on hold), adds corrective actions and completes the investigation.
4. **Resolve.** The quality manager marks the incident resolved, records release or quarantine decisions, then closes it once every action is complete.

# Appendix B. API Reference (50 endpoints)

All endpoints are under `/api`. Every endpoint except login and health requires a `Bearer` token. Roles: Op = operator, Inv = investigator, QM = quality manager, Adm = administrator.

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | /auth/login | Log in (form: username, password) and receive a JWT | Public |
| GET | /auth/me | Current user | Any |
| GET | /health | Liveness check | Public |
| GET, POST | /products | List / register products | Any / Op, QM, Adm |
| PUT | /products/{id} | Update a product | Op, QM, Adm |
| GET, POST | /batches | List and search / register a batch (with intake movement) | Any / Op, QM, Adm |
| GET | /batches/{id}/trace | Stock, movements, shipments, incidents, decision history | Any |
| POST | /batches/{id}/status | Record a batch decision with a reason | Inv, QM (plus the database rule) |
| GET | /batch-transitions | Allowed transitions per role | Any |
| GET, POST | /facilities | List / add facilities (with phone numbers) | Any / Op, QM, Adm |
| GET, POST | /vehicles | List / add vehicles | Any / Op, QM, Adm |
| PATCH | /vehicles/{id} | Change refrigeration status | Op, QM, Adm |
| GET, POST | /sensors | List / register sensors | Any / Op, QM, Adm |
| PATCH | /sensors/{id} | Change installation status | Op, QM, Adm |
| POST | /sensor-assignments | Attach a sensor to a shipment or facility | Op, QM, Adm |
| POST | /sensor-assignments/{id}/end | Detach a sensor | Op, QM, Adm |
| GET | /staff | List staff | Any |
| POST | /staff | Create an account | Adm |
| PATCH | /staff/{id} | Change role, status or password | Adm |
| GET, POST | /shipments | List / create (with lines and sensor) | Any / Op, QM, Adm |
| GET | /shipments/{id} | Detail: lines, limits, sensors, checkpoints, timeline, incidents | Any |
| POST | /shipments/{id}/batches | Add a line | Op, QM, Adm |
| DELETE | /shipments/{id}/batches/{batch} | Remove a line | Op, QM, Adm |
| POST | /shipments/{id}/dispatch | `dispatch_shipment()` | Op, Adm |
| POST | /shipments/{id}/receive | `receive_shipment()` | Op, Adm |
| POST | /shipments/{id}/cancel | Cancel a planned shipment | Op, Adm |
| POST | /shipments/{id}/checkpoints | Record a checkpoint | Op, Adm |
| POST | /readings | Ingest readings (idempotent; returns counts) | Op, Adm |
| GET | /readings | Query by sensor, shipment, time, quality, out of limits | Any |
| GET, POST | /incidents | List / report a manual incident | Any / Op, Inv, QM |
| GET | /incidents/{id} | Full incident detail | Any |
| POST | /incidents/{id}/status | Change status with a reason | Inv, QM (plus the database rules) |
| POST | /incidents/{id}/investigations | Assign an investigator | QM |
| PATCH | /investigations/{id} | Findings and status | Assignee, QM |
| PATCH | /incidents/{id}/batches/{batch} | Assess a batch | Inv, QM |
| POST | /investigations/{id}/actions | Add a corrective action | Inv, QM |
| PATCH | /actions/{id} | Update an action's status | Assignee, Inv, QM |
| GET | /dashboard | Counters, active shipments, recent incidents | Any |
| GET | /reports, /reports/{key} | Report list / one report (whitelisted views) | Any |
| GET | /audit | Audit log | QM, Adm |
| POST | /admin/simulate-excursion | Start a simulated refrigeration failure | Adm |
| POST | /admin/backfill | Fill normal readings up to now | Adm, Op |

A row with two methods (for example "GET, POST") or two paths covers two endpoints, so the 42 rows above add up to 50 endpoints.

# Appendix C. Test Evidence in Full

Generated by `backend/scripts/evidence.py`; raw data is in `docs/final-report/evidence/test_evidence.json`.

<<EVIDENCE_DETAIL>>

# Appendix D. Key SQL Listings

These listings are copied from the source files at build time.

### D.1 `dispatch_shipment` (atomic, concurrency-safe dispatch), from `db/03_functions.sql`

```sql
<<SQL:db/03_functions.sql:dispatch_shipment>>
```

### D.2 `trg_reading_evaluate` (excursion detection), from `db/04_triggers.sql`

```sql
<<SQL:db/04_triggers.sql:trg_reading_evaluate>>
```

### D.3 `record_excursion` (open or update an incident), from `db/04_triggers.sql`

```sql
<<SQL:db/04_triggers.sql:record_excursion>>
```

### D.4 `trg_incident_lifecycle` (closing rules), from `db/04_triggers.sql`

```sql
<<SQL:db/04_triggers.sql:trg_incident_lifecycle>>
```

### D.5 `trg_batch_status_check` (role-based decisions), from `db/04_triggers.sql`

```sql
<<SQL:db/04_triggers.sql:trg_batch_status_check>>
```

### D.6 `v_dashboard`, from `db/05_views.sql`

```sql
<<VIEW:db/05_views.sql:v_dashboard>>
```

# Appendix E. Project Structure

```
DBMSEL/
  db/                 00_extensions … 06_grants.sql, queries/demo.sql
  backend/            app/ (FastAPI), scripts/ (reset_db, seed, evidence, test_report), tests/ (68 tests)
  frontend/           src/ (React + TypeScript: 12 pages)
  benchmark/          workload/gen.py, src/bench.cpp, Dockerfile, run_all.sh, analysis/analyze.py,
                      results/ (4 configurations), results_baseline/, results_m1/
  tools/e2e/          check.mjs, demo.mjs, report_shots.mjs (browser tests)
  docs/               lab-manual/ (diagrams), final-report/ (this report), benchmark-report.md,
                      experiment-phase4.md, test-report.md
  run.bat, stop.bat   launchers
  README.md, HANDOFF.md, CLAUDE.md, idea.md
```

# Appendix F. Demonstration Script

1. **Normal operation.** Log in as the administrator and show the dashboard counters, which are SQL views.
2. **Failure.** In the simulator panel, choose SH004 and press Simulate failure. Readings arrive every 2.5 s.
3. **Incident.** INC0003 appears, raised by the database. Show the chart, the exposure, the peak and the three breached batches.
4. **Trace.** Open a batch: chain of custody, stock per facility, incidents.
5. **Investigate.**
   - The quality manager assigns the investigator.
   - The investigator assesses the batches, puts one on hold, adds an action and completes the investigation.
6. **Resolve.**
   - Close the incident too early: the database refuses.
   - The operator completes the action.
   - The quality manager releases the batch and closes the incident. Show the history.
7. **Database.** Run `db/queries/demo.sql` in psql (listing below).
8. **Research.** Show Chapter 9's figures.

```sql
<<FILE:db/queries/demo.sql>>
```
