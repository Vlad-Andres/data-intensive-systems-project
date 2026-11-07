"""
Compare the reduction methods across databases, query logs and keep shares B, after examples/08_compare_methods.sh has made
the reductions, e.g.:
    uv run python -m plotting.plot_method_comparison --databases 5 6 7 8 --keeps 0.01 0.02 0.05 0.1

Metrics (see plotting/coverage_metrics.py), on the past (first half) and the future (second half) of every query log:
  exact coverage - % of query lines that at least one kept graph fully answers;
  closeness      - per query line the best closeness of a kept graph, averaged; near answers count partly.

Saves in plots/comparison/:
  keep_<B>/DatabaseX_<n>.png  per database: methods x the 4 query logs, exact and closeness panels (bars = future, line = past)
  keep_curve.png              future exact coverage and closeness against B, per query log type, averaged over the databases
  timings.png                 reduction time per method and database (from plots/runs/<run>/timings.json)
  results.csv                 every number
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from plotting.coverage_metrics import METRICS, ClosenessIndex
from graph_parser import read_graph_database  # noqa: E402  (src/ is on the path through plotting.coverage_metrics)

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
COMPARISON_FOLDER = PROJECT_DIRECTORY / "plots" / "comparison"

# (label, part of the reduction file name written by main.py, with graph similarity?, colour)
METHODS = [
    ("naive", "full_query_coverage_simple_selection", False, "#2a78d6"),
    ("greedy", "distributed_query_coverage_rounds_selection", False, "#eb6834"),
    ("greedy + similarity", "distributed_query_coverage_rounds_selection", True, "#1baf7a"),
]
RANDOM_LABEL, RANDOM_COLOR = "random", "#c9c8c3"
COLOR_BY_METHOD = {RANDOM_LABEL: RANDOM_COLOR, **{label: color for label, _, _, color in METHODS}}
QUERY_LOG_NAMES = {1: "QLog_1\npopularity", 2: "QLog_2\nshifting interest", 3: "QLog_3\ncomplex variables", 4: "QLog_4\nsub-queries"}
PANELS = {
    "exact": "Exact answers: query lines fully answered by a kept graph",
    "closeness": "Near answers count too: average best closeness (share of the query's parts a kept graph satisfies)",
}
INK, MUTED_INK, GRID = "#1f1f1e", "#5f5e5a", "#e4e3df"
LINE_STYLES = {
    RANDOM_LABEL: {"linewidth": 2, "linestyle": "--", "marker": "o", "markersize": 5},
    "naive": {"linewidth": 2, "marker": "o", "markersize": 5},
    "greedy + similarity": {"linewidth": 6, "alpha": 0.45, "marker": "s", "markersize": 9},
    "greedy": {"linewidth": 2, "marker": "o", "markersize": 5},
}


def reduction_file(database: int, query_log: int, file_part: str, keep: float, similarity_budget: float | None) -> Path:
    """Same name as main.py gives the reduced database; the run's plots are in plots/runs/<this name without .txt>/."""
    name = f"Database{database}_{query_log}_{file_part}_keep_{keep}"
    if similarity_budget is not None:
        name += f"_graph_similarity_{similarity_budget}"
    return PROJECT_DIRECTORY / "data" / "reductions" / f"{name}.txt"


def compare_database(database: int, keep: float, similarity_budget: float) -> list[dict]:
    """Past and future exact coverage and closeness of every method (and random) on the 4 query logs of one database."""
    database_file = PROJECT_DIRECTORY / "data" / f"DatabaseX_{database}.txt"
    database_lines = [line for line in database_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    graphs = read_graph_database(str(database_file))
    kept_count = int(len(graphs) * keep)  # Same budget as the selection in main.py.
    index = ClosenessIndex(graphs)

    results = []
    for query_log in QUERY_LOG_NAMES:
        log_lines = (PROJECT_DIRECTORY / "data" / f"QLog{database}_{query_log}.txt").read_text(encoding="utf-8").splitlines()
        half = len(log_lines) // 2  # Same split as main.py: first half = past, second half = future.
        past, future = index.of_lines(log_lines[:half]), index.of_lines(log_lines[half:])

        row = {"keep": keep, "database": database, "query_log": query_log, "method": RANDOM_LABEL}
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
            row = {"keep": keep, "database": database, "query_log": query_log, "method": label}
            for metric, (method_metric, _) in METRICS.items():
                row[f"past_{metric}"] = method_metric(past, kept)
                row[f"future_{metric}"] = method_metric(future, kept)
            results.append(row)
    return results


def style_percent_axes(axes) -> None:
    axes.set_ylim(0, 105)
    axes.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], fontsize=8, color=MUTED_INK)
    axes.yaxis.grid(True, color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)


