#!/usr/bin/env python3
"""Report which reference files each with-skill run actually opened.

Parses the agent transcript JSONL and inspects tool_use blocks only, so a
mention of a filename in the prompt or inside a file's own text is not
mistaken for the agent having opened it.

Usage: python3 check_reference_loading.py <transcript-dir> [agent-id ...]
"""
import json, os, sys

TDIR = sys.argv[1]
ids = sys.argv[2:] or None
TARGETS = ("flavors.md", "methodology.md", "SKILL.md")


def tool_inputs(path):
    """Yield every tool_use input dict in the transcript."""
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            stack = [rec]
            while stack:
                cur = stack.pop()
                if isinstance(cur, dict):
                    if cur.get("type") == "tool_use" and isinstance(cur.get("input"), dict):
                        yield cur.get("name", "?"), cur["input"]
                    stack.extend(cur.values())
                elif isinstance(cur, list):
                    stack.extend(cur)


def opened(path):
    hit = {t: 0 for t in TARGETS}
    for name, inp in tool_inputs(path):
        blob = " ".join(str(v) for v in inp.values())
        for t in TARGETS:
            if t in blob:
                hit[t] += 1
    return hit


rows = []
for f in sorted(os.listdir(TDIR)):
    if not f.endswith(".output"):
        continue
    aid = f[:-7]
    if ids and aid not in ids:
        continue
    h = opened(os.path.join(TDIR, f))
    if h["SKILL.md"] == 0:
        continue
    rows.append((aid, h))

if not rows:
    print("no with-skill transcripts found")
    sys.exit(0)

print(f"{'run':20s} {'flavors.md':>12s} {'methodology.md':>16s}")
for aid, h in rows:
    print(f"{aid:20s} {('OPENED x%d' % h['flavors.md']) if h['flavors.md'] else 'closed':>12s}"
          f" {('OPENED x%d' % h['methodology.md']) if h['methodology.md'] else 'closed':>16s}")
n = len(rows)
print(f"\n{sum(1 for _, h in rows if h['flavors.md'])}/{n} opened flavors.md, "
      f"{sum(1 for _, h in rows if h['methodology.md'])}/{n} opened methodology.md")
