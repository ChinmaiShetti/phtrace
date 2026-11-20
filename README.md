# PharmaTrace

Pharmaceutical cold-chain integrity, traceability and incident management. DBMS mini project (CD2521A), RV College of Engineering.

A temperature excursion on a sensor becomes an incident. The database traces the affected batches and where they went, and staff record the investigation, batch decisions and corrective actions until the incident is closed. A separate research benchmark compares a B+ tree with a learned index (ALEX) on workloads modelled on this scenario.

## Layout

| Folder | Contents |
|---|---|
| `db/` | Schema in order: tables, indexes, functions (dispatch/receive transactions), triggers, views, grants. `db/queries/demo.sql` holds the live-demo queries. |
| `backend/` | FastAPI API, seed data, simulator and the pytest suite (68 tests) |
| `frontend/` | React + TypeScript web app (Vite, Mantine) |
| `benchmark/` | Workload generator, C++ harness, Dockerfile, results and analysis |
| `docs/lab-manual/` | ER diagram and DFD figures (PNG and PDF) |

## Setup (Windows, once)

Requirements: PostgreSQL 18 (local service), Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22. Docker is needed only for the benchmark.

1. Copy `.env.example` to `.env` and set `PG_ADMIN_PASSWORD` to your local `postgres` password.
2. Build the database and demo data:
   ```
   cd backend
   set UV_PROJECT_ENVIRONMENT=.venv
   uv sync
   uv run python -m scripts.reset_db
   ```
   This creates the `pharmatrace` database, the roles `pharmatrace_owner` and `pharmatrace_app`, the schema and the seed data. It is safe to rerun: it drops and rebuilds everything, with timestamps relative to now. Run it again just before a demo.
3. Install the frontend: `cd frontend && npm install`

## Run

Use two terminals:

```
cd backend  && uv run uvicorn app.main:app --port 8000      # API, docs at http://localhost:8000/docs
cd frontend && npm run dev                                   # app at http://localhost:5173
```

Demo logins (demo only):

| Role | Email | Password |
|---|---|---|
| Operator | operator@pharmatrace.local | operator123 |
| Investigator | investigator@pharmatrace.local | investigator123 |
| Quality manager | qm@pharmatrace.local | qm123 |
| Administrator | admin@pharmatrace.local | admin123 |

To simulate a refrigeration failure, sign in as the administrator, open the Dashboard, pick an in-transit shipment and press **Simulate failure**. A reading arrives every 2.5 seconds, and the database raises the incident by itself.

## Test

```
cd backend
uv run pytest                                              # all tests (uses a separate pharmatrace_test database)
uv run pytest tests/test_db_transactions.py -k rollback    # one test
uv run ruff check .
cd ../frontend && npm run build                            # type-check + production build
```

## Research benchmark

```
cd benchmark
py -I workload/gen.py                                      # writes traces/ (8.64 M keys, 6 phases x 1 M ops)
docker build -t pharmatrace-bench .
docker run --rm -v "%cd%/traces:/traces" -v "%cd%/results:/results" pharmatrace-bench
py -I analysis/analyze.py                                  # results/summary.md and results/figures/*.png
```

The benchmark runs on its own, outside PostgreSQL. It measures the indexes on workloads modelled on the application's sensor data; it does not change how the application's queries run.

## Notes

- Temperature limits in the demo data are illustrative configured values, not real product specifications.
- PharmaTrace records decisions made by authorised staff. It never decides by itself whether a medicine is safe to use.
