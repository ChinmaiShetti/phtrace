"""Assemble the final report from chapters/*.md, fill the generated sections, and produce .docx and .pdf.

Generated sections come straight from the project's outputs, so they cannot drift from the real results:
  <<TEST_SUMMARY>>, <<TEST_TABLE>>, <<EVIDENCE_DETAIL>>  <- evidence/test_evidence.json (backend/scripts/evidence.py)
  <<PYTEST_TABLE>>                                         <- evidence/pytest_junit.xml (pytest run)
  <<SQL:file:function>>, <<VIEW:file:view>>, <<FILE:path>> <- the source files themselves

Usage (from the repo root): py -I docs/final-report/build_report.py [--no-pdf]
Needs pandoc on PATH; the PDF step uses Microsoft Word through PowerShell COM.
"""

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NAME = "PharmaTrace_Final_Report"


def esc(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def test_parts():
    ev = json.loads((HERE / "evidence" / "test_evidence.json").read_text(encoding="utf-8"))
    root = ET.parse(HERE / "evidence" / "pytest_junit.xml").getroot()
    tests = []
    for tc in root.iter("testcase"):
        failed = tc.find("failure") is not None or tc.find("error") is not None
        tests.append((tc.get("classname", "").split(".")[-1], tc.get("name"), "Fail" if failed else "Pass",
                      float(tc.get("time", 0))))

    mods = OrderedDict()
    for r in ev:
        m = mods.setdefault(r["module"], [0, 0, []])
        m[0] += r["status"] == "Pass"
        m[1] += 1
        m[2].append(r["tc"])
    summary = ["| Module | Test cases | Passed |", "|---|---|---|"]
    summary += [f"| {k} | {', '.join(v[2])} | {v[0]} / {v[1]} |" for k, v in mods.items()]
    passed_ev = sum(r["status"] == "Pass" for r in ev)
    passed_py = sum(t[2] == "Pass" for t in tests)
    summary += [f"| **Total (lab-manual test cases)** | TC01–TC34 | **{passed_ev} / {len(ev)}** |",
                f"| **Automated pytest suite** | 5 files | **{passed_py} / {len(tests)}** |"]

    table = ["| TC | Module | Test | Input / action | Expected | Actual result (system output) | Status |",
             "|---|---|---|---|---|---|---|"]
    table += ["| " + " | ".join(esc(r[k]) for k in ("tc", "module", "title", "action", "expected", "actual", "status")) + " |"
              for r in ev]

    detail = []
    for r in ev:
        detail += [f"**{r['tc']}: {r['title']}** ({r['module']})", "",
                   f"- *Input / action:* {r['action']}",
                   f"- *Expected:* {r['expected']}",
                   f"- *Actual (system output):* `{r['actual']}`" if len(r["actual"]) < 140 else
                   f"- *Actual (system output):* {r['actual']}",
                   f"- *Status:* **{r['status']}**", ""]

    by_file = OrderedDict()
    for f, n, s, t in tests:
        by_file.setdefault(f, []).append((n, s, t))
    py = ["| File | Tests | Passed | Test names |", "|---|---|---|---|"]
    for f, items in by_file.items():
        names = ", ".join(f"`{n}`" for n, _, _ in items)
        py.append(f"| {f}.py | {len(items)} | {sum(s == 'Pass' for _, s, _ in items)} | {names} |")
    return "\n".join(summary), "\n".join(table), "\n".join(detail), "\n".join(py)


def sql_function(path: str, name: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    m = re.search(rf"^CREATE FUNCTION {re.escape(name)}\(.*?^\$\$;", text, re.S | re.M)
    if not m:
        raise SystemExit(f"function {name} not found in {path}")
    return m.group(0)


def sql_view(path: str, name: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    m = re.search(rf"^CREATE VIEW {re.escape(name)} AS.*?;\s*$", text, re.S | re.M)
    if not m:
        raise SystemExit(f"view {name} not found in {path}")
    return m.group(0).strip()


def build() -> Path:
    parts = [p.read_text(encoding="utf-8") for p in sorted((HERE / "chapters").glob("*.md"))]
    doc = "\n\n".join(parts)
    summary, table, detail, py = test_parts()
    doc = (doc.replace("<<TEST_SUMMARY>>", summary).replace("<<TEST_TABLE>>", table)
              .replace("<<EVIDENCE_DETAIL>>", detail).replace("<<PYTEST_TABLE>>", py))
    doc = re.sub(r"<<SQL:([^:>]+):([a-z_]+)>>", lambda m: sql_function(m.group(1), m.group(2)), doc)
    doc = re.sub(r"<<VIEW:([^:>]+):([a-z_]+)>>", lambda m: sql_view(m.group(1), m.group(2)), doc)
    doc = re.sub(r"<<FILE:([^>]+)>>", lambda m: (ROOT / m.group(1)).read_text(encoding="utf-8").strip(), doc)
    left = re.findall(r"<<[A-Z_]+[^>]*>>", doc)
    if left:
        raise SystemExit(f"unfilled placeholders: {left}")
    for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", doc):
        if not (HERE / img).exists():
            raise SystemExit(f"missing image: {img}")
    out = HERE / f"{NAME}.md"
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out.name} ({len(doc.splitlines())} lines)")
    return out


def to_docx(md: Path) -> Path:
    docx = HERE / f"{NAME}.docx"
    subprocess.run(["pandoc", md.name, "-o", docx.name, "--toc", "--toc-depth=2", "--resource-path=.",
                    "--metadata", "toc-title=Contents"], cwd=HERE, check=True)
    print(f"wrote {docx.name}")
    return docx


def to_pdf(docx: Path) -> None:
    """Open in Word, refresh the table of contents, fit tables and images to the page, save, export PDF."""
    pdf = docx.with_suffix(".pdf")
    ps = f"""
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {{
  $d = $w.Documents.Open('{docx}')
  foreach ($t in $d.Tables) {{ $t.AutoFitBehavior(2); $t.Borders.Enable = $true }}
  $usable = $d.PageSetup.PageWidth - $d.PageSetup.LeftMargin - $d.PageSetup.RightMargin
  foreach ($s in $d.InlineShapes) {{ if ($s.Width -gt $usable) {{ $r = $usable / $s.Width; $s.Width = $usable; }} }}
  foreach ($toc in $d.TablesOfContents) {{ $toc.Update() }}
  $d.Fields.Update() | Out-Null
  $d.Save()
  $d.ExportAsFixedFormat('{pdf}', 17)
  $d.Close()
}} finally {{ $w.Quit() }}
"""
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True)
    print(f"wrote {pdf.name}")


if __name__ == "__main__":
    md = build()
    docx = to_docx(md)
    if "--no-pdf" not in sys.argv:
        to_pdf(docx)
