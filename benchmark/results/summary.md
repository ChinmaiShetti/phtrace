# Index benchmark results

Environment:

- date: 2026-11-08T13:18:17Z
- compiler: g++ (GCC) 14.4.0
- cpu: AMD Ryzen 5 7535HS with Radeon Graphics
- cores: 12
- memory: 7533.2 MB
- kernel: 6.6.87.2-microsoft-standard-WSL2
- alex_commit: 4370da6aa8b509fdc9b0d2c49faa0624b0078589
- tlx_commit: 2dd63ab839909f0b43cd02108a1869c4670b2c8e
- reps: 5
- indexes: btree alex alexhb alexhb-nomig
- hb_args: defaults W=4096 H=64 M=4

Medians over 5 repetitions (min-max in brackets). Latencies in nanoseconds per operation.

Replay check: identical results for every index and repetition.

## Bulk load

| Index | Keys | Load time per key (ns) | Index memory (MB) |
|---|---|---|---|
| B+ tree (tlx) | 8,640,000 | 17 | 158 |
| ALEX (learned) | 8,640,000 | 104 | 190 |
| ALEX-HB (hot buffer) | 8,640,000 | 107 | 190 |
| ALEX-HB, no migration | 8,640,000 | 97 | 190 |

## Throughput per phase (operations per second)

| Phase | B+ tree (tlx) | ALEX (learned) | ALEX-HB (hot buffer) | ALEX-HB, no migration | ALEX (learned) / B+ tree | ALEX-HB (hot buffer) / B+ tree | ALEX-HB, no migration / B+ tree |
|---|---|---|---|---|---|---|---|
| P1 stable | 1.53 M (1.47-1.95) | 2.05 M (1.58-2.09) | 2.02 M (2.01-2.19) | 2.04 M (1.87-2.12) | 1.34x | 1.32x | 1.34x |
| P2 ingestion spike | 2.38 M (1.65-2.53) | 2.05 M (1.69-2.11) | 2.13 M (1.77-2.16) | 2.08 M (1.95-2.14) | 0.86x | 0.90x | 0.88x |
| P3 localised incident | 2.59 M (2.33-2.64) | 2.66 M (2.48-2.73) | 4.35 M (4.02-4.57) | 4.37 M (4.30-4.59) | 1.03x | 1.68x | 1.68x |
| P4 investigation | 0.46 M (0.42-0.49) | 1.79 M (1.72-1.84) | 0.89 M (0.84-0.91) | 0.42 M (0.38-0.43) | 3.85x | 1.91x | 0.91x |
| P5 recovery | 1.79 M (1.41-1.84) | 3.40 M (3.21-3.44) | 3.29 M (2.76-3.32) | 3.26 M (2.71-3.34) | 1.90x | 1.84x | 1.82x |
| P6 combined shift | 6.98 M (6.84-7.39) | 3.57 M (3.26-3.63) | 8.49 M (7.74-8.56) | 8.25 M (8.12-8.42) | 0.51x | 1.22x | 1.18x |

## Lookup latency (ns)

