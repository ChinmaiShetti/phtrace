"""Figures for the final report: architecture, workflows, test results and project size.

Reads the real test outputs (evidence/test_evidence.json, evidence/pytest_junit.xml) and copies the ER, DFD
and benchmark figures, so everything in figures/ comes from the project itself.
Usage (from the repo root): py -I docs/final-report/make_figures.py
"""

import json
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
INK, ACCENT, GOOD, MUTED = "#1F2933", "#1C7ED6", "#2E9E5B", "#7B8794"
plt.rcParams.update({"font.family": "Arial", "font.size": 10})


def box(ax, x, y, w, h, title, lines=(), color=ACCENT, fill="#EEF5FC"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=color, lw=1.6))
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=11, fontweight="bold", color=INK)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.68 - i * 0.32, line, ha="center", va="top", fontsize=9, color=INK)


def arrow(ax, p, q, label="", color=INK, rad=0.0, at=None):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=14, color=color, lw=1.3,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        x, y = at if at else ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.15)
        ax.text(x, y, label, ha="center", va="bottom", fontsize=8.5, color=MUTED, style="italic",
                bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))


def save(fig, name):
    fig.savefig(FIG / name, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  wrote", name)


# ------------------------------------------------------------------------------------ architecture
def architecture():
    fig, ax = plt.subplots(figsize=(13, 5.6))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5.6)
    ax.axis("off")
    box(ax, 0.2, 2.1, 3.0, 2.6, "Presentation", ["React 19 + TypeScript", "Vite, Mantine, TanStack Query",
                                                 "12 pages, role-aware UI", "Charts (Recharts)"])
    box(ax, 5.0, 2.1, 3.0, 2.6, "Application", ["Python 3.12, FastAPI", "JWT login, Argon2 hashes",
                                                "Role checks, Pydantic validation", "50 endpoints, parameterised SQL"])
    box(ax, 9.8, 1.3, 3.0, 4.0, "Data: PostgreSQL 18", ["20 tables (3NF)", "27 foreign keys",
                                                        "50 CHECK + 1 EXCLUDE", "24 functions, 18 triggers",
                                                        "14 views (derived data)", "Audit log (SECURITY DEFINER)",
                                                        "Least-privilege app role"], color=GOOD, fill="#EAF6EF")
    arrow(ax, (3.2, 3.6), (5.0, 3.6), "HTTPS / JSON (JWT)", at=(4.1, 3.72))
    arrow(ax, (5.0, 3.0), (3.2, 3.0), "responses, errors", at=(4.1, 3.12))
    arrow(ax, (8.0, 3.6), (9.8, 3.6), "1 transaction / request", at=(8.9, 3.72))
    arrow(ax, (9.8, 3.0), (8.0, 3.0), "rows, trigger errors", at=(8.9, 3.12))
    box(ax, 5.0, 0.15, 3.0, 1.4, "Sensor simulator", ["readings every 5 min / 2.5 s", "(no physical sensors)"],
        color=MUTED, fill="#F3F4F6")
    arrow(ax, (8.0, 0.85), (9.8, 1.7), "INSERT readings", at=(8.75, 1.35))
    ax.text(11.3, 0.9, "set_config('app.current_staff_id')\nidentifies the acting user\nto triggers and the audit log",
            ha="center", va="top", fontsize=8.5, color=MUTED)
    ax.set_title("Three-tier architecture: a thin API over a database that enforces the rules", fontsize=12,
                 fontweight="bold", color=INK, loc="left")
    save(fig, "arch_three_tier.png")


