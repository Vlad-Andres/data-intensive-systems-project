#!/usr/bin/env bash
# Naive, greedy and greedy + graph similarity on the baseline dataset (group 15, filtered: peer-dataset-test/Dataset24_fixed/)
# for several keep shares B, one worked greedy run with every phase plot (plots/runs/), then the baseline plots (plots/baseline/).
# Shows a progress bar; the full output of every run goes to plots/baseline/runs.log.
set -e
KEEPS=${KEEPS:-"0.01 0.02 0.05 0.1"}
source "$(dirname "$0")/../examples/_setup.sh"
source plotting/_progress.sh

DATA=(--graph peer-dataset-test/Dataset24_fixed/Database15.txt --qlog peer-dataset-test/Dataset24_fixed/QLog15_1.txt)
METHODS=(
    "naive|--graph_selection simple --query_coverage full"
    "greedy|--graph_selection rounds --query_coverage distributed"
    "greedy + graph similarity|--graph_selection rounds --query_coverage distributed --graph_similarity True --similarity_budget 0.2"
)
LOG=plots/baseline/runs.log
mkdir -p plots/baseline
: > "$LOG"
total=$(( $(wc -w <<< "$KEEPS") * ${#METHODS[@]} + 1 ))

for keep in $KEEPS; do
    for method in "${METHODS[@]}"; do
        run_main "baseline · B=$keep · ${method%%|*}" "${DATA[@]}" --importance_threshold "$keep" --performance True ${method#*|}
    done
done
# Worked example with the evaluation phase (4_evaluation) for the report; same reduction as the greedy run at B = 2%.
run_main "baseline · B=0.02 · greedy (worked example with tests)" "${DATA[@]}" --importance_threshold 0.02 --performance True \
    --graph_selection rounds --query_coverage distributed --tests True
progress "all runs done"; echo

echo "Computing the metrics (results.csv) and drawing the plots..."
uv run python -m plotting.plot_baseline --keeps $KEEPS --similarity_budget 0.2
