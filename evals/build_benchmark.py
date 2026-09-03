#!/usr/bin/env python3
"""Build benchmark.json for an iteration from its grading.json + timing.json files.

Usage: python3 build_benchmark.py iteration-2 [--notes notes.txt]
"""
import json, os, sys, statistics as st

W = os.path.dirname(os.path.abspath(__file__))
IT_NAME = sys.argv[1] if len(sys.argv) > 1 else "iteration-2"
IT = os.path.join(W, IT_NAME)

runs, agg = [], {c: {"pass_rate": [], "time_seconds": [], "tokens": [], "tool_calls": []}
                 for c in ("with_skill", "without_skill")}
missing = []

for d in sorted(os.listdir(IT)):
    p = os.path.join(IT, d)
    if not os.path.isdir(p) or not d.startswith("eval-"):
        continue
    eid = int(d.split("-")[1])
    name = d.split("-", 2)[2]
    for cfg in ("with_skill", "without_skill"):
        gp, tp = os.path.join(p, cfg, "grading.json"), os.path.join(p, cfg, "timing.json")
        if not (os.path.exists(gp) and os.path.exists(tp)):
            missing.append(f"{d}/{cfg}")
            continue
        g, t = json.load(open(gp)), json.load(open(tp))
        pr = g["passed"] / g["total"]
        runs.append({
            "eval_id": eid, "eval_name": name, "configuration": cfg, "run_number": 1,
            "result": {"pass_rate": pr, "passed": g["passed"],
                       "failed": g["total"] - g["passed"], "total": g["total"],
                       "time_seconds": t["total_duration_seconds"], "tokens": t["total_tokens"],
                       "tool_calls": t.get("tool_uses", 0), "errors": 0},
            "expectations": g["expectations"], "notes": []})
        agg[cfg]["pass_rate"].append(pr)
        agg[cfg]["time_seconds"].append(t["total_duration_seconds"])
        agg[cfg]["tokens"].append(t["total_tokens"])
        agg[cfg]["tool_calls"].append(t.get("tool_uses", 0))

if missing:
    print("INCOMPLETE - refusing to build benchmark. Missing:", *missing, sep="\n  ")
    sys.exit(1)

def stats(v):
    return {"mean": round(st.mean(v), 4), "stddev": round(st.pstdev(v), 4),
            "min": round(min(v), 4), "max": round(max(v), 4)}

summary = {c: {k: stats(v) for k, v in m.items()} for c, m in agg.items()}
summary["delta"] = {
    "pass_rate": f"{summary['with_skill']['pass_rate']['mean'] - summary['without_skill']['pass_rate']['mean']:+.2f}",
    "time_seconds": f"{summary['with_skill']['time_seconds']['mean'] - summary['without_skill']['time_seconds']['mean']:+.1f}",
    "tokens": f"{summary['with_skill']['tokens']['mean'] - summary['without_skill']['tokens']['mean']:+.0f}",
}

notes = []
np = os.path.join(IT, "notes.txt")
if os.path.exists(np):
    notes = [l.strip() for l in open(np) if l.strip()]

bench = {"metadata": {"skill_name": "pua", "skill_path": "pua/", "executor_model": "claude-opus-5",
                      "iteration": IT_NAME, "evals_run": sorted({r["eval_name"] for r in runs}),
                      "runs_per_configuration": 1},
         "runs": runs, "run_summary": summary, "notes": notes}
json.dump(bench, open(os.path.join(IT, "benchmark.json"), "w"), indent=2)

print(f"benchmark.json written for {IT_NAME}\n")
print(f"{'eval':38s} {'with':>8s} {'base':>8s}")
by = {}
for r in runs:
    by.setdefault(r["eval_name"], {})[r["configuration"]] = r["result"]
for n, cfgs in by.items():
    w, b = cfgs["with_skill"], cfgs["without_skill"]
    print(f"{n:38s} {w['passed']:>3d}/{w['total']:<4d} {b['passed']:>3d}/{b['total']:<4d}")
tw = sum(c["with_skill"]["passed"] for c in by.values())
tb = sum(c["without_skill"]["passed"] for c in by.values())
tt = sum(c["with_skill"]["total"] for c in by.values())
print(f"{'TOTAL':38s} {tw:>3d}/{tt:<4d} {tb:>3d}/{tt:<4d}")
print("\ntokens     with:", sum(agg['with_skill']['tokens']), " base:", sum(agg['without_skill']['tokens']))
print("tool calls with:", sum(agg['with_skill']['tool_calls']), " base:", sum(agg['without_skill']['tool_calls']))
