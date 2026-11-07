"""
Compare reduction methods per database: coverage of the past (first half) and of the future (second half) of every query log.

Run after examples/08_compare_methods.sh has made the reductions, e.g.:
    uv run python -m plotting.plot_method_comparison --databases 5 6 7 8 --keep 0.02

Saves plots/comparison/keep_<keep>/DatabaseX_<n>.png (one chart per database) and results.csv with all numbers.
"""
import argparse
import csv
import sys
from math import comb
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIRECTORY / "src"))
from graph_parser import read_graph_database  # noqa: E402
from QLog_satisfaction import graph_satisfies_query, parse_query  # noqa: E402

# (label, part of the reduction file name written by main.py, with graph similarity?, colour)
METHODS = [
    ("naive", "full_query_coverage_simple_selection", False, "#2a78d6"),
    ("greedy", "distributed_query_coverage_rounds_selection", False, "#eb6834"),
    ("greedy + similarity", "distributed_query_coverage_rounds_selection", True, "#1baf7a"),
]
RANDOM_LABEL, RANDOM_COLOR = "random", "#c9c8c3"
QUERY_LOG_NAMES = {1: "QLog_1\npopularity", 2: "QLog_2\nshifting interest", 3: "QLog_3\ncomplex variables", 4: "QLog_4\nsub-queries"}
INK, MUTED_INK, GRID = "#1f1f1e", "#5f5e5a", "#e4e3df"


def reduction_file(database: int, query_log: int, file_part: str, keep: float, similarity_budget: float | None) -> Path:
    """Same name as main.py gives the reduced database."""
    name = f"Database{database}_{query_log}_{file_part}_keep_{keep}"
    if similarity_budget is not None:
        name += f"_graph_similarity_{similarity_budget}"
    return PROJECT_DIRECTORY / "data" / "reductions" / f"{name}.txt"


def coverage(lines: list[frozenset[int]], kept: set[int]) -> float:
    """% of query lines that at least one kept graph fully answers."""
    return 100.0 * sum(1 for answering in lines if answering & kept) / len(lines)


def random_coverage(lines: list[frozenset[int]], graph_count: int, kept_count: int) -> float:
    """Expected % of query lines answered when kept_count graphs are kept at random."""
    return 100.0 * sum(1 - comb(graph_count - len(answering), kept_count) / comb(graph_count, kept_count) for answering in lines) / len(lines)


def compare_database(database: int, keep: float, similarity_budget: float) -> list[dict]:
    database_file = PROJECT_DIRECTORY / "data" / f"DatabaseX_{database}.txt"
    database_lines = [line for line in database_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    graphs = read_graph_database(str(database_file))
    kept_count = int(len(graphs) * keep)  # Same budget as the selection in main.py.

    answering_graphs = {}

    def answering(query: str) -> frozenset[int]:
        if query not in answering_graphs:
            paths = parse_query(query)
            answering_graphs[query] = frozenset(graph_id for graph_id, graph in enumerate(graphs) if graph_satisfies_query(graph, paths))
        return answering_graphs[query]

    results = []
    for query_log in QUERY_LOG_NAMES:
        log_lines = (PROJECT_DIRECTORY / "data" / f"QLog{database}_{query_log}.txt").read_text(encoding="utf-8").splitlines()
        half = len(log_lines) // 2  # Same split as main.py: first half = past, second half = future.
        past = [answering(line.strip()) for line in log_lines[:half] if line.strip()]
        future = [answering(line.strip()) for line in log_lines[half:] if line.strip()]

        results.append({"database": database, "query_log": query_log, "method": RANDOM_LABEL,
                        "past": random_coverage(past, len(graphs), kept_count), "future": random_coverage(future, len(graphs), kept_count)})
        for label, file_part, with_similarity, _ in METHODS:
            path = reduction_file(database, query_log, file_part, keep, similarity_budget if with_similarity else None)
            if not path.exists():
                print(f"Missing {path.relative_to(PROJECT_DIRECTORY)}: run examples/08_compare_methods.sh first.")
                continue
            kept_lines = set(path.read_text(encoding="utf-8").splitlines())
            kept = {graph_id for graph_id, line in enumerate(database_lines) if line in kept_lines}
            results.append({"database": database, "query_log": query_log, "method": label,
                            "past": coverage(past, kept), "future": coverage(future, kept)})
    return results


def plot_database(database: int, results: list[dict], keep: float, output_path: Path) -> None:
    """One group of bars per query log: bar = future coverage, black line on the bar = past coverage."""
    bars = [(RANDOM_LABEL, RANDOM_COLOR)] + [(label, color) for label, _, _, color in METHODS]
    bar_width = 0.8 / len(bars)
    figure, axes = plt.subplots(figsize=(9, 4.5), layout="constrained")

    for group, query_log in enumerate(QUERY_LOG_NAMES):
        for position, (label, color) in enumerate(bars):
            row = next((r for r in results if r["query_log"] == query_log and r["method"] == label), None)
            if row is None:
                continue
            x = group + (position - (len(bars) - 1) / 2) * bar_width
            axes.bar(x, row["future"], width=bar_width * 0.85, color=color)
            axes.plot([x - bar_width * 0.42, x + bar_width * 0.42], [row["past"]] * 2, color=INK, linewidth=2)

    axes.set_xticks(range(len(QUERY_LOG_NAMES)), list(QUERY_LOG_NAMES.values()), fontsize=9, color=INK)
    axes.set_ylim(0, 105)
    axes.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], fontsize=8, color=MUTED_INK)
    axes.set_ylabel("query lines answered", color=MUTED_INK, fontsize=9)
    axes.yaxis.grid(True, color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)
    axes.set_title(f"DatabaseX_{database} · {keep:.0%} of the graphs kept", loc="left", color=INK, fontsize=11)

    figure.legend(
        handles=[Patch(color=color, label=label) for label, color in bars]
        + [Line2D([], [], color=INK, linewidth=2, label="past (first half)")],
        loc="outside lower center", ncol=len(bars) + 1, frameon=False, fontsize=8, labelcolor=MUTED_INK,
        title="bars = future (second half)", title_fontsize=8,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {output_path.relative_to(PROJECT_DIRECTORY)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot past and future query coverage of the reduction methods per database.")
    parser.add_argument("--databases", type=int, nargs="+", default=[5, 6, 7, 8], help="Database numbers to compare.")
    parser.add_argument("--keep", type=float, default=0.02, help="Share of graphs kept, as passed to main.py --importance_threshold.")
    parser.add_argument("--similarity_budget", type=float, default=0.2, help="Similarity budget, as passed to main.py.")
    args = parser.parse_args()

    output_folder = PROJECT_DIRECTORY / "plots" / "comparison" / f"keep_{args.keep}"
    all_results = []
    for database in args.databases:
        results = compare_database(database, args.keep, args.similarity_budget)
        plot_database(database, results, args.keep, output_folder / f"DatabaseX_{database}.png")
        all_results.extend(results)

    output_folder.mkdir(parents=True, exist_ok=True)
    with open(output_folder / "results.csv", "w", newline="", encoding="utf-8") as results_file:
        writer = csv.DictWriter(results_file, fieldnames=["database", "query_log", "method", "past", "future"])
        writer.writeheader()
        writer.writerows({**row, "past": f"{row['past']:.1f}", "future": f"{row['future']:.1f}"} for row in all_results)
    print(f"Saved {(output_folder / 'results.csv').relative_to(PROJECT_DIRECTORY)}")
