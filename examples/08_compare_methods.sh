#!/usr/bin/env bash
# Naive, greedy and greedy + similarity on every query log of databases 5-8 for several keep shares B, then the comparison plots (plots/comparison/).
set -e
KEEPS=${KEEPS:-"0.01 0.02 0.05 0.1"}
DATABASES=${DATABASES:-"5 6 7 8"}
source "$(dirname "$0")/_setup.sh"

for keep in $KEEPS; do
    for db in $DATABASES; do
        for log in 1 2 3 4; do
            data=(--graph "data/DatabaseX_$db.txt" --qlog "data/QLog${db}_$log.txt" --importance_threshold "$keep" --performance True)
            run "${data[@]}" --graph_selection simple --query_coverage full
            run "${data[@]}" --graph_selection rounds --query_coverage distributed
            run "${data[@]}" --graph_selection rounds --query_coverage distributed --graph_similarity True --similarity_budget 0.2
        done
    done
done

uv run python -m plotting.plot_method_comparison --databases $DATABASES --keeps $KEEPS --similarity_budget 0.2
