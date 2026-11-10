#!/usr/bin/env bash
# Greedy + graph similarity with graph similarity budgets 0.1, 0.5 and 1.0 on every query log of databases 5-8 at B = 1% and 2%,
# then the budget plot (plots/comparison/similarity_budget/). Budget 0.2 and plain greedy (budget 0) come from
# plotting/compare-methods.sh, so run that first.
# Shows a progress bar; the full output of every run goes to plots/comparison/similarity_budget/runs.log.
set -e
BUDGETS=${BUDGETS:-"0.1 0.5 1.0"}
KEEPS=${KEEPS:-"0.01 0.02"}
DATABASES=${DATABASES:-"5 6 7 8"}
source "$(dirname "$0")/../examples/_setup.sh"
source plotting/_progress.sh

LOG=plots/comparison/similarity_budget/runs.log
mkdir -p plots/comparison/similarity_budget
: > "$LOG"
total=$(( $(wc -w <<< "$KEEPS") * $(wc -w <<< "$DATABASES") * 4 * $(wc -w <<< "$BUDGETS") ))

for keep in $KEEPS; do
    for db in $DATABASES; do
        for log in 1 2 3 4; do
            for budget in $BUDGETS; do
                run_main "DatabaseX_$db · QLog${db}_$log · B=$keep · graph similarity budget $budget" \
                    --graph "data/DatabaseX_$db.txt" --qlog "data/QLog${db}_$log.txt" --importance_threshold "$keep" --performance True \
                    --graph_selection rounds --query_coverage distributed --graph_similarity True --similarity_budget "$budget"
            done
        done
    done
done
progress "all runs done"; echo

echo "Computing the metrics (results.csv) and drawing the plot..."
uv run python -m plotting.plot_extra_comparisons similarity-budgets --databases $DATABASES --keeps $KEEPS --budgets 0 0.1 0.2 $BUDGETS
