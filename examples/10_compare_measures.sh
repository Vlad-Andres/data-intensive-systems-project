#!/usr/bin/env bash
# Scores of every graph under the full, partial and distributed measures, side by side (plots/measures/).
set -e
source "$(dirname "$0")/_setup.sh"

uv run python -m plotting.plot_measures --graph data/toy_restaurants_database.txt --qlog data/toy_restaurants_qlog.txt
uv run python -m plotting.plot_measures --graph data/DatabaseX_3.txt --qlog data/QLog3_3.txt
