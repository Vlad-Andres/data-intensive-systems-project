#!/usr/bin/env bash
# Naive, greedy and greedy + similarity on every query log of databases 5-8, then one chart per database (plots/comparison/).
set -e
KEEP=${KEEP:-0.02}
DATABASES=${DATABASES:-"5 6 7 8"}
source "$(dirname "$0")/_setup.sh"

for db in $DATABASES; do
    for log in 1 2 3 4; do
        data=(--graph "data/DatabaseX_$db.txt" --qlog "data/QLog${db}_$log.txt" --importance_threshold "$KEEP")
        run "${data[@]}" --graph_selection simple --query_coverage full
        run "${data[@]}" --graph_selection rounds --query_coverage distributed
        run "${data[@]}" --graph_selection rounds --query_coverage distributed --graph_similarity True --similarity_budget 0.2
    done
done

uv run python -m plotting.plot_method_comparison --databases $DATABASES --keep "$KEEP" --similarity_budget 0.2
