# Innovative Experiment, Phase 4: hot-range buffer for ALEX ("ALEX-HB")

Status: **IN PROGRESS.** See the progress log at the bottom. Update it after every step, so the next agent knows exactly where things stand.

## 1. Why

The baseline study (`docs/benchmark-report.md`) found the following:
- ALEX reads 2–4.6× faster than a B+ tree.
- ALEX's insert cost is concentrated in rare, synchronous reorganisations (node expansion and retraining). In the incident phases, its slowest 1 % of inserts take 80–83 % of all insert time, with single pauses up to about 27 ms. In the combined-shift phase (P6), its throughput drops to 0.54× the B+ tree's.

The pauses coincide with **sudden insert hot spots**: a few failing sensors report every second, appending densely to a few narrow key ranges.

## 2. Idea (hypothesis, to be measured)

Absorb hot-spot inserts in a small B+ tree in front of ALEX, and move them into ALEX later, a few keys at a time, once the hot spot has cooled.

- **Detect hot sensors.** Keep a sliding window of the last W inserts and count inserts per sensor (`sensor = key >> 40`). A sensor becomes hot when its count reaches H. It stops being hot when the count falls below H/2 (hysteresis).
- **Route inserts.**
  - An insert for a hot sensor goes into the buffer (a tlx `btree_map`, whose appends are cheap with bounded cost).
  - Every other insert goes straight into ALEX.
- **Lookups.** If the key's sensor has buffered keys, check the buffer first, then ALEX. Each key lives in exactly one structure.
- **Range scans.** Scan both ALEX and the buffer over the range and combine the results. The key sets are disjoint, so counts and sums simply add.
- **Deferred, incremental migration.** While no sensor is hot and the buffer is not empty, each operation moves up to M keys from the buffer into ALEX. The reorganisation work therefore leaves the burst and is spread over quieter phases.
- **Ablation.** A "never migrate" variant shows the pure effect of buffering, and the cost of a growing buffer.

**Prior art, so no novelty claim.** Delta buffers in front of learned indexes appear in earlier designs, for example XIndex and FINEdex, and in the "buffer + merge" approach of LSM trees. The contribution here is applying a hot-range trigger and deferred migration to incident-driven cold-chain workloads, and measuring the result. Any claim must cite the prior designs once the literature check is done (still a TODO).

## 3. Expected trade-offs (state them in the report whatever happens)

- **Should help:** insert tail latency and throughput in P3 (localised incident) and P6 (combined shift).
- **Should not help:** P1 and P2, where inserts are spread uniformly and no sensor becomes hot.
- **Costs:**
  - lookups of buffered sensors pay an extra buffer probe;
  - range scans touch two structures;
  - migration moves ALEX's reorganisation work into P4 and P5, which may raise their insert or lookup tails;
  - the buffer uses extra memory.
- **Correctness check:** every configuration must produce identical found counts and checksums. The harness already verifies this.

## 4. Implementation plan

| Step | What | Where |
|---|---|---|
| 1 | Add the `HotBufferAlex` adapter (index name `alexhb`), plus a `alexhb-nomig` ablation | `benchmark/src/bench.cpp` |
| 2 | Parameters W, H, M as CLI flags with defaults (W = 4096, H = 64, M = 4), recorded in the CSV `stats` column | `bench.cpp` |
| 3 | Make the index list configurable (`INDEXES` env, default `btree alex alexhb alexhb-nomig`) and rotate the run order | `benchmark/run_all.sh` |
| 4 | Smoke test on a small trace: same checksums for every index, no crash | Docker |
| 5 | Full run: 4 configurations × 5 repetitions on the standard traces | Docker, about 20 min |
| 6 | Generalise the analysis to N indexes, with ratios against the B+ tree and ALEX | `benchmark/analysis/analyze.py` |
| 7 | Write up the results honestly, including where it loses | `docs/benchmark-report.md` (new section) and the mid-term or final report |
| 8 | Update HANDOFF.md §10 and §11 | `HANDOFF.md` |

**Commands** (from HANDOFF.md §10):
```
py -I benchmark/workload/gen.py                         # traces are gitignored; regenerate if benchmark/traces/ is missing
docker build -t pharmatrace-bench benchmark
MSYS_NO_PATHCONV=1 docker run --rm -e REPS=5 -v "D:/DBMSEL/benchmark/traces:/traces" -v "D:/DBMSEL/benchmark/results:/results" pharmatrace-bench
py -I benchmark/analysis/analyze.py
```
Docker Desktop must be running (`"/c/Program Files/Docker/Docker/Docker Desktop.exe" & disown`). Keep the machine otherwise idle during timed runs.