| Phase | Index | p50 | p95 | p99 | p99.9 | max | mean | time in slowest 1 % |
|---|---|---|---|---|---|---|---|---|
| P1 stable | B+ tree (tlx) | 521 | 892 | 1173 | 3256 | 204 µs | 613 | 6 % |
| P1 stable | ALEX (learned) | 231 | 511 | 782 | 1393 | 202 µs | 280 | 6 % |
| P1 stable | ALEX-HB (hot buffer) | 231 | 501 | 761 | 1382 | 250 µs | 279 | 6 % |
| P1 stable | ALEX-HB, no migration | 230 | 481 | 742 | 1373 | 186 µs | 271 | 6 % |
| P2 ingestion spike | B+ tree (tlx) | 552 | 922 | 1162 | 2265 | 163 µs | 598 | 4 % |
| P2 ingestion spike | ALEX (learned) | 270 | 642 | 992 | 1674 | 283 µs | 337 | 7 % |
| P2 ingestion spike | ALEX-HB (hot buffer) | 270 | 571 | 882 | 1553 | 249 µs | 316 | 6 % |
| P2 ingestion spike | ALEX-HB, no migration | 261 | 591 | 902 | 1523 | 105 µs | 315 | 6 % |
| P3 localised incident | B+ tree (tlx) | 521 | 872 | 1112 | 1944 | 231 µs | 562 | 5 % |
| P3 localised incident | ALEX (learned) | 231 | 581 | 942 | 1664 | 229 µs | 292 | 7 % |
| P3 localised incident | ALEX-HB (hot buffer) | 240 | 531 | 822 | 1483 | 163 µs | 288 | 6 % |
| P3 localised incident | ALEX-HB, no migration | 240 | 531 | 822 | 1433 | 240 µs | 286 | 6 % |
| P4 investigation | B+ tree (tlx) | 321 | 691 | 892 | 1634 | 581 µs | 356 | 6 % |
| P4 investigation | ALEX (learned) | 101 | 270 | 451 | 901 | 155 µs | 135 | 7 % |
| P4 investigation | ALEX-HB (hot buffer) | 140 | 861 | 1653 | 15711 | 18294 µs | 387 | 41 % |
| P4 investigation | ALEX-HB, no migration | 350 | 742 | 971 | 1644 | 150 µs | 385 | 6 % |
| P5 recovery | B+ tree (tlx) | 491 | 822 | 1042 | 1934 | 206 µs | 534 | 5 % |
| P5 recovery | ALEX (learned) | 221 | 471 | 731 | 1373 | 277 µs | 259 | 6 % |
| P5 recovery | ALEX-HB (hot buffer) | 221 | 471 | 732 | 1383 | 249 µs | 261 | 6 % |
| P5 recovery | ALEX-HB, no migration | 230 | 491 | 751 | 1413 | 536 µs | 265 | 6 % |
| P6 combined shift | B+ tree (tlx) | 80 | 110 | 150 | 260 | 139 µs | 85 | 5 % |
| P6 combined shift | ALEX (learned) | 50 | 101 | 120 | 271 | 44 µs | 62 | 5 % |
| P6 combined shift | ALEX-HB (hot buffer) | 80 | 100 | 140 | 230 | 127 µs | 82 | 4 % |
| P6 combined shift | ALEX-HB, no migration | 80 | 101 | 131 | 231 | 88 µs | 84 | 4 % |

## Insert latency (ns)

