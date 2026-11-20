# Index benchmark results

Environment:

- date: 2026-10-28T12:56:04Z
- compiler: g++ (GCC) 14.4.0
- cpu: AMD Ryzen 5 7535HS with Radeon Graphics
- cores: 12
- memory: 7533.2 MB
- kernel: 6.6.87.2-microsoft-standard-WSL2
- alex_commit: 4370da6aa8b509fdc9b0d2c49faa0624b0078589
- tlx_commit: 2dd63ab839909f0b43cd02108a1869c4670b2c8e
- reps: 5

Medians over 5 repetitions (min-max in brackets). Latencies in nanoseconds per operation.

Replay check: identical results for every index and repetition.

## Bulk load

| Index | Keys | Load time per key (ns) | Index memory (MB) |
|---|---|---|---|
| B+ tree (tlx) | 8,640,000 | 21 | 158 |
| ALEX (learned) | 8,640,000 | 105 | 190 |

## Throughput per phase (operations per second)

| Phase | B+ tree (tlx) | ALEX (learned) | ALEX (learned) / B+ tree |
|---|---|---|---|
| P1 stable | 1.89 M (1.77-1.94) | 2.14 M (1.91-2.20) | 1.13x |
| P2 ingestion spike | 2.48 M (2.39-2.56) | 2.20 M (2.10-2.25) | 0.89x |
| P3 localised incident | 2.64 M (2.34-2.70) | 2.76 M (2.33-2.82) | 1.04x |
| P4 investigation | 0.46 M (0.45-0.49) | 1.53 M (1.47-1.77) | 3.30x |
| P5 recovery | 1.80 M (1.66-1.91) | 3.31 M (2.33-3.45) | 1.84x |
| P6 combined shift | 7.12 M (7.01-7.17) | 3.81 M (3.55-3.83) | 0.54x |

## Lookup latency (ns)

| Phase | Index | p50 | p95 | p99 | p99.9 | max | mean | time in slowest 1 % |
|---|---|---|---|---|---|---|---|---|
| P1 stable | B+ tree (tlx) | 461 | 772 | 1042 | 2996 | 169 µs | 501 | 5 % |
| P1 stable | ALEX (learned) | 230 | 471 | 731 | 1523 | 120 µs | 267 | 6 % |
| P2 ingestion spike | B+ tree (tlx) | 521 | 871 | 1203 | 3497 | 462 µs | 566 | 6 % |
| P2 ingestion spike | ALEX (learned) | 251 | 561 | 892 | 1793 | 311 µs | 310 | 6 % |
| P3 localised incident | B+ tree (tlx) | 511 | 872 | 1192 | 3858 | 190 µs | 563 | 6 % |
| P3 localised incident | ALEX (learned) | 231 | 571 | 952 | 2084 | 374 µs | 292 | 7 % |
| P4 investigation | B+ tree (tlx) | 320 | 701 | 932 | 2154 | 311 µs | 362 | 6 % |
| P4 investigation | ALEX (learned) | 110 | 331 | 591 | 1263 | 400 µs | 156 | 11 % |
| P5 recovery | B+ tree (tlx) | 481 | 822 | 1102 | 3186 | 393 µs | 532 | 5 % |
| P5 recovery | ALEX (learned) | 230 | 481 | 761 | 1523 | 535 µs | 266 | 6 % |
| P6 combined shift | B+ tree (tlx) | 80 | 110 | 140 | 251 | 68 µs | 86 | 4 % |
| P6 combined shift | ALEX (learned) | 50 | 101 | 121 | 300 | 69 µs | 62 | 5 % |

## Insert latency (ns)

