"""
Compare reduction methods per database on the past (first half) and the future (second half) of every query log, with two metrics:
  exact coverage   - % of query lines that at least one kept graph fully answers;
  closeness        - per query line, the best closeness of a kept graph (share of the query's parts it satisfies, 1 = full
                     answer, as computed by the matcher), averaged over the lines; near answers count partly.

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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIRECTORY / "src"))
from graph_parser import read_graph_database  # noqa: E402
from QLog_satisfaction import parse_query  # noqa: E402
from query_matcher_and_measurer.match_queries_with_variables_on_graphs import query_coverage_of_graph  # noqa: E402

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


def exact_coverage(lines: list[dict[int, float]], kept: set[int]) -> float:
    """% of query lines that at least one kept graph fully answers."""
    return 100.0 * sum(1 for closeness in lines if any(value == 1.0 and graph_id in kept for graph_id, value in closeness.items())) / len(lines)


def average_closeness(lines: list[dict[int, float]], kept: set[int]) -> float:
    """Per query line the best closeness of a kept graph (0 if none matches), averaged over the lines, in %."""
    return 100.0 * sum(max((value for graph_id, value in closeness.items() if graph_id in kept), default=0.0) for closeness in lines) / len(lines)


def chance_at_least_one(graphs_with_it: int, graph_count: int, kept_count: int) -> float:
    """Probability that kept_count random graphs include at least one of graphs_with_it given graphs."""
    return 1 - comb(graph_count - graphs_with_it, kept_count) / comb(graph_count, kept_count)


def random_exact_coverage(lines: list[dict[int, float]], graph_count: int, kept_count: int) -> float:
    """Expected exact coverage when kept_count graphs are kept at random."""
    return 100.0 * sum(chance_at_least_one(sum(value == 1.0 for value in closeness.values()), graph_count, kept_count)
                       for closeness in lines) / len(lines)


def random_average_closeness(lines: list[dict[int, float]], graph_count: int, kept_count: int) -> float:
    """Expected average closeness when kept_count graphs are kept at random: E[best] = sum of (step up) x P(best >= that level)."""
    total = 0.0
    for closeness in lines:
        previous_level = 0.0
        for level in sorted(set(closeness.values())):
            graphs_at_least = sum(value >= level for value in closeness.values())
            total += (level - previous_level) * chance_at_least_one(graphs_at_least, graph_count, kept_count)
            previous_level = level
    return 100.0 * total / len(lines)


METRICS = {"exact": (exact_coverage, random_exact_coverage), "closeness": (average_closeness, random_average_closeness)}


def compare_database(database: int, keep: float, similarity_budget: float) -> list[dict]:
    database_file = PROJECT_DIRECTORY / "data" / f"DatabaseX_{database}.txt"
    database_lines = [line for line in database_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    graphs = read_graph_database(str(database_file))
    kept_count = int(len(graphs) * keep)  # Same budget as the selection in main.py.

    closeness_by_query = {}

    def closeness(query: str) -> dict[int, float]:
        """Closeness of every graph that matches at least part of the query."""
        if query not in closeness_by_query:
            paths = parse_query(query)
            values = {graph_id: query_coverage_of_graph(graph, paths) for graph_id, graph in enumerate(graphs)}
            closeness_by_query[query] = {graph_id: value for graph_id, value in values.items() if value > 0}
        return closeness_by_query[query]

    results = []
    for query_log in QUERY_LOG_NAMES:
        log_lines = (PROJECT_DIRECTORY / "data" / f"QLog{database}_{query_log}.txt").read_text(encoding="utf-8").splitlines()
        half = len(log_lines) // 2  # Same split as main.py: first half = past, second half = future.
        past = [closeness(line.strip()) for line in log_lines[:half] if line.strip()]
        future = [closeness(line.strip()) for line in log_lines[half:] if line.strip()]

        row = {"database": database, "query_log": query_log, "method": RANDOM_LABEL}
        for metric, (_, random_metric) in METRICS.items():
            row[f"past_{metric}"] = random_metric(past, len(graphs), kept_count)
            row[f"future_{metric}"] = random_metric(future, len(graphs), kept_count)
        results.append(row)
        for label, file_part, with_similarity, _ in METHODS:
            path = reduction_file(database, query_log, file_part, keep, similarity_budget if with_similarity else None)
            if not path.exists():
                print(f"Missing {path.relative_to(PROJECT_DIRECTORY)}: run examples/08_compare_methods.sh first.")
                continue
            kept_lines = set(path.read_text(encoding="utf-8").splitlines())
            kept = {graph_id for graph_id, line in enumerate(database_lines) if line in kept_lines}
            row = {"database": database, "query_log": query_log, "method": label}
            for metric, (method_metric, _) in METRICS.items():
                row[f"past_{metric}"] = method_metric(past, kept)
                row[f"future_{metric}"] = method_metric(future, kept)
            results.append(row)
    return results


def plot_database(database: int, results: list[dict], keep: float, output_path: Path) -> None:
    """Top: exact coverage, bottom: closeness. One group of bars per query log: bar = future, black line on the bar = past."""
    bars = [(RANDOM_LABEL, RANDOM_COLOR)] + [(label, color) for label, _, _, color in METHODS]
    bar_width = 0.8 / len(bars)
    figure, axes_by_metric = plt.subplots(2, 1, figsize=(9, 8), layout="constrained", sharex=True)
    panels = {
        "exact": "Exact answers: query lines fully answered by a kept graph",
        "closeness": "Near answers count too: average best closeness (share of the query's parts a kept graph satisfies)",
    }

    for axes, (metric, panel_title) in zip(axes_by_metric, panels.items()):
        for group, query_log in enumerate(QUERY_LOG_NAMES):
            for position, (label, color) in enumerate(bars):
                row = next((r for r in results if r["query_log"] == query_log and r["method"] == label), None)
                if row is None:
                    continue
                x = group + (position - (len(bars) - 1) / 2) * bar_width
                axes.bar(x, row[f"future_{metric}"], width=bar_width * 0.85, color=color)
                axes.plot([x - bar_width * 0.42, x + bar_width * 0.42], [row[f"past_{metric}"]] * 2, color=INK, linewidth=2)
        axes.set_ylim(0, 105)
        axes.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], fontsize=8, color=MUTED_INK)
        axes.yaxis.grid(True, color=GRID, linewidth=0.8)
        axes.set_axisbelow(True)
        axes.tick_params(length=0)
        for spine in axes.spines.values():
            spine.set_visible(False)
        axes.set_title(panel_title, loc="left", color=INK, fontsize=10)

    axes_by_metric[-1].set_xticks(range(len(QUERY_LOG_NAMES)), list(QUERY_LOG_NAMES.values()), fontsize=9, color=INK)
    figure.suptitle(f"DatabaseX_{database} · {keep:.0%} of the graphs kept", x=0.01, ha="left", color=INK, fontsize=12)
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
    parser = argparse.ArgumentParser(description="Plot past and future exact coverage and closeness of the reduction methods per database.")
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
        columns = ["past_exact", "future_exact", "past_closeness", "future_closeness"]
        writer = csv.DictWriter(results_file, fieldnames=["database", "query_log", "method", *columns])
        writer.writeheader()
        writer.writerows({**row, **{column: f"{row[column]:.1f}" for column in columns}} for row in all_results)
    print(f"Saved {(output_folder / 'results.csv').relative_to(PROJECT_DIRECTORY)}")