def plot_database(database: int, results: list[dict], keep: float, output_path: Path) -> None:
    """Top: exact coverage, bottom: closeness. One group of bars per query log: bar = future, black line on the bar = past."""
    bars = [RANDOM_LABEL] + [label for label, _, _, _ in METHODS]
    bar_width = 0.8 / len(bars)
    figure, axes_by_metric = plt.subplots(2, 1, figsize=(9, 8), layout="constrained", sharex=True)
    for axes, (metric, panel_title) in zip(axes_by_metric, PANELS.items()):
        for group, query_log in enumerate(QUERY_LOG_NAMES):
            for position, label in enumerate(bars):
                row = next((r for r in results if r["query_log"] == query_log and r["method"] == label), None)
                if row is None:
                    continue
                x = group + (position - (len(bars) - 1) / 2) * bar_width
                axes.bar(x, row[f"future_{metric}"], width=bar_width * 0.85, color=COLOR_BY_METHOD[label])
                axes.plot([x - bar_width * 0.42, x + bar_width * 0.42], [row[f"past_{metric}"]] * 2, color=INK, linewidth=2)
        style_percent_axes(axes)
        axes.set_title(panel_title, loc="left", color=INK, fontsize=10)
    axes_by_metric[-1].set_xticks(range(len(QUERY_LOG_NAMES)), list(QUERY_LOG_NAMES.values()), fontsize=9, color=INK)
    figure.suptitle(f"DatabaseX_{database} · {keep:.0%} of the graphs kept", x=0.01, ha="left", color=INK, fontsize=12)
    figure.legend(
        handles=[Patch(color=COLOR_BY_METHOD[label], label=label) for label in bars]
        + [Line2D([], [], color=INK, linewidth=2, label="past (first half)")],
        loc="outside lower center", ncol=len(bars) + 1, frameon=False, fontsize=8, labelcolor=MUTED_INK,
        title="bars = future (second half)", title_fontsize=8,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {output_path.relative_to(PROJECT_DIRECTORY)}")


def plot_keep_curve(results: list[dict], keeps: list[float], output_path: Path) -> None:
    """Future exact coverage (top) and closeness (bottom) against B, one panel per query log type, averaged over the databases."""
    # Drawn in this order; greedy + similarity is wide and translucent underneath so the greedy line stays visible where they coincide.
    methods = [RANDOM_LABEL, "naive", "greedy + similarity", "greedy"]
    figure, axes_grid = plt.subplots(2, len(QUERY_LOG_NAMES), figsize=(13, 7), layout="constrained", sharex=True, sharey=True)
    for row_axes, metric in zip(axes_grid, PANELS):
        for axes, (query_log, log_name) in zip(row_axes, QUERY_LOG_NAMES.items()):
            for method in methods:
                points = []
                for keep in keeps:
                    values = [r[f"future_{metric}"] for r in results if r["keep"] == keep and r["query_log"] == query_log and r["method"] == method]
                    if values:
                        points.append((100 * keep, statistics.mean(values)))
                if points:
                    xs, ys = zip(*points)
                    axes.plot(xs, ys, **LINE_STYLES[method], color=COLOR_BY_METHOD[method])
            style_percent_axes(axes)
            axes.set_xscale("log")
            axes.set_xticks([100 * keep for keep in keeps], [f"{keep:.0%}" for keep in keeps], fontsize=8, color=MUTED_INK)
            axes.minorticks_off()
            if metric == "exact":
                axes.set_title(log_name.replace("\n", " · "), loc="left", color=INK, fontsize=10)
        row_axes[0].set_ylabel("future exact coverage" if metric == "exact" else "future closeness", color=MUTED_INK, fontsize=9)
    for axes in axes_grid[-1]:
        axes.set_xlabel("B = share of graphs kept", color=MUTED_INK, fontsize=9)
    figure.suptitle("Future (second half) coverage against the keep share B, averaged over the databases", x=0.01, ha="left", color=INK, fontsize=12)
    figure.legend(handles=[Line2D([], [], **LINE_STYLES[m], color=COLOR_BY_METHOD[m], label=m) for m in methods],
                  loc="outside lower center", ncol=len(methods), frameon=False, fontsize=9, labelcolor=MUTED_INK)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {output_path.relative_to(PROJECT_DIRECTORY)}")


def plot_timings(databases: list[int], keep: float, similarity_budget: float, output_path: Path) -> None:
    """Mean reduction time over the 4 query logs per method and database, read from plots/runs/<run>/timings.json."""
    seconds = {}
    graph_counts = {}
    for database in databases:
        for label, file_part, with_similarity, _ in METHODS:
            times = []
            for query_log in QUERY_LOG_NAMES:
                run = reduction_file(database, query_log, file_part, keep, similarity_budget if with_similarity else None).stem
                path = PROJECT_DIRECTORY / "plots" / "runs" / run / "timings.json"
                if path.exists():
                    timings = json.loads(path.read_text())
                    times.append(timings["reduction_seconds"])
                    graph_counts[database] = timings["graphs"]
            if times:
                seconds[(database, label)] = statistics.mean(times)
    if not seconds:
        print("No timings.json found in plots/runs/: run examples/08_compare_methods.sh first.")
        return

    labels = [label for label, _, _, _ in METHODS]
    bar_width = 0.8 / len(labels)
    figure, axes = plt.subplots(figsize=(9, 4.5), layout="constrained")
    for group, database in enumerate(databases):
        for position, label in enumerate(labels):
            if (database, label) in seconds:
                x = group + (position - (len(labels) - 1) / 2) * bar_width
                value = seconds[(database, label)]
                axes.bar(x, value, width=bar_width * 0.85, color=COLOR_BY_METHOD[label])
                axes.annotate(f"{value:.1f}s", (x, value), xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=7, color=MUTED_INK)
    axes.set_xticks(range(len(databases)), [f"DatabaseX_{d}\n({graph_counts.get(d, '?')} graphs)" for d in databases], fontsize=9, color=INK)
    axes.set_ylabel("seconds (mean over the 4 query logs)", color=MUTED_INK, fontsize=9)
    axes.yaxis.grid(True, color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(length=0, labelsize=8, labelcolor=MUTED_INK)
    for spine in axes.spines.values():
        spine.set_visible(False)
    axes.set_title(f"Reduction time with {keep:.0%} kept: match + scores + selection (+ similarity); Spark start-up and plots excluded",
                   loc="left", color=INK, fontsize=10)
    figure.legend(handles=[Patch(color=COLOR_BY_METHOD[label], label=label) for label in labels],
                  loc="outside lower center", ncol=len(labels), frameon=False, fontsize=8, labelcolor=MUTED_INK)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {output_path.relative_to(PROJECT_DIRECTORY)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare the reduction methods across databases, query logs and keep shares.")
    parser.add_argument("--databases", type=int, nargs="+", default=[5, 6, 7, 8], help="Database numbers to compare.")
    parser.add_argument("--keeps", type=float, nargs="+", default=[0.02], help="Shares of graphs kept, as passed to main.py --importance_threshold.")
    parser.add_argument("--similarity_budget", type=float, default=0.2, help="Similarity budget, as passed to main.py.")
    args = parser.parse_args()

    all_results = []
    for keep in args.keeps:
        for database in args.databases:
            results = compare_database(database, keep, args.similarity_budget)
            plot_database(database, results, keep, COMPARISON_FOLDER / f"keep_{keep}" / f"DatabaseX_{database}.png")
            all_results.extend(results)
    if len(args.keeps) > 1:
        plot_keep_curve(all_results, sorted(args.keeps), COMPARISON_FOLDER / "keep_curve.png")
    timing_keep = 0.02 if 0.02 in args.keeps else args.keeps[0]
    plot_timings(args.databases, timing_keep, args.similarity_budget, COMPARISON_FOLDER / "timings.png")

    COMPARISON_FOLDER.mkdir(parents=True, exist_ok=True)
    with open(COMPARISON_FOLDER / "results.csv", "w", newline="", encoding="utf-8") as results_file:
        columns = ["past_exact", "future_exact", "past_closeness", "future_closeness"]
        writer = csv.DictWriter(results_file, fieldnames=["keep", "database", "query_log", "method", *columns])
        writer.writeheader()
        writer.writerows({**row, **{column: f"{row[column]:.1f}" for column in columns}} for row in all_results)
    print(f"Saved {(COMPARISON_FOLDER / 'results.csv').relative_to(PROJECT_DIRECTORY)}")
