#!/usr/bin/env bash
# One bar chart per query log type: how many times each query is asked (plots/q_logs/).
set -e
source "$(dirname "$0")/../examples/_setup.sh"

uv run python -m plotting.plot_query_logs
