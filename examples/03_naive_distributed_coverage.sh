#!/usr/bin/env bash
# Naive, each query's point is split over the graphs that answer it.
set -e
source "$(dirname "$0")/_setup.sh"

run --graph "$GRAPH" --qlog "$QLOG" --graph_selection simple --query_coverage distributed --importance_threshold "$KEEP" --tests True