| Phase | Index | p50 | p95 | p99 | p99.9 | max | mean | time in slowest 1 % |
|---|---|---|---|---|---|---|---|---|
| P1 stable | B+ tree (tlx) | 390 | 872 | 3436 | 18085 | 126 µs | 532 | 18 % |
| P1 stable | ALEX (learned) | 280 | 982 | 1814 | 217152 | 27190 µs | 1974 | 82 % |
| P1 stable | ALEX-HB (hot buffer) | 321 | 1002 | 1834 | 175362 | 26001 µs | 1941 | 80 % |
| P1 stable | ALEX-HB, no migration | 301 | 982 | 1814 | 216460 | 26322 µs | 2015 | 81 % |
| P2 ingestion spike | B+ tree (tlx) | 190 | 401 | 2645 | 7635 | 349 µs | 266 | 20 % |
| P2 ingestion spike | ALEX (learned) | 160 | 581 | 1142 | 19398 | 3518 µs | 534 | 62 % |
| P2 ingestion spike | ALEX-HB (hot buffer) | 181 | 501 | 911 | 13907 | 2834 µs | 518 | 58 % |
| P2 ingestion spike | ALEX-HB, no migration | 181 | 531 | 962 | 14248 | 3007 µs | 533 | 59 % |
| P3 localised incident | B+ tree (tlx) | 101 | 170 | 2595 | 7485 | 143 µs | 170 | 36 % |
| P3 localised incident | ALEX (learned) | 71 | 130 | 241 | 3466 | 37520 µs | 415 | 81 % |
| P3 localised incident | ALEX-HB (hot buffer) | 110 | 210 | 330 | 581 | 101 µs | 126 | 5 % |
| P3 localised incident | ALEX-HB, no migration | 110 | 211 | 331 | 581 | 123 µs | 126 | 6 % |
| P4 investigation | B+ tree (tlx) | 941 | 1543 | 5982 | 26703 | 441 µs | 1152 | 15 % |
| P4 investigation | ALEX (learned) | 832 | 1413 | 2014 | 18587 | 1772 µs | 962 | 16 % |
| P4 investigation | ALEX-HB (hot buffer) | 1022 | 2034 | 5782 | 23036 | 1806 µs | 1318 | 18 % |
| P4 investigation | ALEX-HB, no migration | 1182 | 2034 | 2925 | 21923 | 2388 µs | 1452 | 16 % |
| P5 recovery | B+ tree (tlx) | 381 | 771 | 4138 | 14309 | 102 µs | 499 | 17 % |
| P5 recovery | ALEX (learned) | 201 | 451 | 802 | 8076 | 97 µs | 259 | 15 % |
| P5 recovery | ALEX-HB (hot buffer) | 251 | 541 | 1052 | 12395 | 108 µs | 338 | 17 % |
| P5 recovery | ALEX-HB, no migration | 260 | 551 | 891 | 8097 | 124 µs | 320 | 13 % |
| P6 combined shift | B+ tree (tlx) | 91 | 131 | 2395 | 6874 | 137 µs | 153 | 37 % |
| P6 combined shift | ALEX (learned) | 70 | 110 | 160 | 2596 | 23435 µs | 454 | 84 % |
| P6 combined shift | ALEX-HB (hot buffer) | 100 | 150 | 230 | 541 | 72 µs | 109 | 5 % |
| P6 combined shift | ALEX-HB, no migration | 100 | 151 | 240 | 541 | 155 µs | 112 | 5 % |

## Range latency (ns)

| Phase | Index | p50 | p95 | p99 | p99.9 | max | mean | time in slowest 1 % |
|---|---|---|---|---|---|---|---|---|
| P1 stable | B+ tree (tlx) | 571 | 962 | 1272 | 3517 | 188 µs | 680 | 5 % |
| P1 stable | ALEX (learned) | 341 | 661 | 972 | 1703 | 128 µs | 390 | 6 % |
| P1 stable | ALEX-HB (hot buffer) | 341 | 652 | 922 | 1593 | 142 µs | 396 | 6 % |
| P1 stable | ALEX-HB, no migration | 340 | 632 | 902 | 1623 | 121 µs | 380 | 5 % |
| P2 ingestion spike | B+ tree (tlx) | 602 | 982 | 1242 | 2795 | 50 µs | 652 | 4 % |
| P2 ingestion spike | ALEX (learned) | 371 | 782 | 1172 | 2094 | 151 µs | 438 | 6 % |
| P2 ingestion spike | ALEX-HB (hot buffer) | 361 | 702 | 1002 | 1754 | 60 µs | 414 | 5 % |
| P2 ingestion spike | ALEX-HB, no migration | 361 | 721 | 1052 | 1734 | 53 µs | 417 | 5 % |
| P4 investigation | B+ tree (tlx) | 3717 | 7635 | 9569 | 29899 | 761 µs | 3976 | 5 % |
| P4 investigation | ALEX (learned) | 762 | 1333 | 1864 | 8828 | 501 µs | 877 | 5 % |
| P4 investigation | ALEX-HB (hot buffer) | 852 | 6443 | 9630 | 23737 | 22120 µs | 1782 | 21 % |
| P4 investigation | ALEX-HB, no migration | 4078 | 8257 | 10852 | 34808 | 733 µs | 4367 | 5 % |
| P5 recovery | B+ tree (tlx) | 541 | 881 | 1102 | 2324 | 122 µs | 589 | 5 % |
| P5 recovery | ALEX (learned) | 341 | 621 | 842 | 1643 | 112 µs | 383 | 5 % |
| P5 recovery | ALEX-HB (hot buffer) | 350 | 621 | 852 | 1674 | 118 µs | 388 | 5 % |
| P5 recovery | ALEX-HB, no migration | 351 | 641 | 862 | 1654 | 70 µs | 392 | 5 % |

