#!/usr/bin/env bash
# Greedy + graph similarity keeping 30%: every useful graph fits, the rest of the slots are filler. With timings.
set -e
KEEP=${KEEP:-0.3}
source "$(dirname "$0")/_setup.sh"

run --graph "$GRAPH" --qlog "$QLOG" --graph_selection rounds --query_coverage distributed --importance_threshold "$KEEP" --graph_similarity True --similarity_budget 0.2 --tests True --performance True
