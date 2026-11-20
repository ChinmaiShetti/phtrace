# 7. Testing

## 7.1 Strategy

| Level | What is tested | Tool | Result |
|---|---|---|---|
| Database (unit) | Keys, constraints, triggers, functions, views, privileges, run directly against PostgreSQL | pytest + psycopg | Pass |
| Transactions and concurrency | Atomic dispatch and receipt, rollback on partial failure, two simultaneous sessions | pytest with two real connections and threads | Pass |
| API (integration) | Login, tokens, role checks, validation, error mapping, full workflow over HTTP | pytest + FastAPI TestClient | Pass |
| Evidence run (TC01–TC34) | Every lab-manual test case on a fresh database, recording the **actual** system response | `backend/scripts/evidence.py` | 34 / 34 pass |
| End-to-end (UI) | Every page as every role (no console errors); the full demonstration scenario through the browser | Playwright driving Microsoft Edge (`tools/e2e/`) | Pass |

Test design used equivalence partitioning and boundary values: quantity 0 and 1; expiry one day after manufacture; a reading exactly beyond the limit; future timestamps. Every constraint was given both a positive and a negative case.

**Test environment:**

- PostgreSQL 18 in a separate database (`pharmatrace_test` for pytest, `pharmatrace_evidence` for the evidence run), rebuilt from the SQL scripts;
- Python 3.12;
- Windows 11.

**Test data:** each test starts from the same small data set:

- 4 staff members (one per role);
- 3 products: a vaccine at 2–8 °C, a syrup at 2–25 °C and a tablet at 15–25 °C;
- 3 facilities and 1 vehicle;
- batches B1–B4, plus BEXP, which has already expired;
- 3 sensors.

## 7.2 Results summary

<<TEST_SUMMARY>>

![Test cases by module](figures/tests_by_module.png){width=85%}

*Figure 7.1: Lab-manual test cases TC01–TC34 by module (evidence run).*

![Automated suite](figures/tests_pytest_by_file.png){width=85%}

*Figure 7.2: The automated pytest suite, by file.*

## 7.3 Test cases with actual results

The table below is generated from `docs/final-report/evidence/test_evidence.json`. The **Actual result** column is the system's real output: the exact PostgreSQL error, the row counts or the HTTP response. Appendix C lists every case in full.

<<TEST_TABLE>>

## 7.4 Selected proofs explained

- **TC12, rollback.** The dispatch processed B1 first, then failed on B2 ("Insufficient stock of batch B2"). Afterwards, the shipment had zero movements and was still *planned*, and B1's stock was unchanged at 1,000. So the whole dispatch was undone, including the part that had already succeeded.
- **TC14, concurrency.** Session 1 dispatched 800 of B1's 1,000 units and held the row lock. Session 2 tried to dispatch another 800 and **waited** for that lock. When session 1 committed, session 2 re-read the stock (200) and failed cleanly. The final stock was 200: never negative, and no unit was sold twice.
- **TC24, precise tracing.** A 10.1 °C reading on a shipment carrying a vaccine (limit 8 °C) and a syrup (limit 25 °C) linked **only** the vaccine batch. The system does not condemn every batch on board.
- **TC26, defence in depth.** The operator's request was refused by the API (HTTP 403). The same change attempted directly in SQL, as that operator, was refused by the database trigger ("Role operator may not change batch B1 from available to on_hold").
- **TC30, workflow rule.** Closing was refused twice, with a specific reason each time: first because a corrective action was still pending, then because the affected batches were not assessed.

## 7.5 Automated test suite

All 68 automated tests pass (`uv run pytest`, last run on the date of this report):

<<PYTEST_TABLE>>

## 7.6 End-to-end tests through the user interface

Two browser scripts drive the real application in Microsoft Edge:

- **Page sweep (`check.mjs`).** It logs in as each of the four roles and opens all 13 page routes. Any browser console error or server error counts as a failure. Result: **52 of 52 page/role combinations clean.**
- **Demonstration scenario (`demo.mjs` and `report_shots.mjs`).** It performs the complete incident workflow through the user interface, as four different users:
  1. simulate a failure;
  2. the database raises the incident;
  3. assign an investigator;
  4. assess the batches, hold one, add an action, record findings;
  5. try to close too early (refused);
  6. complete the action;
  7. release the batch and close.

  Result: **the flow completes**. Every step is shown in Chapter 8.

Two interface defects were found and fixed during this testing:
- invalid HTML nesting in page subtitles;
- table columns clipped inside half-width cards.

One misleading attribution was also corrected: automatically raised incidents are now shown as created by "automatic detection".
