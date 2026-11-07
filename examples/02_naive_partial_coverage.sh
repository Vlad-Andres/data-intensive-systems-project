#!/usr/bin/env bash
# Naive, but partly answered queries also count.
set -e
source "$(dirname "$0")/_setup.sh"

run --graph "$GRAPH" --qlog "$QLOG" --graph_selection simple --query_coverage partial --importance_threshold "$KEEP" --tests True
