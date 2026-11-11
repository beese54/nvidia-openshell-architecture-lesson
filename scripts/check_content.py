#!/usr/bin/env python3
"""Static check: every evidence citation in index.html points at a real audit row.

Run from the repository root:  python scripts/check_content.py
Exits 1 on any problem. The dynamic checks (every panel opens, every quiz
answers, every scenario steps) live in the page itself: open
index.html?selftest=1, or run scripts/selftest.sh.
"""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
audit = (root / "tasks" / "doc_audit.md").read_text(encoding="utf-8")
page = (root / "index.html").read_text(encoding="utf-8")

status = {}
for line in audit.splitlines():
    m = re.match(r"\| ([A-Z]\d+) \|", line)
    if m:
        last = line.rstrip().rstrip("|").split(" | ")[-1].strip()
        status[m.group(1)] = last

problems = []
cited = set()
lists = re.findall(r"rows:\s*\[([^\]]*)\]", page)
for body in lists:
    ids = re.findall(r'"([^"]+)"|\'([^\']+)\'', body)
    ids = [a or b for a, b in ids]
    if not ids:
        problems.append("an empty rows:[] list")
    for i in ids:
        cited.add(i)
        if i not in status:
            problems.append(f"cites {i}, which is not a row in tasks/doc_audit.md")
        elif status[i].startswith("UNVERIFIED"):
            problems.append(f"cites {i}, which is UNVERIFIED")

inferred = sorted(i for i in cited if status.get(i, "").startswith("INF"))
print(f"audit rows: {len(status)}   citation lists in page: {len(lists)}   distinct rows cited: {len(cited)}")
print(f"cited rows that are INFERRED (must carry the INFERRED badge): {', '.join(inferred) or 'none'}")
never = sorted(i for i in status if i not in cited and not i.startswith("J"))
print(f"audit rows never cited: {', '.join(never) or 'none'}")

# INFERRED rows may only be cited by evidence items badged "I" (or alongside other rows in a step/quiz).
for m in re.finditer(r'\{b:"([OSDI])",x:"(?:[^"\\]|\\.)*",rows:\[([^\]]*)\]\}', page):
    badge, ids = m.group(1), re.findall(r'"([^"]+)"', m.group(2))
    if ids and all(status.get(i, "").startswith("INF") for i in ids) and badge != "I":
        problems.append(f"evidence citing only inferred rows {ids} is badged {badge}, not I")

if problems:
    print("\nPROBLEMS:")
    for p in sorted(set(problems)):
        print(" -", p)
    sys.exit(1)
print("OK")
