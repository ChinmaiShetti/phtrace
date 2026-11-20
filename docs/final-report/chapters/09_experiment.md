# 9. Innovative Experiment: Learned Index under Cold-Chain Workloads

## 9.1 Question

Sensor readings in PharmaTrace are looked up by (sensor, time). During a refrigeration failure the workload shifts in three ways:

- a few sensors start reporting far more often;
- investigators query a narrow time window again and again;
- later, activity returns to normal.

The questions are:

1. Does a learned index, ALEX [7], keep its advantage over a B+ tree under such shifts?
2. What does adapting to the shifts cost?
3. Can a simple policy reduce that cost?

The benchmark runs on its own, outside PostgreSQL. It evaluates the index structures on workloads modelled on the application; it does not change how the application's own SQL runs.

## 9.2 Method

| Item | Setting |
|---|---|
| Keys | `sensor_id << 40 | epoch_seconds`: unique, ordered by sensor then time; 8-byte payload |
| Initial data | 1,000 sensors × 30 days at 5-minute intervals = **8,640,000 keys**, bulk-loaded |
| Workload | Six phases × 1,000,000 operations, generated once (fixed seed); **every configuration replays identical files** |
| Configurations | B+ tree (tlx `btree_map`, commit 2dd63ab); ALEX (`alex::Alex`, commit 4370da6); **ALEX-HB** (proposed, section 9.4); ALEX-HB without migration (ablation) |
| Build and run | g++ 14.4, `-O3 -march=native`, single thread, in Docker on WSL2; AMD Ryzen 5 7535HS; 5 repetitions per configuration, each in a fresh process, with the run order rotated |
| Measurements | Each operation timed individually (20 ns timer overhead included); throughput; p50/p95/p99/p99.9/maximum latency; share of time in the slowest 1 %; memory (RSS); ALEX's internal counters |
| Correctness | Lookup hits and payload checksums were **identical** for every configuration and repetition |

| Phase | Simulates | Operation mix |
|---|---|---|
| P1 stable | Normal monitoring | 80 % lookups, 10 % inserts (all sensors, 5-minute steps), 10 % one-hour range scans |
| P2 ingestion spike | Many more readings | 60 % inserts, 35 % lookups, 5 % ranges |
| P3 localised incident | 10 failing sensors report every second | 50 % inserts on those sensors, 50 % lookups |
| P4 investigation | Repeated queries on the incident window | Zipf(0.99) over incident readings: 47.5 % lookups, 47.5 % ten-minute ranges, 5 % inserts |
| P5 recovery | Back to normal | Same mix as P1 |
| P6 combined shift | A second failure while it is being investigated | 50 % inserts on 10 new sensors, 50 % lookups of their newest readings |

## 9.3 Baseline: ALEX against the B+ tree

**Reads favour ALEX.**
- P1 lookups: median 231 ns for ALEX against 521 ns for the B+ tree.
- P4 lookups: 101 ns against 321 ns.
- P4 ten-minute range scans: 762 ns against 3,717 ns.

**ALEX's insert cost is concentrated in rare reorganisations.**
- In P1, P3 and P6, its slowest 1 % of inserts took 81–84 % of all its insert time.
- Its worst single insert pauses were 27 ms (P1), 37.5 ms (P3) and 23 ms (P6). The B+ tree's worst was 0.44 ms (P4).
- ALEX's own counters show the adaptation work arriving in bursts at the distribution shifts: expand-and-scale operations went 0 → 206 → 619 → 1,008 across the phases.

**Memory and loading.**
- After all phases, ALEX used 510 MB against the B+ tree's 244 MB.
- Its bulk load was slower: 104 ns against 17 ns per key.

## 9.4 Proposed policy: ALEX-HB (hot-range buffer)

ALEX-HB absorbs hot-spot inserts in a small B+ tree placed in front of ALEX, and moves them into ALEX later, once the hot spot has cooled.

- **Detect hot sensors.** Over the last W = 4,096 inserts, a sensor with H = 64 or more inserts is *hot*. It cools when its count falls below 32.
- **Route inserts.** Hot sensors' inserts go into the buffer; all others go straight into ALEX.
- **Read from both.** A lookup checks the buffer only if the key's sensor has buffered keys. A range scan adds the results of both structures; each key lives in exactly one.
- **Deferred migration.** While no sensor is hot, each operation moves up to M = 4 buffered keys into ALEX. The cost is counted in that operation's measured time.

