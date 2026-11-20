"""Run the test suite and write docs/test-report.md: each lab-manual test case with its actual result.

Usage (from backend/): uv run python -m scripts.test_report
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

from app.config import ROOT

# lab-manual test case -> (description, pytest node name substring(s))
CASES = [
    ("TC01", "Register a valid product", ["test_tc01_"]),
    ("TC02", "Invalid temperature range rejected", ["test_tc02_"]),
    ("TC03", "Duplicate batch number rejected", ["test_tc03_"]),
    ("TC04", "Expiry before manufacture rejected", ["test_tc04_"]),
    ("TC05", "Quantity boundary (0 rejected, 1 accepted)", ["test_tc05_"]),
    ("TC06", "Product with batches cannot be deleted", ["test_tc06_"]),
    ("TC07", "Shipment with nonexistent vehicle rejected", ["test_tc07_"]),
    ("TC08", "Same origin and destination rejected", ["test_tc08_"]),
    ("TC09", "Add batch to shipment", ["test_tc09_"]),
    ("TC10", "Same batch twice in a shipment rejected", ["test_tc10_"]),
    ("TC11", "Dispatch records movements, checkpoint and status", ["test_tc11_"]),
    ("TC12", "Partial failure rolls back the whole dispatch", ["test_tc12_"]),
    ("TC13", "Expired or quarantined batch cannot be dispatched", ["test_tc13_"]),
    ("TC14", "Concurrent dispatches cannot oversell stock", ["test_tc14_"]),
    ("TC15", "Receive moves stock and closes sensor assignment", ["test_tc15_"]),
    ("TC16", "Overlapping sensor assignment rejected", ["test_tc16_"]),
    ("TC17", "Valid in-range reading, no incident", ["test_tc17_"]),
    ("TC18", "Out-of-limit reading creates and links an incident", ["test_tc18_"]),
    ("TC19", "Repeated breach appends to the same incident", ["test_tc19_"]),
    ("TC20", "Duplicate reading rejected", ["test_tc20_"]),
    ("TC21", "Future timestamp stored as invalid, no incident", ["test_tc21_"]),
    ("TC22", "Gap in readings appears in data-quality report", ["test_tc22_"]),
    ("TC23", "Original reading values protected", ["test_tc23_"]),
    ("TC24", "Only breached batches linked to incident", ["test_tc24_"]),
    ("TC25", "Wrong password rejected", ["test_tc25_"]),
    ("TC26", "Unauthorised status change rejected (API and DB)", ["test_tc26_"]),
    ("TC27", "SQL injection treated as plain text", ["test_tc27_"]),
    ("TC28", "App role cannot delete readings or write audit log", ["test_tc28_"]),
    ("TC29", "Complete an investigation (findings required)", ["test_tc29_"]),
    ("TC30", "Close blocked by pending action / unassessed batch", ["test_tc30_"]),
    ("TC31", "Close a fully resolved incident (QM only, audited)", ["test_tc31_"]),
    ("TC32", "Dashboard counts match base tables", ["test_tc32_"]),
    ("TC33", "Incident report totals match", ["test_tc33_"]),
    ("TC34", "Form validation messages", ["test_tc34_"]),
]


def main() -> None:
    backend = ROOT / "backend"
    junit = backend / ".pytest_cache" / "junit.xml"
    junit.parent.mkdir(exist_ok=True)
    proc = subprocess.run([sys.executable, "-m", "pytest", f"--junitxml={junit}", "-q"], cwd=backend,
                          capture_output=True, text=True)
    tests = []
    for tc in ET.parse(junit).getroot().iter("testcase"):
        failed = tc.find("failure") is not None or tc.find("error") is not None
        tests.append((tc.get("classname", "").split(".")[-1], tc.get("name"), "Fail" if failed else "Pass",
                      float(tc.get("time", 0))))

    lines = ["# Test report", "",
             f"Run: {datetime.now():%Y-%m-%d %H:%M}. Command: `uv run pytest` against a fresh `pharmatrace_test` database.", "",
             f"Summary: {sum(t[2] == 'Pass' for t in tests)} of {len(tests)} automated tests passed.", "",
             "## Lab-manual test cases", "", "| TC ID | Test | Automated test(s) | Actual result | Status |",
             "|---|---|---|---|---|"]
    for tc_id, desc, keys in CASES:
        hits = [t for t in tests if any(k in t[1] for k in keys)]
        status = "Not run" if not hits else ("Pass" if all(t[2] == "Pass" for t in hits) else "Fail")
        actual = "As expected" if status == "Pass" else ("See failure output" if hits else "No automated test")
        lines.append(f"| {tc_id} | {desc} | {', '.join(t[1] for t in hits)} | {actual} | {status} |")
    lines += ["", "## All automated tests", "", "| File | Test | Result | Time (s) |", "|---|---|---|---|"]
    lines += [f"| {f} | {n} | {s} | {t:.2f} |" for f, n, s, t in tests]
    lines += ["", "## pytest output", "", "```", proc.stdout.strip()[-3000:], "```"]
    out = ROOT / "docs" / "test-report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(tests)} tests, exit code {proc.returncode})")


if __name__ == "__main__":
    main()
