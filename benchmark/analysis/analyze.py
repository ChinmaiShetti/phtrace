"""Summarise results/results.csv into tables (summary.md) and figures (figures/*.png).

Medians across repetitions are reported, with the min-max range as the spread.
Usage: py -I analysis/analyze.py [results_dir]
"""

import csv
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results"
FIG = RESULTS / "figures"
ORDER = ("btree", "alex", "alexhb", "alexhb-nomig")
COLORS = {"btree": "#2F6DB5", "alex": "#D9822B", "alexhb": "#2E9E5B", "alexhb-nomig": "#8E5BB5"}
NAMES = {"btree": "B+ tree (tlx)", "alex": "ALEX (learned)", "alexhb": "ALEX-HB (hot buffer)",
         "alexhb-nomig": "ALEX-HB, no migration"}


def load():
    rows = list(csv.DictReader(open(RESULTS / "results.csv", newline="")))
    for r in rows:
        for k in ("count", "p50_ns", "p95_ns", "p99_ns", "found", "checksum"):
            r[k] = int(float(r[k]))
        for k in ("mean_ns", "phase_ops_per_s", "rss_index_mb", "p999_ns", "max_ns", "tail_time_share"):
            r[k] = float(r[k])
    return rows


def stats_dict(s: str) -> dict:
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", s or "")}


