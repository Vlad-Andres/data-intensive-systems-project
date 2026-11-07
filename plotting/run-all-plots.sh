#!/usr/bin/env bash
# Makes every plot in plots/: query log charts, measure charts, the worked example runs and the full method comparison.
# The output of steps 1-3 goes to plots/run-all-plots.log; step 4 shows a progress bar and logs to plots/comparison/runs.log.
# To only redraw existing plots from their CSVs (no runs): uv run python -m plotting.replot
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/.."
LOG="$ROOT/plots/run-all-plots.log"
mkdir -p "$ROOT/plots"
: > "$LOG"

step() { echo "[$1/4] $2"; }

step 1 "query log charts            -> plots/q_logs/"
"$HERE/query-log-charts.sh" >> "$LOG" 2>&1

step 2 "measure charts              -> plots/measures/"
"$HERE/measure-charts.sh" >> "$LOG" 2>&1

step 3 "worked example runs (naive, greedy, greedy + graph similarity on DatabaseX_7 + QLog7_2, B = 2%) -> plots/runs/"
for example in 01_naive_full_coverage 04_greedy_rounds 05_greedy_with_graph_similarity; do
    echo "      $example"
    "$ROOT/examples/$example.sh" >> "$LOG" 2>&1
done

step 4 "method comparison (192 runs) -> plots/comparison/"
"$HERE/compare-methods.sh"

echo "All plots done."
