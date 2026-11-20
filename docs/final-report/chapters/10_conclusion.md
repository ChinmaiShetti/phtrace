# 10. Conclusion and Future Work

## 10.1 Conclusion

PharmaTrace meets all of its objectives.

**The database.** A normalised PostgreSQL schema, of 20 tables in 3NF (also BCNF), enforces the cold-chain workflow itself:

- excursions raise incidents automatically and link only the batches whose own limits were breached;
- dispatching and receiving are atomic and safe under concurrency;
- batch decisions follow role-based transition rules;
- an incident closes only when every investigation, corrective action and batch assessment is complete;
- every decision is audited, with who, when, what and why.

**The application.** The web application exposes this through 12 pages and 50 API endpoints. Validation and authorisation are enforced at three layers: browser, API and database.

**Testing.** All 34 planned test cases pass, each with the system's actual response recorded as evidence. All 68 automated tests pass, and the complete scenario runs end to end through the browser.

**The Innovative Experiment.** A learned index (ALEX) is about twice as fast as a B+ tree for reads on this workload, but pays for sudden distribution shifts with insert pauses of tens of milliseconds and twice the memory. The proposed ALEX-HB variant buffers hot sensors' inserts:

- it removes those pauses during incidents (worst insert 0.1 ms instead of 37.5 ms);
- it gives the best throughput of all configurations in the combined-shift phase;
- it costs half of ALEX's throughput in the investigation phase, where its deferred migration runs.

Both the gains and the losses are reported as measured.

## 10.2 Limitations

- Sensor readings are simulated; there is no hardware integration.
- Temperature limits and severity thresholds are illustrative, not regulatory values.
- The index benchmark is single-threaded and in-memory, and is not integrated into PostgreSQL.
- The application has been demonstrated on one machine; deployment (HTTPS, a production secret store, backups) is outside the project's scope.

## 10.3 Future work

1. **Index research:** faster bulk migration and query-aware migration for ALEX-HB; a parameter sweep over the window W and threshold H; a literature comparison with XIndex and FINEdex.
2. **In-database indexing:** compare PostgreSQL's B-tree and BRIN indexes on `sensor_reading` at tens of millions of rows using `EXPLAIN (ANALYZE, BUFFERS)`.
3. **Product-specific stability budgets:** allowed cumulative time out of range, instead of simple limits.
4. **Notifications:** e-mail alerts when an incident opens; escalation of overdue corrective actions.
5. **Data import:** CSV and API ingestion from real data loggers, with sensor calibration records.
