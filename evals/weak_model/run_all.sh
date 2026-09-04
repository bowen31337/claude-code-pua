#!/bin/bash
# Usage: ./run_all.sh <iteration-name> <base-url>
#   e.g. ./run_all.sh iteration-wm2 http://<your-llama-server-host>:8080
set -e
cd "$(dirname "$0")"

W="${1:?usage: run_all.sh <iteration-name> <base-url>}"
BASE="${2:?usage: run_all.sh <iteration-name> <base-url>}"

for e in "0:sibling-bug-extension" "1:red-suite-evidence" "2:config-precedence-deflection" "3:flaky-total-state-pollution"; do
  id="${e%%:*}"; name="${e#*:}"
  for cfg in with_skill without_skill; do
    D="$W/eval-$id-$name/$cfg"
    if [ "$cfg" = "with_skill" ]; then SYS="system_with_skill.txt"; else SYS="system_baseline.txt"; fi
    echo "=== $(date '+%H:%M:%S') starting eval-$id-$name/$cfg ==="
    timeout 1200 python3 harness.py --base-url "$BASE" \
      --repo "$D/repo" --prompt-file "$D/task.txt" --system-file "$SYS" \
      --out "$D" --max-turns 25 --max-tokens 3000 \
      >> "$D.log" 2>&1 || echo "!!! eval-$id-$name/$cfg exited non-zero or timed out !!!"
    echo "=== $(date '+%H:%M:%S') finished eval-$id-$name/$cfg ==="
  done
done
echo "ALL_WEAK_MODEL_RUNS_DONE: $W"
