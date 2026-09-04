#!/bin/bash
set -e
cd "$(dirname "$0")"
BASE="http://<your-llama-server-host>:8080"
for n in 2 3 4 5 6; do
  echo "########## $(date '+%H:%M:%S') ITERATION-WM$n START ##########"
  ./run_all.sh "iteration-wm$n" "$BASE"
  echo "########## $(date '+%H:%M:%S') ITERATION-WM$n COMPLETE ##########"
done
echo "ALL_5_REPEATS_DONE"
