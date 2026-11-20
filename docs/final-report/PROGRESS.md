# Final report: progress log

Goal: one complete final report of the whole project (Markdown master, plus Word and PDF), with evidence for every test case (actual database/API responses), screenshots of every screen, form and demo step, and charts.

Output folder: `docs/final-report/`
- `PharmaTrace_Final_Report.md`: master text (pandoc source)
- `PharmaTrace_Final_Report.docx` / `.pdf`: generated (`pandoc` 3.11 at `D:\tools\engines\Pandoc`; PDF via Word COM)
- `evidence/`: `test_evidence.md` + `.json` from `backend/scripts/evidence.py`, plus the pytest junit run
- `screenshots/`: from `tools/e2e/report_shots.mjs` (needs API :8000 and Vite :5173 on freshly seeded data)
- `figures/`: charts from `docs/final-report/make_figures.py`, plus copies of the ER, DFD and benchmark figures

Environment used: Docker dev DB `pharmatrace-pg-dev` on port 5433 (`PG_PORT=5433 PG_ADMIN_PASSWORD=devpass`), so the user's local database is never touched.

| When | Step | Status |
|---|---|---|
| 2026-11-08 | `stop.bat` written (kills the run.bat windows plus anything listening on 8000/5173) | Done (not yet run by the user) |
| 2026-11-08 | Folder structure and this log | Done |
| 2026-11-08 | `backend/scripts/evidence.py` written and run: TC01–TC34 with actual DB/API output → `evidence/test_evidence.{md,json}` | Done, 34/34 pass |
| 2026-11-08 | pytest suite rerun → `docs/test-report.md`, junit copied to `evidence/pytest_junit.xml` | Done |
| 2026-11-08 | `tools/e2e/report_shots.mjs` written and run → 44 screenshots in `screenshots/` (all screens, 4 form-validation proofs, 3 role-restriction proofs, 13 demo steps D01–D13) | Done. Table-layout fix confirmed visually. Monitoring shot cropped to one screen (fix in the script) |
| 2026-11-08 | `make_figures.py`: architecture, incident lifecycle, batch workflow, test charts (from the evidence + junit files), project size; copied ER/DFD/benchmark figures → `figures/` | Done; fixed a wrong arrow direction (on_hold → quarantined) and label overlaps after visual check |
| 2026-11-08 | Writing `PharmaTrace_Final_Report.md` | IN PROGRESS |
| 2026-11-08 | Chapters written: `chapters/00_front … 12_appendices.md`; `build_report.py` assembles them, fills test tables, evidence, SQL listings and demo.sql from source, runs pandoc | Done: `.md` (1,982 lines) + `.docx` built |
| 2026-11-08 | PDF export via Word COM (TOC refresh, fit tables and images) | IN PROGRESS |
