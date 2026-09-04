#!/bin/bash
# Usage: ./run_all_tools.sh <iteration-name> <base-url>
set -e
cd "$(dirname "$0")"
W="${1:?usage: run_all_tools.sh <iteration-name> <base-url>}"
BASE="${2:?usage: run_all_tools.sh <iteration-name> <base-url>}"

for e in "0:sibling-bug-extension" "1:red-suite-evidence" "2:config-precedence-deflection" "3:flaky-total-state-pollution"; do
  id="${e%%:*}"; name="${e#*:}"
  for cfg in with_skill without_skill; do
    D="$W/eval-$id-$name/$cfg"
    if [ "$cfg" = "with_skill" ]; then SYS="system_with_skill.txt"; else SYS="system_baseline.txt"; fi
    echo "=== $(date '+%H:%M:%S') starting eval-$id-$name/$cfg ==="
    timeout 900 python3 harness_tools.py --base-url "$BASE" \
      --repo "$D/repo" --prompt-file "$D/task.txt" --system-file "$SYS" \
      --out "$D" --max-turns 25 --max-tokens 3000 \
      >> "$D.log" 2>&1 || echo "!!! eval-$id-$name/$cfg exited non-zero or timed out !!!"
    echo "=== $(date '+%H:%M:%S') finished eval-$id-$name/$cfg ==="
  done
done
echo "ALL_TOOLS_RUNS_DONE: $W"
