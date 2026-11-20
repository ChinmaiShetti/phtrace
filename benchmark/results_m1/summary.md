# Index benchmark results

Environment:

- date: 2026-11-08T13:20:45Z
- compiler: g++ (GCC) 14.4.0
- cpu: AMD Ryzen 5 7535HS with Radeon Graphics
- cores: 12
- memory: 7533.2 MB
- kernel: 6.6.87.2-microsoft-standard-WSL2
- alex_commit: 4370da6aa8b509fdc9b0d2c49faa0624b0078589
- tlx_commit: 2dd63ab839909f0b43cd02108a1869c4670b2c8e
- reps: 3
- indexes: alexhb
- hb_args: --hb-migrate 1

Medians over 3 repetitions (min-max in brackets). Latencies in nanoseconds per operation.

Replay check: identical results for every index and repetition.

## Bulk load

| Index | Keys | Load time per key (ns) | Index memory (MB) |
|---|---|---|---|
| ALEX-HB (hot buffer) | 8,640,000 | 99 | 190 |

## Throughput per phase (operations per second)

| Phase | ALEX-HB (hot buffer) | ALEX-HB (hot buffer) / B+ tree |
|---|---|---|
| P1 stable | 2.01 M (1.99-2.02) |
| P2 ingestion spike | 2.04 M (1.80-2.10) |
| P3 localised incident | 4.38 M (4.34-4.39) |
| P4 investigation | 0.63 M (0.55-0.65) |
| P5 recovery | 2.97 M (2.06-3.25) |
| P6 combined shift | 8.25 M (7.48-8.59) |

## Memory after each phase (MB, process RSS above baseline)

| Phase | ALEX-HB (hot buffer) |
|---|---|
| P1 stable | 262 |
| P2 ingestion spike | 302 |
| P3 localised incident | 302 |
| P4 investigation | 414 |
| P5 recovery | 415 |
| P6 combined shift | 415 |

## ALEX-HB (hot buffer): ALEX structure after each phase (repetition 1)

| Phase | Data nodes | Model nodes | Expand+scale | Expand+retrain | Downward splits | Sideways splits |
|---|---|---|---|---|---|---|
| load | 1,001 | 1 | 0 | 0 | 0 | 0 |
| P1 stable | 2,016 | 23 | 0 | 3 | 22 | 992 |
| P2 ingestion spike | 3,621 | 80 | 206 | 107 | 79 | 2,540 |
| P3 localised incident | 3,621 | 80 | 206 | 109 | 79 | 2,540 |
| P4 investigation | 3,932 | 89 | 758 | 353 | 88 | 2,842 |
| P5 recovery | 3,936 | 89 | 851 | 395 | 88 | 2,846 |
| P6 combined shift | 3,936 | 89 | 851 | 395 | 88 | 2,846 |

## ALEX-HB (hot buffer): hot buffer after each phase (repetition 1; W=4096, H=64, M=1)

| Phase | Hot sensors now | Keys in buffer | Max buffer so far | Inserts routed to buffer (total) | Keys migrated to ALEX (total) |
|---|---|---|---|---|---|
| P1 stable | 0 | 0 | 0 | 0 | 0 |
| P2 ingestion spike | 0 | 0 | 0 | 0 | 0 |
| P3 localised incident | 10 | 499,329 | 499,329 | 499,329 | 0 |
| P4 investigation | 0 | 0 | 499,358 | 499,358 | 499,358 |
| P5 recovery | 0 | 0 | 499,358 | 499,358 | 499,358 |
| P6 combined shift | 10 | 499,084 | 499,358 | 998,442 | 499,358 |

Timer overhead (median of back-to-back clock reads): 20 ns; it is included in every latency.
