#!/usr/bin/env python3
"""Re-extract final_response.md from each run's transcript.json using the fixed
extract_block(). Flags any run where the old (buggy) extraction differs from the
corrected one, so nothing is silently overwritten without visibility."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from harness import extract_block

W = "iteration-wm1"
changed = []
for eval_dir in sorted(os.listdir(W)):
    p = os.path.join(W, eval_dir)
    if not os.path.isdir(p):
        continue
    for cfg in ("with_skill", "without_skill"):
        d = os.path.join(p, cfg)
        tp = os.path.join(d, "outputs", "transcript.json")
        if not os.path.exists(tp):
            continue
        messages = json.load(open(tp))
        last_assistant = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
        new_final = extract_block(last_assistant, "final")
        if new_final is None:
            new_final = "[INCOMPLETE -- hit max-turns without declaring done. Last assistant message follows]\n\n" + last_assistant
        old_path = os.path.join(d, "outputs", "final_response.md")
        old_final = open(old_path).read() if os.path.exists(old_path) else None
        if new_final != old_final:
            changed.append((eval_dir, cfg, len(old_final or ""), len(new_final)))
            open(old_path, "w").write(new_final)

if changed:
    print(f"{'run':45s} {'old chars':>10s} {'new chars':>10s}")
    for e, c, o, n in changed:
        flag = "  <-- WAS TRUNCATED" if n > o else "  (changed)"
        print(f"{e+'/'+c:45s} {o:10d} {n:10d}{flag}")
else:
    print("no runs needed correction")
