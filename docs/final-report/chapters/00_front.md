---
title: "PharmaTrace: Pharmaceutical Cold-Chain Integrity, Traceability and Incident Management System"
subtitle: "DBMS Mini Project — Final Report"
author:
  - "Chinmai Kiran Shetti (USN 1RV24CS068)"
  - "Department of Computer Science and Engineering, RV College of Engineering, Bengaluru"
  - "Database Management Systems Laboratory (CD2521A)"
date: "November 2026"
lang: en-GB
---

# Abstract {.unnumbered}

Temperature-sensitive medicines such as vaccines, insulin and biologics must stay within configured temperature limits from the warehouse to the hospital. When a refrigeration unit fails during storage or transport, an organisation must quickly answer:

- which shipment or facility was affected;
- which batches were inside, and whose limits were actually breached;
- how long they were exposed, and where they went next;
- who investigated, what was decided, and which corrective actions were completed.

PharmaTrace answers these questions from one normalised relational database.

The system was implemented as a three-tier web application:

| Tier | Implementation |
|---|---|
| Database | PostgreSQL 18: 20 tables in third normal form, 27 foreign keys, 50 CHECK constraints and 1 EXCLUDE constraint, 24 functions, 18 triggers, 14 views |
| Backend | Python FastAPI (50 endpoints) |
| Frontend | React with TypeScript (12 pages) |

The integrity rules and the workflow are enforced by the database itself:

- a temperature excursion raises an incident automatically, linking only the batches whose own product limits were breached;
- dispatching a shipment is a single atomic, concurrency-safe transaction;
- batch decisions follow role-based transition rules;
- an incident can be closed only by a quality manager, after every investigation, corrective action and batch assessment is complete;
- every decision is written to an audit log.

All 34 planned test cases pass. The evidence was produced by running each case against a fresh database and recording the system's actual response. The full suite of 68 automated tests also passes, and the complete scenario was driven end to end through the web interface.

For the Innovative Experiment, a B+ tree and a learned index (ALEX) were benchmarked on 8.64 million sensor-reading keys under six workload phases modelled on the cold-chain scenario. A proposed variant, ALEX-HB, was then implemented and measured. It absorbs insert hot spots in a small B+ tree buffer and migrates them later.

| Measurement | Result |
|---|---|
| Lookups, ALEX vs B+ tree | About 2× faster |
| Worst insert pause during insert bursts, ALEX | Up to 37.5 ms |
| Worst insert pause, ALEX-HB | Below 0.11 ms |
| Throughput in the combined-shift phase, ALEX-HB vs plain ALEX | 2.4× higher |
| Cost of ALEX-HB | Halved throughput in the investigation phase, where its deferred migration runs |

**Keywords:** relational database, normalisation, transactions, triggers, cold chain, traceability, learned index, ALEX.
