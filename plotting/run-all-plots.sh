#!/usr/bin/env bash
# Makes every plot in plots/: query log charts, measure charts, the worked example runs, the full method comparison, the small
# databases comparison, the graph similarity budget comparison and the baseline dataset (about 1.5 hours).
# The output of steps 1-3 goes to plots/run-all-plots.log; steps 4-7 show a progress bar and log to runs.log in their folder.
# To only redraw existing plots from their CSVs (no runs): uv run python -m plotting.replot
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/.."
LOG="$ROOT/plots/run-all-plots.log"
mkdir -p "$ROOT/plots"
: > "$LOG"

step() { echo "[$1/7] $2"; }

step 1 "query log charts            -> plots/q_logs/"
"$HERE/query-log-charts.sh" >> "$LOG" 2>&1

step 2 "measure charts              -> plots/measures/"
"$HERE/measure-charts.sh" >> "$LOG" 2>&1

step 3 "worked example runs (naive, greedy, greedy + graph similarity on DatabaseX_7 + QLog7_2, B = 2%) -> plots/runs/"
for example in 01_naive_full_coverage 04_greedy_rounds 05_greedy_with_graph_similarity; do
    echo "      $example"
    "$ROOT/examples/$example.sh" >> "$LOG" 2>&1
done

step 4 "method comparison, databases 5-8 (192 runs) -> plots/comparison/"
"$HERE/compare-methods.sh"

step 5 "method comparison, small databases 1-4 (96 runs) -> plots/comparison/small_databases/"
"$HERE/compare-small-databases.sh"

step 6 "graph similarity budgets, databases 5-8 (96 runs) -> plots/comparison/similarity_budget/"
"$HERE/compare-similarity-budgets.sh"

step 7 "baseline dataset, group 15 filtered (13 runs) -> plots/baseline/"
"$HERE/baseline-comparison.sh"

echo "All plots done."