**Preserve the baseline results.** Before step 5, copy `benchmark/results/` to `benchmark/results_baseline/`, so the two-index results cited in the existing reports stay reproducible.

## 5. Progress log (newest last)

| When | Step | Status / notes |
|---|---|---|
| 2026-11-08 | Design written (this file) | Done |
| 2026-11-08 | Step 1–2: `HotBufferAlex<Migrate>` adapter in `bench.cpp` (`alexhb`, `alexhb-nomig`); CLI `--hb-window/--hb-hot/--hb-migrate`; stats column records buffer size, max buffer, routed, migrated, hot sensors, W/H/M | Done (not yet compiled) |
| 2026-11-08 | Step 3: `run_all.sh` takes `INDEXES` (default 4 configs) and `HB_ARGS`, rotates order each rep | Done |
| 2026-11-08 | Step 6: `analyze.py` generalised to N indexes (ratios vs B+ tree for each, ALEX structure per ALEX variant, hot-buffer table) | Done; still produces the baseline summary correctly |
| 2026-11-08 | Step 4: building image | In progress: Docker's cache of `gcc:14` was lost, base image re-downloading slowly (~0.4 MB/s). If interrupted, just re-run `docker build -t pharmatrace-bench benchmark` (log: `benchmark/build.log`) |
| 2026-11-08 | Step 4: image built (base image re-downloaded once); smoke test on a small trace (500 sensors, 2 days, 50k ops/phase) | Done: identical found counts and checksums for all 4 configs in every phase. Early signal (small trace, 1 rep, noisy): P3 ALEX 0.54 M → ALEX-HB 4.59 M ops/s; P6 6.3 → 9.3 M; but P5 (recovery) 2.25 → 0.78 M because migration lands there; no-migration variant keeps P5 at 2.4 M |
| 2026-11-08 | Baseline results preserved | `benchmark/results/` copied to `benchmark/results_baseline/` (2-index run cited in existing reports) |
| 2026-11-08 | Step 5: full run, 4 configs × 5 reps | STARTED (output `benchmark/results/`, log `benchmark/results_run.log`). If it was interrupted, re-run the docker command from §4 |
| 2026-11-08 | Step 5: full run done (4 configs × 5 reps, `benchmark/results/`) | Done. Replay check identical. P3: ALEX-HB 4.35 M vs ALEX 2.66 M ops/s, insert max 0.10 ms vs 37.5 ms. P6: 8.49 M vs 3.57 M (beats B+ tree 1.22×), insert max 0.07 vs 23 ms. Memory end 409 vs 510 MB. COST: P4 throughput 0.89 M vs 1.79 M (migration of ~500k keys lands in the investigation phase; lookup max 18 ms). No-migration variant: P4 0.42 M (queries hit buffer). P1/P2/P5 unchanged |
| 2026-11-08 | Step 5b: sensitivity, M=1 (alexhb only, 3 reps, `benchmark/results_m1/`) | Done. P4 0.63 M ops/s, WORSE than M=4 (0.89 M): slower migration lengthens the overlap with investigation queries. P3 4.38 M, P6 8.25 M (unchanged) |
| 2026-11-08 | Step 7: write-up | Done: `docs/benchmark-report.md` §6 (design, results tables, where it loses, next steps). Baseline sections now link `benchmark/results_baseline/` |
| 2026-11-08 | Step 8: HANDOFF.md updated | Done |

## 6. Next agent: where to pick up

The first iteration is complete and measured. Optional follow-ups, in order of promise:
1. **Bulk migration.** When a sensor cools, insert its whole buffered range into ALEX in one step (ALEX has no range bulk-insert, so this needs either a modified ALEX or a rebuild of the affected subtree) and compare P4.
2. **Query-aware migration.** Track reads per buffered sensor and delay migrating sensors that are still being queried.
3. **Parameter sweep.** Run H in {32, 64, 128} and W in {2048, 4096, 8192}, with 3 repetitions each, using `INDEXES=alexhb HB_ARGS=...`.
4. **Literature check.** Look at XIndex, FINEdex and other buffered or LSM-style learned indexes before making any claim in the final report.
5. **Reports.** Copy §6 of the benchmark report into the draft and final reports (submissions 9 and 11), together with `benchmark/results/figures/throughput.png`.
