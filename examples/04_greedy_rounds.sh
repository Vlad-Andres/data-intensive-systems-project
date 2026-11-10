#!/usr/bin/env bash
# Greedy: pick one graph per round, recompute the gains, repeat.
set -e
source "$(dirname "$0")/_setup.sh"

run --graph "$GRAPH" --qlog "$QLOG" --graph_selection rounds --query_coverage distributed --importance_threshold "$KEEP" --tests True
