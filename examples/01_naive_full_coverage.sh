#!/usr/bin/env bash
# Naive: sort graphs once by fully answered queries, keep the top share.
set -e
source "$(dirname "$0")/_setup.sh"

run --graph "$GRAPH" --qlog "$QLOG" --graph_selection simple --query_coverage full --importance_threshold "$KEEP" --tests True
