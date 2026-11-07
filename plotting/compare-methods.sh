#!/usr/bin/env bash
# Naive, greedy and greedy + graph similarity on every query log of databases 5-8 for several keep shares B, then the comparison plots (plots/comparison/).
# Shows a progress bar; the full output of every run goes to plots/comparison/runs.log.
set -e
KEEPS=${KEEPS:-"0.01 0.02 0.05 0.1"}
DATABASES=${DATABASES:-"5 6 7 8"}
source "$(dirname "$0")/../examples/_setup.sh"

METHODS=(
    "naive|--graph_selection simple --query_coverage full"
    "greedy|--graph_selection rounds --query_coverage distributed"
    "greedy + graph similarity|--graph_selection rounds --query_coverage distributed --graph_similarity True --similarity_budget 0.2"
)
LOG=plots/comparison/runs.log
mkdir -p plots/comparison
: > "$LOG"
total=$(( $(wc -w <<< "$KEEPS") * $(wc -w <<< "$DATABASES") * 4 * ${#METHODS[@]} ))
finished=0
start=$(date +%s)

progress() {  # [#####     ] runs done / total, estimated minutes left, current run
    local width=30 filled=$(( finished * 30 / total )) left="?"
    [ "$finished" -gt 0 ] && left="$(( ($(date +%s) - start) * (total - finished) / finished / 60 ))m"
    printf "\r[%-${width}s] %3d/%d  ~%-4s left  %-60s" "$(printf "%${filled}s" | tr ' ' '#')" "$finished" "$total" "$left" "$1"
}

for keep in $KEEPS; do
    for db in $DATABASES; do
        for log in 1 2 3 4; do
            for method in "${METHODS[@]}"; do
                name=${method%%|*}
                flags=${method#*|}
                progress "DatabaseX_$db · QLog${db}_$log · B=$keep · $name"
                if ! uv run main.py --graph "data/DatabaseX_$db.txt" --qlog "data/QLog${db}_$log.txt" \
                        --importance_threshold "$keep" --performance True $flags >> "$LOG" 2>&1; then
                    echo; echo "Run failed: DatabaseX_$db QLog${db}_$log B=$keep $name. Last lines of $LOG:"; tail -20 "$LOG"; exit 1
                fi
                finished=$(( finished + 1 ))
            done
        done
    done
done
progress "all runs done"; echo

echo "Computing the comparison metrics (results.csv) and drawing the plots..."
uv run python -m plotting.plot_method_comparison --databases $DATABASES --keeps $KEEPS --similarity_budget 0.2