# ------------------------------------------------------------------------------------ incident lifecycle
def workflow():
    fig, ax = plt.subplots(figsize=(12.5, 4.2))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    steps = [("Sensor reading", "outside product limits"), ("Incident: OPEN", "raised by trigger,\nbatches linked"),
             ("INVESTIGATING", "QM assigns\ninvestigator"), ("RESOLVED", "investigation\ncompleted"),
             ("CLOSED", "QM only; actions done,\nbatches assessed")]
    xs = [0.2, 2.65, 5.1, 7.55, 10.0]
    for i, ((t, sub), x) in enumerate(zip(steps, xs, strict=True)):
        color = GOOD if t == "CLOSED" else (MUTED if i == 0 else ACCENT)
        fill = "#EAF6EF" if t == "CLOSED" else ("#F3F4F6" if i == 0 else "#EEF5FC")
        ax.add_patch(FancyBboxPatch((x, 1.6), 2.1, 1.3, boxstyle="round,pad=0.02,rounding_size=0.1", fc=fill, ec=color,
                                    lw=1.6))
        ax.text(x + 1.05, 2.55, t, ha="center", va="center", fontsize=10.5, fontweight="bold", color=INK)
        ax.text(x + 1.05, 2.05, sub, ha="center", va="center", fontsize=8.5, color=INK)
        if i:
            arrow(ax, (xs[i - 1] + 2.1, 2.25), (x, 2.25))
    arrow(ax, (8.6, 1.6), (6.15, 1.6), "QM reopens", rad=-0.35, at=(7.38, 0.75))
    ax.text(6.25, 0.25, "Each transition is checked by the trigger trg_incident_lifecycle; a refused step returns the "
            "reason (e.g. 'corrective actions that are not finished').", ha="center", fontsize=9, color=MUTED)
    ax.set_title("Incident lifecycle enforced by the database", fontsize=12, fontweight="bold", color=INK, loc="left")
    save(fig, "workflow_incident_lifecycle.png")


def batch_states():
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.8)
    ax.axis("off")
    pos = OrderedDict(available=(0.3, 2.0), on_hold=(3.2, 3.2), quarantined=(3.2, 0.6), released=(6.6, 2.0),
                      returned=(9.6, 3.2), disposed=(9.6, 0.6))
    for name, (x, y) in pos.items():
        terminal = name in ("returned", "disposed")
        ax.add_patch(FancyBboxPatch((x, y), 2.0, 0.9, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc="#F3F4F6" if terminal else "#EEF5FC", ec=MUTED if terminal else ACCENT, lw=1.6))
        ax.text(x + 1.0, y + 0.45, name.replace("_", " "), ha="center", va="center", fontsize=10.5, fontweight="bold")

    def edge(a, b, label, rad=0.0):
        (xa, ya), (xb, yb) = pos[a], pos[b]
        arrow(ax, (xa + 2.0 if xb > xa else xa, ya + 0.45), (xb if xb > xa else xb + 2.0, yb + 0.45), label, rad=rad)

    edge("available", "on_hold", "Investigator, QM")
    edge("available", "quarantined", "QM")
    arrow(ax, (5.2, 3.45), (6.6, 2.6), "QM", at=(6.0, 2.75))                         # on_hold -> released
    edge("quarantined", "released", "QM")
    edge("on_hold", "returned", "QM")
    edge("quarantined", "disposed", "QM")
    arrow(ax, (4.2, 3.2), (4.2, 1.5), "QM", at=(4.45, 2.25))                         # on_hold -> quarantined
    arrow(ax, (7.6, 2.9), (5.2, 3.9), "Investigator, QM", rad=0.2, at=(6.6, 4.05))   # released -> on_hold
    ax.text(6.0, 0.15, "Rows of BATCH_STATUS_TRANSITION (from, to, role). The trigger trg_batch_status_check refuses any "
            "change not listed for the acting staff member's role. on_hold -> disposed and quarantined -> returned are "
            "also allowed (QM).", ha="center", fontsize=8.5, color=MUTED, wrap=True)
    ax.set_title("Batch decision workflow (recorded decisions, never automatic)", fontsize=12, fontweight="bold",
                 color=INK, loc="left")
    save(fig, "workflow_batch_status.png")


