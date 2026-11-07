#!/usr/bin/env bash
# Naive, greedy and greedy + graph similarity on every query log of the small databases 1-4 (20 graphs each), with larger keep
# shares B (20% = 4 graphs, 40% = 8 graphs), then their comparison plots (plots/comparison/small_databases/).
# Shows a progress bar; the full output of every run goes to plots/comparison/small_databases/runs.log.
set -e
KEEPS=${KEEPS:-"0.2 0.4"}
DATABASES=${DATABASES:-"1 2 3 4"}
source "$(dirname "$0")/../examples/_setup.sh"
source plotting/_progress.sh

METHODS=(
    "naive|--graph_selection simple --query_coverage full"
    "greedy|--graph_selection rounds --query_coverage distributed"
    "greedy + graph similarity|--graph_selection rounds --query_coverage distributed --graph_similarity True --similarity_budget 0.2"
)
LOG=plots/comparison/small_databases/runs.log
mkdir -p plots/comparison/small_databases
: > "$LOG"
total=$(( $(wc -w <<< "$KEEPS") * $(wc -w <<< "$DATABASES") * 4 * ${#METHODS[@]} ))

for keep in $KEEPS; do
    for db in $DATABASES; do
        for log in 1 2 3 4; do
            for method in "${METHODS[@]}"; do
                run_main "DatabaseX_$db · QLog${db}_$log · B=$keep · ${method%%|*}" \
                    --graph "data/DatabaseX_$db.txt" --qlog "data/QLog${db}_$log.txt" --importance_threshold "$keep" --performance True ${method#*|}
            done
        done
    done
done
progress "all runs done"; echo

echo "Computing the metrics (results.csv) and drawing the plots..."
uv run python -m plotting.plot_extra_comparisons small-databases --databases $DATABASES --keeps $KEEPS