| Phase | Index | p50 | p95 | p99 | p99.9 | max | mean | time in slowest 1 % |
|---|---|---|---|---|---|---|---|---|
| P1 stable | B+ tree (tlx) | 291 | 681 | 3096 | 9168 | 155 µs | 395 | 15 % |
| P1 stable | ALEX (learned) | 250 | 851 | 1843 | 179181 | 26445 µs | 1877 | 83 % |
| P2 ingestion spike | B+ tree (tlx) | 181 | 301 | 2585 | 6522 | 648 µs | 242 | 19 % |
| P2 ingestion spike | ALEX (learned) | 160 | 411 | 782 | 13737 | 3295 µs | 495 | 62 % |
| P3 localised incident | B+ tree (tlx) | 101 | 170 | 2495 | 6352 | 177 µs | 151 | 27 % |
| P3 localised incident | ALEX (learned) | 70 | 121 | 240 | 3186 | 26646 µs | 386 | 80 % |
| P4 investigation | B+ tree (tlx) | 932 | 1614 | 6453 | 24457 | 210 µs | 1159 | 14 % |
| P4 investigation | ALEX (learned) | 862 | 1644 | 2975 | 22484 | 1846 µs | 1081 | 18 % |
| P5 recovery | B+ tree (tlx) | 380 | 761 | 4148 | 12535 | 176 µs | 474 | 16 % |
| P5 recovery | ALEX (learned) | 210 | 471 | 832 | 8206 | 130 µs | 266 | 15 % |
| P6 combined shift | B+ tree (tlx) | 91 | 131 | 2034 | 6162 | 149 µs | 151 | 36 % |
| P6 combined shift | ALEX (learned) | 70 | 110 | 170 | 2615 | 20884 µs | 417 | 83 % |

## Range latency (ns)

| Phase | Index | p50 | p95 | p99 | p99.9 | max | mean | time in slowest 1 % |
|---|---|---|---|---|---|---|---|---|
| P1 stable | B+ tree (tlx) | 511 | 832 | 1132 | 3687 | 169 µs | 561 | 6 % |
| P1 stable | ALEX (learned) | 331 | 631 | 932 | 2335 | 148 µs | 380 | 6 % |
| P2 ingestion spike | B+ tree (tlx) | 571 | 922 | 1313 | 4378 | 113 µs | 627 | 6 % |
| P2 ingestion spike | ALEX (learned) | 360 | 682 | 1102 | 2464 | 69 µs | 405 | 6 % |
| P4 investigation | B+ tree (tlx) | 3607 | 7675 | 10320 | 41852 | 745 µs | 3973 | 6 % |
| P4 investigation | ALEX (learned) | 791 | 1744 | 2645 | 16272 | 358 µs | 1034 | 7 % |
| P5 recovery | B+ tree (tlx) | 541 | 882 | 1192 | 3938 | 167 µs | 593 | 5 % |
| P5 recovery | ALEX (learned) | 351 | 641 | 962 | 2145 | 108 µs | 398 | 6 % |

## Memory after each phase (MB, process RSS above baseline)

| Phase | B+ tree (tlx) | ALEX (learned) |
|---|---|---|
| P1 stable | 170 | 262 |
| P2 ingestion spike | 197 | 302 |
| P3 localised incident | 216 | 410 |
| P4 investigation | 221 | 413 |
| P5 recovery | 225 | 414 |
| P6 combined shift | 244 | 510 |

## ALEX (learned): ALEX structure after each phase (repetition 1)

| Phase | Data nodes | Model nodes | Expand+scale | Expand+retrain | Downward splits | Sideways splits |
|---|---|---|---|---|---|---|
| load | 1,001 | 1 | 0 | 0 | 0 | 0 |
| P1 stable | 2,016 | 23 | 0 | 3 | 22 | 992 |
| P2 ingestion spike | 3,621 | 80 | 206 | 107 | 79 | 2,540 |
| P3 localised incident | 3,870 | 87 | 619 | 332 | 86 | 2,782 |
| P4 investigation | 3,913 | 89 | 630 | 338 | 88 | 2,823 |
| P5 recovery | 3,917 | 89 | 701 | 373 | 88 | 2,827 |
| P6 combined shift | 4,191 | 100 | 1,008 | 576 | 99 | 3,090 |

Timer overhead (median of back-to-back clock reads): 20 ns; it is included in every latency.
