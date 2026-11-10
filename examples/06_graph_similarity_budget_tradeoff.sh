#!/usr/bin/env bash
# Graph similarity with few slots (1%): budget 0.2 vs 0.5, the slots it takes cost answers to known queries.
set -e
KEEP=${KEEP:-0.01}
source "$(dirname "$0")/_setup.sh"

for budget in 0.2 0.5; do
    run --graph "$GRAPH" --qlog "$QLOG" --graph_selection rounds --query_coverage distributed --importance_threshold "$KEEP" --graph_similarity True --similarity_budget "$budget" --tests True
done
