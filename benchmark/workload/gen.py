"""Synthetic sensor-reading workload for the index benchmark.

Keys model the PharmaTrace lookup key (sensor_id, recorded_at) packed into one integer:
    key = sensor_id << 40 | epoch_seconds        (unique, and ordered by sensor then time)

Output (all little-endian, read by src/bench.cpp):
    bulk.bin      uint64 count, then count sorted uint64 keys (payload = position)
    phases.bin    uint32 phase count, then per phase: uint32 name length, name bytes, uint64 op count, ops
                  op = packed {uint8 kind (0 lookup, 1 insert, 2 range), uint64 key, uint32 arg}
                  arg = range length in seconds for range scans, otherwise 0

Every index replays exactly these files, so all configurations see the same operations.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

OP = np.dtype([("kind", "u1"), ("key", "<u8"), ("arg", "<u4")])   # packed, 13 bytes
LOOKUP, INSERT, RANGE = 0, 1, 2
T0 = 1_767_225_600          # 2026-01-01T00:00:00Z
STEP = 300                  # normal reading interval (5 minutes)


def key(sensor, ts):
    return (np.asarray(sensor, dtype=np.uint64) << np.uint64(40)) | np.asarray(ts, dtype=np.uint64)


class Workload:
    def __init__(self, sensors: int, days: int, seed: int):
        self.rng = np.random.default_rng(seed)
        self.S = sensors
        self.N = days * 86400 // STEP                       # bulk readings per sensor
        self.ids = np.arange(1, sensors + 1, dtype=np.uint64)
        self.last_ts = np.full(sensors, T0 + (self.N - 1) * STEP, dtype=np.int64)
        self.recent: list[np.ndarray] = []                  # keys inserted by the incident phases

    def bulk(self) -> np.ndarray:
        ts = T0 + STEP * np.arange(self.N, dtype=np.uint64)
        return (self.ids[:, None] << np.uint64(40) | ts[None, :]).ravel()   # sensor-major => sorted

    # ------------------------------------------------------------------ building blocks
    def inserts(self, sensors: np.ndarray, step: int) -> np.ndarray:
        """Next reading of each listed sensor, in the given order (per-sensor time strictly increases)."""
        order = np.argsort(sensors, kind="stable")
        sorted_s = sensors[order]
        first = np.searchsorted(sorted_s, sorted_s, side="left")
        nth = np.empty_like(order)
        nth[order] = np.arange(len(sensors)) - first + 1
        ts = self.last_ts[sensors] + nth * step
        np.maximum.at(self.last_ts, sensors, ts)
        return key(self.ids[sensors], ts)

    def bulk_lookups(self, n: int) -> np.ndarray:
        s = self.rng.integers(0, self.S, n)
        i = self.rng.integers(0, self.N, n)
        return key(self.ids[s], T0 + STEP * i)

    def zipf_pick(self, pool: np.ndarray, n: int, a: float = 0.99) -> np.ndarray:
        """Zipf-popular picks from pool: a random popularity order, weight 1/rank^a."""
        weights = 1.0 / np.arange(1, len(pool) + 1) ** a
        ranks = self.rng.choice(len(pool), n, p=weights / weights.sum())
        return pool[self.rng.permutation(len(pool))][ranks]

    def phase(self, n, p_insert, p_lookup, p_range, insert_sensors, insert_step, lookup_keys, range_starts, range_len):
        kinds = self.rng.choice(3, n, p=[p_lookup, p_insert, p_range]).astype(np.uint8)
        kinds = np.where(kinds == 0, LOOKUP, np.where(kinds == 1, INSERT, RANGE)).astype(np.uint8)
        ops = np.zeros(n, dtype=OP)
        ops["kind"] = kinds
        ins = kinds == INSERT
        ops["key"][ins] = self.inserts(insert_sensors(int(ins.sum())), insert_step)
        look = kinds == LOOKUP
        ops["key"][look] = lookup_keys(int(look.sum()), ops, look)
        rng_ = kinds == RANGE
        ops["key"][rng_] = range_starts(int(rng_.sum()), ops, rng_)
        ops["arg"][rng_] = range_len
        return ops, ops["key"][ins]


def build(sensors: int, days: int, ops_per_phase: int, seed: int, out: Path) -> dict:
    w = Workload(sensors, days, seed)
    rng = w.rng
    out.mkdir(parents=True, exist_ok=True)

    bulk = w.bulk()
    with open(out / "bulk.bin", "wb") as f:
        np.array([len(bulk)], dtype="<u8").tofile(f)
        bulk.astype("<u8").tofile(f)

    n = ops_per_phase
    hot = rng.choice(sensors, max(1, sensors // 100), replace=False)          # 1 % of sensors fail
    hot2 = rng.choice(np.setdiff1d(np.arange(sensors), hot), len(hot), replace=False)
    uniform = lambda k: rng.integers(0, sensors, k)                            # noqa: E731
    bulk_points = lambda k, ops, m: w.bulk_lookups(k)                          # noqa: E731
    phases = []

    # P1 stable: steady ingestion across all sensors, uniform queries
    ops, _ = w.phase(n, 0.10, 0.80, 0.10, uniform, STEP, bulk_points, bulk_points, 3600)
    phases.append(("P1 stable", ops))
    # P2 ingestion spike: six times the insert share
    ops, _ = w.phase(n, 0.60, 0.35, 0.05, uniform, STEP, bulk_points, bulk_points, 3600)
    phases.append(("P2 ingestion spike", ops))
    # P3 localised incident: failing sensors report every second -> dense keys in narrow sub-ranges
    ops, incident_keys = w.phase(n, 0.50, 0.50, 0.0, lambda k: rng.choice(hot, k), 1,
                                 bulk_points, bulk_points, 0)
    phases.append(("P3 localised incident", ops))
    # P4 investigation: repeated queries on the incident window (Zipf), half of them 10-minute range scans
    hot_points = lambda k, ops, m: w.zipf_pick(incident_keys, k)               # noqa: E731
    ops, _ = w.phase(n, 0.05, 0.475, 0.475, uniform, STEP, hot_points, hot_points, 600)
    phases.append(("P4 investigation", ops))
    # P5 recovery: back to the stable mix
    ops, _ = w.phase(n, 0.10, 0.80, 0.10, uniform, STEP, bulk_points, bulk_points, 3600)
    phases.append(("P5 recovery", ops))

    # P6 combined: a second failure; investigators query the newest readings of the newly hot sensors
    def recent_hot(k, ops, mask):
        inserted_before = np.cumsum(ops["kind"] == INSERT)[mask] - 1          # inserts seen before each query
        keys_so_far = ops["key"][ops["kind"] == INSERT]
        back = rng.geometric(0.01, k)                                         # mostly the last few hundred
        idx = inserted_before - back
        picked = np.where(idx >= 0, keys_so_far[np.clip(idx, 0, None)], w.bulk_lookups(k))
        return picked

    kinds = rng.choice([LOOKUP, INSERT], n, p=[0.5, 0.5]).astype(np.uint8)
    ops = np.zeros(n, dtype=OP)
    ops["kind"] = kinds
    ins = kinds == INSERT
    ops["key"][ins] = w.inserts(rng.choice(hot2, int(ins.sum())), 1)
    look = kinds == LOOKUP
    ops["key"][look] = recent_hot(int(look.sum()), ops, look)
    phases.append(("P6 combined shift", ops))

    with open(out / "phases.bin", "wb") as f:
        np.array([len(phases)], dtype="<u4").tofile(f)
        for name, ops in phases:
            b = name.encode()
            np.array([len(b)], dtype="<u4").tofile(f)
            f.write(b)
            np.array([len(ops)], dtype="<u8").tofile(f)
            ops.tofile(f)

    meta = {
        "sensors": sensors, "days": days, "bulk_keys": int(len(bulk)), "ops_per_phase": n, "seed": seed,
        "hot_sensors": sorted(int(x) + 1 for x in hot), "second_hot_sensors": sorted(int(x) + 1 for x in hot2),
        "phases": [{"name": name, "lookups": int((o["kind"] == LOOKUP).sum()), "inserts": int((o["kind"] == INSERT).sum()),
                    "ranges": int((o["kind"] == RANGE).sum())} for name, o in phases],
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (out / "bulk.bin", out / "phases.bin")},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensors", type=int, default=1000)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--ops", type=int, default=1_000_000, help="operations per phase")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "traces")
    a = ap.parse_args()
    m = build(a.sensors, a.days, a.ops, a.seed, a.out)
    print(json.dumps({k: m[k] for k in ("bulk_keys", "ops_per_phase", "phases")}, indent=1))