def main():
    rows = load()
    phases = list(dict.fromkeys(r["phase"] for r in rows if r["phase"] != "load"))
    indexes = [i for i in ORDER if any(r["index"] == i for r in rows)]
    others = [i for i in indexes if i != "btree"]
    by = defaultdict(list)
    for r in rows:
        by[(r["index"], r["phase"], r["op"])].append(r)

    # -- replay check: every repetition of every index must see the same results
    check = defaultdict(set)
    for r in rows:
        if r["phase"] != "load":
            check[(r["phase"], r["op"])].add((r["found"], r["checksum"]))
    mismatches = [k for k, v in check.items() if len(v) != 1]

    def med(idx, phase, op, field):
        v = [r[field] for r in by[(idx, phase, op)]]
        return (st.median(v), min(v), max(v)) if v else (None, None, None)

    def phase_tput(idx, phase):
        # one throughput per (rep, phase); every op row of that rep repeats it
        reps = {r["rep"]: r["phase_ops_per_s"] for op in ("lookup", "insert", "range") for r in by[(idx, phase, op)]}
        v = list(reps.values())
        return st.median(v), min(v), max(v)

    lines = ["# Index benchmark results", ""]
    env = (RESULTS / "environment.txt").read_text().strip().splitlines() if (RESULTS / "environment.txt").exists() else []
    lines += ["Environment:", ""] + [f"- {e}" for e in env] + [""]
    reps = len({r["rep"] for r in rows})
    lines += [f"Medians over {reps} repetitions (min-max in brackets). Latencies in nanoseconds per operation.", ""]
    lines += ["Replay check: " + ("identical results for every index and repetition."
                                  if not mismatches else f"MISMATCH in {mismatches}"), ""]

    lines += ["## Bulk load", "", "| Index | Keys | Load time per key (ns) | Index memory (MB) |", "|---|---|---|---|"]
    for i in indexes:
        r = by[(i, "load", "bulk_load")]
        lines.append(f"| {NAMES[i]} | {r[0]['count']:,} | {st.median(x['mean_ns'] for x in r):.0f} | "
                     f"{st.median(x['rss_index_mb'] for x in r):.0f} |")

    lines += ["", "## Throughput per phase (operations per second)", "",
              "| Phase | " + " | ".join(NAMES[i] for i in indexes) + " | "
              + " | ".join(f"{NAMES[i]} / B+ tree" for i in others) + " |",
              "|---" * (len(indexes) + len(others) + 1) + "|"]
    for p in phases:
        cells, vals = [], {}
        for i in indexes:
            m, lo, hi = phase_tput(i, p)
            vals[i] = m
            cells.append(f"{m / 1e6:.2f} M ({lo / 1e6:.2f}-{hi / 1e6:.2f})")
        ratios = [f"{vals[i] / vals['btree']:.2f}x" for i in others] if "btree" in vals else []
        lines.append(f"| {p} | " + " | ".join(cells + ratios) + " |")

    for op in ("lookup", "insert", "range"):
        present = [p for p in phases if by[("btree", p, op)]]
        if not present:
            continue
        lines += ["", f"## {op.capitalize()} latency (ns)", "",
                  "| Phase | Index | p50 | p95 | p99 | p99.9 | max | mean | time in slowest 1 % |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for p in present:
            for i in indexes:
                p50, p95, p99 = (med(i, p, op, f)[0] for f in ("p50_ns", "p95_ns", "p99_ns"))
                mean, p999, mx, tail = (med(i, p, op, f)[0] for f in ("mean_ns", "p999_ns", "max_ns", "tail_time_share"))
                lines.append(f"| {p} | {NAMES[i]} | {p50:.0f} | {p95:.0f} | {p99:.0f} | {p999:.0f} | {mx / 1000:.0f} µs | "
                             f"{mean:.0f} | {tail * 100:.0f} % |")

    lines += ["", "## Memory after each phase (MB, process RSS above baseline)", "",
              "| Phase | " + " | ".join(NAMES[i] for i in indexes) + " |", "|---" * (len(indexes) + 1) + "|"]
    for p in phases:
        lines.append(f"| {p} | " + " | ".join(f"{med(i, p, 'lookup', 'rss_index_mb')[0]:.0f}" for i in indexes) + " |")

    first_rep = min(r["rep"] for r in rows)

    def stats_at(idx, p):
        op = "bulk_load" if p == "load" else "lookup"
        found = [x for x in by[(idx, p, op)] if x["rep"] == first_rep]
        return stats_dict(found[0]["stats"]) if found else {}

    for idx in [i for i in indexes if i.startswith("alex")]:
        lines += ["", f"## {NAMES[idx]}: ALEX structure after each phase (repetition {first_rep})", "",
                  "| Phase | Data nodes | Model nodes | Expand+scale | Expand+retrain | Downward splits | Sideways splits |",
                  "|---|---|---|---|---|---|---|"]
        for p in ["load"] + phases:
            s = stats_at(idx, p)
            lines.append(f"| {p} | {s.get('data_nodes', 0):,} | {s.get('model_nodes', 0):,} | "
                         f"{s.get('expand_and_scales', 0):,} | {s.get('expand_and_retrains', 0):,} | "
                         f"{s.get('downward_splits', 0):,} | {s.get('sideways_splits', 0):,} |")

    for idx in [i for i in indexes if i.startswith("alexhb")]:
        s0 = stats_at(idx, phases[0])
        lines += ["", f"## {NAMES[idx]}: hot buffer after each phase (repetition {first_rep}; "
                  f"W={s0.get('W')}, H={s0.get('H')}, M={s0.get('M')})", "",
                  "| Phase | Hot sensors now | Keys in buffer | Max buffer so far | Inserts routed to buffer (total) | "
                  "Keys migrated to ALEX (total) |", "|---|---|---|---|---|---|"]
        for p in phases:
            s = stats_at(idx, p)
            lines.append(f"| {p} | {s.get('hot_now', 0)} | {s.get('buffer_keys', 0):,} | {s.get('max_buffer', 0):,} | "
                         f"{s.get('routed', 0):,} | {s.get('migrated', 0):,} |")

    timer = st.median(int(r["timer_overhead_ns"]) for r in rows)
    lines += ["", f"Timer overhead (median of back-to-back clock reads): {timer:.0f} ns; it is included in every latency."]
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ figures
    FIG.mkdir(exist_ok=True)
    short = [p.split(" ", 1)[0] + "\n" + p.split(" ", 1)[1] for p in phases]
    x = range(len(phases))
    w = 0.8 / len(indexes)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    for k, i in enumerate(indexes):
        t = [phase_tput(i, p) for p in phases]
        m = [v[0] / 1e6 for v in t]
        err = [[(v[0] - v[1]) / 1e6 for v in t], [(v[2] - v[0]) / 1e6 for v in t]]
        ax.bar([xi + (k - (len(indexes) - 1) / 2) * w for xi in x], m, w, yerr=err, capsize=3, color=COLORS[i],
               label=NAMES[i])
    ax.set_xticks(list(x), short, fontsize=9)
    ax.set_ylabel("Million operations / second")
    ax.set_title("Throughput per workload phase (median of repetitions, min-max whiskers)", fontsize=11)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "throughput.png", dpi=160)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
    panels = [("lookup", ("p50_ns", "p99_ns"), ("p50", "p99"), "Lookup latency: typical and p99 (ns, log scale)"),
              ("insert", ("p999_ns", "max_ns"), ("p99.9", "worst"), "Insert tail: p99.9 and worst pause (ns, log scale)")]
    for ax, (op, fields, names, title) in zip(axes, panels, strict=True):
        present = [p for p in phases if by[("btree", p, op)]]
        for i in indexes:
            ax.plot(range(len(present)), [med(i, p, op, fields[1])[0] for p in present], "-o", color=COLORS[i],
                    label=f"{NAMES[i]} {names[1]}")
            ax.plot(range(len(present)), [med(i, p, op, fields[0])[0] for p in present], "--", color=COLORS[i],
                    alpha=0.6, label=f"{NAMES[i]} {names[0]}")
        ax.set_xticks(range(len(present)), [p.split(" ", 1)[0] for p in present])
        ax.set_yscale("log")
        ax.set_title(title, fontsize=11)
        ax.grid(alpha=0.3, which="both")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "latency.png", dpi=160)

    fig, ax = plt.subplots(figsize=(7, 3.8))
    for i in indexes:
        ax.plot(["load"] + [p.split(" ", 1)[0] for p in phases],
                [med(i, "load", "bulk_load", "rss_index_mb")[0]] + [med(i, p, "lookup", "rss_index_mb")[0] for p in phases],
                "-o", color=COLORS[i], label=NAMES[i])
    ax.set_ylabel("MB above baseline")
    ax.set_title("Index memory after each phase", fontsize=11)
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "memory.png", dpi=160)
    print((RESULTS / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