## Memory after each phase (MB, process RSS above baseline)

| Phase | B+ tree (tlx) | ALEX (learned) | ALEX-HB (hot buffer) | ALEX-HB, no migration |
|---|---|---|---|---|
| P1 stable | 170 | 262 | 262 | 262 |
| P2 ingestion spike | 197 | 302 | 302 | 302 |
| P3 localised incident | 216 | 410 | 302 | 302 |
| P4 investigation | 221 | 413 | 408 | 307 |
| P5 recovery | 225 | 414 | 409 | 308 |
| P6 combined shift | 244 | 510 | 409 | 308 |

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

## ALEX-HB (hot buffer): ALEX structure after each phase (repetition 1)

| Phase | Data nodes | Model nodes | Expand+scale | Expand+retrain | Downward splits | Sideways splits |
|---|---|---|---|---|---|---|
| load | 1,001 | 1 | 0 | 0 | 0 | 0 |
| P1 stable | 2,016 | 23 | 0 | 3 | 22 | 992 |
| P2 ingestion spike | 3,621 | 80 | 206 | 107 | 79 | 2,540 |
| P3 localised incident | 3,621 | 80 | 206 | 109 | 79 | 2,540 |
| P4 investigation | 3,935 | 90 | 798 | 404 | 89 | 2,844 |
| P5 recovery | 3,939 | 90 | 889 | 445 | 89 | 2,848 |
| P6 combined shift | 3,939 | 90 | 889 | 445 | 89 | 2,848 |

## ALEX-HB, no migration: ALEX structure after each phase (repetition 1)

| Phase | Data nodes | Model nodes | Expand+scale | Expand+retrain | Downward splits | Sideways splits |
|---|---|---|---|---|---|---|
| load | 1,001 | 1 | 0 | 0 | 0 | 0 |
| P1 stable | 2,016 | 23 | 0 | 3 | 22 | 992 |
| P2 ingestion spike | 3,621 | 80 | 206 | 107 | 79 | 2,540 |
| P3 localised incident | 3,621 | 80 | 206 | 109 | 79 | 2,540 |
| P4 investigation | 3,664 | 82 | 217 | 115 | 81 | 2,581 |
| P5 recovery | 3,668 | 82 | 273 | 140 | 81 | 2,585 |
| P6 combined shift | 3,668 | 82 | 273 | 140 | 81 | 2,585 |

## ALEX-HB (hot buffer): hot buffer after each phase (repetition 1; W=4096, H=64, M=4)

| Phase | Hot sensors now | Keys in buffer | Max buffer so far | Inserts routed to buffer (total) | Keys migrated to ALEX (total) |
|---|---|---|---|---|---|
| P1 stable | 0 | 0 | 0 | 0 | 0 |
| P2 ingestion spike | 0 | 0 | 0 | 0 | 0 |
| P3 localised incident | 10 | 499,329 | 499,329 | 499,329 | 0 |
| P4 investigation | 0 | 0 | 499,358 | 499,358 | 499,358 |
| P5 recovery | 0 | 0 | 499,358 | 499,358 | 499,358 |
| P6 combined shift | 10 | 499,084 | 499,358 | 998,442 | 499,358 |

## ALEX-HB, no migration: hot buffer after each phase (repetition 1; W=4096, H=64, M=0)

| Phase | Hot sensors now | Keys in buffer | Max buffer so far | Inserts routed to buffer (total) | Keys migrated to ALEX (total) |
|---|---|---|---|---|---|
| P1 stable | 0 | 0 | 0 | 0 | 0 |
| P2 ingestion spike | 0 | 0 | 0 | 0 | 0 |
| P3 localised incident | 10 | 499,329 | 499,329 | 499,329 | 0 |
| P4 investigation | 0 | 499,358 | 499,358 | 499,358 | 0 |
| P5 recovery | 0 | 499,358 | 499,358 | 499,358 | 0 |
| P6 combined shift | 10 | 998,442 | 998,442 | 998,442 | 0 |

Timer overhead (median of back-to-back clock reads): 20 ns; it is included in every latency.
