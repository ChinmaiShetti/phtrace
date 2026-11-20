# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What PharmaTrace is

A DBMS mini-project: a PostgreSQL-backed web app that tracks temperature-sensitive pharmaceutical batches and manages cold-chain incidents. The concept spec is [idea.md](idea.md). Lab-manual figures are in `docs/lab-manual/`.

Core workflow: **sensor excursion → incident → trace affected batches → trace movements → investigation → corrective action → close**

There are two separate deliverables. Do not conflate them:
1. **The application:** `db/`, `backend/` and `frontend/`.
2. **The research benchmark** in `benchmark/`. It compares a tlx B+ tree with ALEX on synthetic traces, runs outside PostgreSQL in Docker, and is not integrated with the app.

## Commands

Backend (run from `backend/`; set `UV_PROJECT_ENVIRONMENT=.venv`, because the user's shell points uv at a shared environment):
- `uv sync`
- `uv run python -m scripts.reset_db`: drop, rebuild and seed the DB from `db/*.sql` (needs `.env` with `PG_ADMIN_PASSWORD`). Add `--no-seed` for an empty schema.
- `uv run uvicorn app.main:app --port 8000`
- `uv run pytest` (all tests), `uv run pytest tests/test_db_workflow.py::test_tc31_close_fully_resolved_incident` (one test)
- `uv run ruff check .`

Frontend (from `frontend/`): `npm run dev` (proxies `/api` to :8000), `npm run build` (tsc + vite).

Benchmark: `py -I benchmark/workload/gen.py`, `docker build -t pharmatrace-bench benchmark`, run with `traces/` and `results/` mounted, then `py -I benchmark/analysis/analyze.py`.

Dev tip: a throwaway Postgres can run in Docker (`pharmatrace-pg-dev` on port 5433, password `devpass`). Point the tools at it with `PG_PORT=5433 PG_ADMIN_PASSWORD=devpass`.

## Architecture: a thin API over a smart database

- Integrity and workflow live in PostgreSQL, because that is what the DBMS course grades. Changing a rule means editing the SQL files, not adding Python checks.
  - `03_functions.sql`: `dispatch_shipment` / `receive_shipment`, the multi-step transactions. Dispatch locks batch rows in `batch_id` order.
  - `04_triggers.sql`:
    - excursion detection (`trg_reading_evaluate` → `record_excursion` / `end_excursion`)
    - batch status transitions checked against the `batch_status_transition` table and the acting staff member's role
    - incident lifecycle and close rules
    - immutable sensor readings
    - a generic `SECURITY DEFINER` audit trigger
  - `05_views.sql`: everything derived (stock, exposure, dashboard, reports). Never store derived values.
- **Acting user:** each API request runs in one transaction as the least-privileged `pharmatrace_app` role (`app/db.py`). It first calls `set_config('app.current_staff_id', …, true)`, and `current_staff_id()` in SQL reads it back. Status-changing endpoints also set `app.change_reason`, which lands in `audit_log.reason`.
- **API checks and DB checks:** FastAPI checks roles (`require(...)` in `app/auth.py`) and input shape (Pydantic). The DB enforces the same rules again. DB errors are mapped to HTTP status codes in `app/errors.py`, and trigger messages are written to be shown to users.
- **Lab-manual schema:** table and column names match lab manual Section 6.5. Keep them in sync. The ER diagram and normalisation docs depend on them.
- **Test fixtures:** tests rebuild `pharmatrace_test` once per session and TRUNCATE before each test. `tests/conftest.py::world` provides a small consistent data set.

## Domain and claims constraints

- Batch decisions (hold, quarantine, release, return, dispose) are recorded statuses set by authorised users. The software never decides on its own whether a medicine is safe. An excursion links only the batches whose own product limits were breached.
- Temperature limits and severity thresholds are illustrative.
- Do not claim novelty for cold-chain monitoring or learned indexing. Report benchmark results as measured, including where ALEX loses.
- The user commits to git themselves. Do not commit or push.