# ------------------------------------------------------------------------------------ tests
def tests():
    ev = json.loads((HERE / "evidence" / "test_evidence.json").read_text(encoding="utf-8"))
    cats = OrderedDict()
    for r in ev:
        c = cats.setdefault(r["module"], [0, 0])
        c[0 if r["status"] == "Pass" else 1] += 1
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    names = list(cats)
    passed = [cats[n][0] for n in names]
    failed = [cats[n][1] for n in names]
    ax.barh(names, passed, color=GOOD, label="Pass")
    ax.barh(names, failed, left=passed, color="#D64545", label="Fail")
    for i, v in enumerate(passed):
        ax.text(v + 0.1, i, f"{v}/{v + failed[i]}", va="center", fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Lab-manual test cases")
    ax.set_title(f"Test cases TC01-TC34 by module: {sum(passed)} of {len(ev)} pass (evidence run)", fontsize=11,
                 loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    save(fig, "tests_by_module.png")

    root = ET.parse(HERE / "evidence" / "pytest_junit.xml").getroot()
    files = Counter()
    failed_files = Counter()
    for tc in root.iter("testcase"):
        f = tc.get("classname", "").split(".")[-1]
        files[f] += 1
        if tc.find("failure") is not None or tc.find("error") is not None:
            failed_files[f] += 1
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    names = list(files)
    ax.barh(names, [files[n] - failed_files[n] for n in names], color=ACCENT)
    for i, n in enumerate(names):
        ax.text(files[n] + 0.2, i, f"{files[n] - failed_files[n]}/{files[n]}", va="center", fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Automated tests (pytest)")
    ax.set_title(f"Automated test suite: {sum(files.values()) - sum(failed_files.values())} of {sum(files.values())} pass",
                 fontsize=11, loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "tests_pytest_by_file.png")


def size():
    objects = OrderedDict([("Tables", 20), ("Foreign keys", 27), ("CHECK constraints", 50), ("Indexes (explicit)", 27),
                           ("Functions", 24), ("Triggers", 18), ("Views", 14), ("API endpoints", 50)])
    lines = OrderedDict([("SQL (db/)", 1055), ("Backend (Python)", 1144), ("Frontend (TypeScript)", 1861),
                         ("Tests (Python)", 780), ("Benchmark (C++/Python)", 715)])
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    for ax, data, title, color in ((axes[0], objects, "Database and API objects", GOOD),
                                   (axes[1], lines, "Lines of code by part", ACCENT)):
        ax.barh(list(data), list(data.values()), color=color)
        for i, v in enumerate(data.values()):
            ax.text(v * 1.01, i, f"{v:,}", va="center", fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=11, loc="left", fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save(fig, "project_size.png")


def copies():
    pairs = {
        ROOT / "docs/lab-manual/diagrams/fig3_1_er_diagram_chen.png": "er_diagram_chen.png",
        ROOT / "docs/lab-manual/diagrams/fig5_1_dfd_level0.png": "dfd_level0.png",
        ROOT / "docs/lab-manual/diagrams/fig5_2_dfd_level1.png": "dfd_level1.png",
        ROOT / "docs/lab-manual/diagrams/fig5_3_dfd_level2_process5.png": "dfd_level2_p5.png",
        ROOT / "docs/lab-manual/diagrams/fig5_4_dfd_level2_process6.png": "dfd_level2_p6.png",
        ROOT / "benchmark/results/figures/throughput.png": "bench_throughput_4configs.png",
        ROOT / "benchmark/results/figures/latency.png": "bench_latency_4configs.png",
        ROOT / "benchmark/results/figures/memory.png": "bench_memory_4configs.png",
    }
    for src, dst in pairs.items():
        shutil.copy(src, FIG / dst)
        print("  copied", dst)


if __name__ == "__main__":
    architecture()
    workflow()
    batch_states()
    tests()
    size()
    copies()
