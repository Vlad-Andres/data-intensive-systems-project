#!/usr/bin/env bash
# Greedy + graph similarity: 20% of the kept slots go to graphs adding the most new facts.
set -e
source "$(dirname "$0")/_setup.sh"

run --graph "$GRAPH" --qlog "$QLOG" --graph_selection rounds --query_coverage distributed --importance_threshold "$KEEP" --graph_similarity True --similarity_budget 0.2 --tests True
