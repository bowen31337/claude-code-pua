#!/bin/bash
set -e
cd "$(dirname "$0")"
BASE="http://<your-llama-server-host>:8080"
for n in 1 2 3 4 5 6; do
  echo "########## $(date '+%H:%M:%S') ITERATION-WMT$n START ##########"
  ./run_all_tools.sh "iteration-wmt$n" "$BASE"
  echo "########## $(date '+%H:%M:%S') ITERATION-WMT$n COMPLETE ##########"
done
echo "ALL_6_TOOLS_REPEATS_DONE"