Update buffers placed in front of learned indexes appear in earlier designs (for example XIndex and FINEdex). What is tested here is a hot-sensor trigger with deferred migration, under incident-driven workloads.

## 9.5 Results (throughput, million operations per second, median of 5 repetitions)

| Phase | B+ tree | ALEX | **ALEX-HB** | ALEX-HB, no migration |
|---|---|---|---|---|
| P1 stable | 1.53 | 2.05 | 2.02 | 2.04 |
| P2 ingestion spike | 2.38 | 2.05 | 2.13 | 2.08 |
| P3 localised incident | 2.59 | 2.66 | **4.35** | 4.37 |
| P4 investigation | 0.46 | **1.79** | 0.89 | 0.42 |
| P5 recovery | 1.79 | 3.40 | 3.29 | 3.26 |
| P6 combined shift | 6.98 | 3.57 | **8.49** | 8.25 |

![Throughput, four configurations](figures/bench_throughput_4configs.png){width=100%}

*Figure 9.1: Throughput per phase. Whiskers show the minimum and maximum of the 5 repetitions.*

| Insert latency | ALEX p99.9 | ALEX worst | ALEX-HB p99.9 | ALEX-HB worst | Time in the slowest 1 %: ALEX → ALEX-HB |
|---|---|---|---|---|---|
| P3 localised incident | 3,466 ns | 37.5 ms | 581 ns | 0.10 ms | 81 % → 5 % |
| P6 combined shift | 2,596 ns | 23.4 ms | 541 ns | 0.07 ms | 84 % → 5 % |

![Latency](figures/bench_latency_4configs.png){width=100%}

*Figure 9.2: Lookup latency (left) and the insert tail: p99.9 and worst pause (right), on log scales.*

| Memory above baseline (MB) | After P3 | After P4 | After P6 |
|---|---|---|---|
| B+ tree | 216 | 221 | 244 |
| ALEX | 410 | 413 | 510 |
| ALEX-HB | 302 | 408 | 409 |
| ALEX-HB, no migration | 302 | 307 | 308 |

![Memory](figures/bench_memory_4configs.png){width=75%}

*Figure 9.3: Index memory after each phase.*

## 9.6 Analysis

**Where ALEX-HB wins.** In both incident phases, ALEX's long reorganisation pauses disappear:

- In **P3**, throughput is 1.64× plain ALEX, and the worst insert falls from 37.5 ms to 0.1 ms.
- In **P6**, throughput is 2.4× plain ALEX. ALEX-HB is the fastest of all four configurations, 1.22× the B+ tree.
- After P6, it uses 101 MB less memory than ALEX.

**Where it loses.**

- **Migration lands on the investigation.** During P3, the buffer collected about 499,000 keys from the 10 hot sensors. In P4 no sensor is hot, so migration begins, and it overlaps exactly with investigators querying those same keys:
  - P4 throughput halves (0.89 against 1.79 million operations per second for ALEX), though it remains 1.9× the B+ tree;
  - lookup p99.9 rises to 15.7 µs, with pauses up to 18 ms, because ALEX's node expansions now happen during migration instead of during the burst.
- **Without migration,** P4 is slower still (0.42), because every investigation query also searches the large buffer.
- **Slower migration did not help.** A sensitivity run with M = 1 (3 repetitions) gave 0.63 in P4, worse than with M = 4, because migrating more slowly lengthens the overlap with the queries.
- **P1, P2 and P5 are unchanged**, as expected: no sensor becomes hot in those phases.

**Conclusion.** Buffering hot ranges removes ALEX's pauses during insert bursts. The limiting factor is *when* the buffered keys are merged back. Two directions follow from the measurements, and neither has been tested yet:

- **faster migration:** merge a cooled sensor's range in one step, for example by bulk-loading a new ALEX node;
- **query-aware migration:** delay merging keys that are still being queried.

## 9.7 Threats to validity

- The workload is synthetic, with one seed and one key layout.
- The indexes run single-threaded and in memory: no concurrency, no disk, no database engine.
- The runs were inside Docker on WSL2 on a laptop. Absolute numbers vary between runs: the B+ tree's P1 throughput was 1.89 million in an earlier run and 1.53 million in this one. Compare configurations within a single run.
- The libraries were used with default settings.
