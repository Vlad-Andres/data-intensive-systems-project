"""
The methods on the baseline dataset (group 15's, filtered: peer-dataset-test/Dataset24_fixed/), after
plotting/baseline-comparison.sh has made the reductions. Computed into CSVs, drawn from them (redraw: plotting.replot):

  plots/baseline/results.csv, comparison.png  past and future exact coverage and closeness per B and method (and random)
  plots/baseline/timings.csv, timings.png     reduction time per B and method
  plots/baseline/query_log.csv/.png           how often each query of the filtered log is asked

    uv run python -m plotting.plot_baseline --keeps 0.01 0.02 0.05 0.1
    uv run python -m plotting.plot_baseline --replot
"""
import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from plotting.coverage_metrics import METRICS, ClosenessIndex
from plotting.plot_method_comparison import (
    COLOR_BY_METHOD, GRID, INK, METHODS, MUTED_INK, PANELS, PROJECT_DIRECTORY, RANDOM_LABEL, RESULT_COLUMNS,
    reduction_file, style_percent_axes, write_csv,
)
from plotting.plot_query_logs import draw_query_log
from graph_parser import read_graph_database  # noqa: E402  (src/ is on the path through plotting.coverage_metrics)

BASELINE_FOLDER = PROJECT_DIRECTORY / "plots" / "baseline"
GRAPH_FILE = PROJECT_DIRECTORY / "peer-dataset-test" / "Dataset24_fixed" / "Database15.txt"
QUERY_LOG_FILE = PROJECT_DIRECTORY / "peer-dataset-test" / "Dataset24_fixed" / "QLog15_1.txt"
DATABASE_NUMBER, QUERY_LOG_NUMBER = 15, 1  # From the name QLog15_1.txt, as main.py reads it.


def read_rows(path: Path, numeric: list[str]) -> list[dict]:
    import csv
    with open(path, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        row["keep"] = float(row["keep"])
        for column in numeric:
            row[column] = float(row[column])
    return rows


def compute(keeps: list[float], similarity_budget: float) -> None:
    database_lines = [line for line in GRAPH_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    graphs = read_graph_database(str(GRAPH_FILE))
    log_lines = QUERY_LOG_FILE.read_text(encoding="utf-8").splitlines()
    half = len(log_lines) // 2  # Same split as main.py: first half = past, second half = future.
    index = ClosenessIndex(graphs)
    past, future = index.of_lines(log_lines[:half]), index.of_lines(log_lines[half:])

    results, timings = [], []
    for keep in keeps:
        kept_count = int(len(graphs) * keep)
        row = {"keep": keep, "method": RANDOM_LABEL}
        for metric, (_, random_metric) in METRICS.items():
            row[f"past_{metric}"] = random_metric(past, len(graphs), kept_count)
            row[f"future_{metric}"] = random_metric(future, len(graphs), kept_count)
        results.append(row)
        for label, file_part, with_similarity, _ in METHODS:
            path = reduction_file(DATABASE_NUMBER, QUERY_LOG_NUMBER, file_part, keep, similarity_budget if with_similarity else None)
            if not path.exists():
                print(f"Missing {path.relative_to(PROJECT_DIRECTORY)}: run plotting/baseline-comparison.sh first.")
                continue
            kept_lines = set(path.read_text(encoding="utf-8").splitlines())
            kept = {graph_id for graph_id, line in enumerate(database_lines) if line in kept_lines}
            row = {"keep": keep, "method": label}
            for metric, (method_metric, _) in METRICS.items():
                row[f"past_{metric}"] = method_metric(past, kept)
                row[f"future_{metric}"] = method_metric(future, kept)
            results.append(row)
            timing_file = PROJECT_DIRECTORY / "plots" / "runs" / path.stem / "timings.json"
            if timing_file.exists():
                timings.append({"keep": keep, "method": label, "reduction_seconds": f"{json.loads(timing_file.read_text())['reduction_seconds']:.3f}"})

    write_csv(BASELINE_FOLDER / "results.csv", ["keep", "method", *RESULT_COLUMNS],
              [{**row, **{column: f"{row[column]:.2f}" for column in RESULT_COLUMNS}} for row in results])
    write_csv(BASELINE_FOLDER / "timings.csv", ["keep", "method", "reduction_seconds"], timings)
    lines = [line.strip() for line in log_lines if line.strip()]
    write_csv(BASELINE_FOLDER / "query_log.csv", ["query", "times_asked"],
              [{"query": query, "times_asked": count} for query, count in Counter(lines).most_common()])
    (BASELINE_FOLDER / "query_log.json").write_text(json.dumps({"title": f"Baseline query log {QUERY_LOG_FILE.stem} (group 15, filtered)"}))
    print(f"Saved {(BASELINE_FOLDER / 'results.csv').relative_to(PROJECT_DIRECTORY)}, timings.csv and query_log.csv")


def draw_comparison() -> None:
    """Top: exact coverage, bottom: closeness. One group of bars per B: bar = future, black line on the bar = past."""
    results = read_rows(BASELINE_FOLDER / "results.csv", RESULT_COLUMNS)
    keeps = sorted({row["keep"] for row in results})
    bars = [RANDOM_LABEL] + [label for label, _, _, _ in METHODS]
    bar_width = 0.8 / len(bars)
    figure, axes_by_metric = plt.subplots(2, 1, figsize=(9, 8), layout="constrained", sharex=True)
    for axes, (metric, panel_title) in zip(axes_by_metric, PANELS.items()):
        for group, keep in enumerate(keeps):
            for position, label in enumerate(bars):
                row = next((r for r in results if r["keep"] == keep and r["method"] == label), None)
                if row is None:
                    continue
                x = group + (position - (len(bars) - 1) / 2) * bar_width
                axes.bar(x, row[f"future_{metric}"], width=bar_width * 0.85, color=COLOR_BY_METHOD[label])
                axes.plot([x - bar_width * 0.42, x + bar_width * 0.42], [row[f"past_{metric}"]] * 2, color=INK, linewidth=2)
        style_percent_axes(axes)
        axes.set_title(panel_title, loc="left", color=INK, fontsize=10)
    axes_by_metric[-1].set_xticks(range(len(keeps)), [f"B = {keep:.0%}" for keep in keeps], fontsize=9, color=INK)
    figure.suptitle("Baseline dataset (group 15, filtered) · 3,370 graphs", x=0.01, ha="left", color=INK, fontsize=12)
    figure.legend(handles=[Patch(color=COLOR_BY_METHOD[label], label=label) for label in bars]
                  + [Line2D([], [], color=INK, linewidth=2, label="past (first half)")],
                  loc="outside lower center", ncol=len(bars) + 1, frameon=False, fontsize=8, labelcolor=MUTED_INK,
                  title="bars = future (second half)", title_fontsize=8)
    figure.savefig(BASELINE_FOLDER / "comparison.png", dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {(BASELINE_FOLDER / 'comparison.png').relative_to(PROJECT_DIRECTORY)}")


def draw_timings() -> None:
    rows = read_rows(BASELINE_FOLDER / "timings.csv", ["reduction_seconds"])
    if not rows:
        return
    keeps = sorted({row["keep"] for row in rows})
    labels = [label for label, _, _, _ in METHODS]
    bar_width = 0.8 / len(labels)
    figure, axes = plt.subplots(figsize=(9, 4.5), layout="constrained")
    for group, keep in enumerate(keeps):
        for position, label in enumerate(labels):
            values = [row["reduction_seconds"] for row in rows if row["keep"] == keep and row["method"] == label]
            if values:
                x = group + (position - (len(labels) - 1) / 2) * bar_width
                value = statistics.mean(values)
                axes.bar(x, value, width=bar_width * 0.85, color=COLOR_BY_METHOD[label])
                axes.annotate(f"{value:.1f}s", (x, value), xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=7, color=MUTED_INK)
    axes.set_xticks(range(len(keeps)), [f"B = {keep:.0%}" for keep in keeps], fontsize=9, color=INK)
    axes.set_ylabel("seconds", color=MUTED_INK, fontsize=9)
    axes.yaxis.grid(True, color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(length=0, labelsize=8, labelcolor=MUTED_INK)
    for spine in axes.spines.values():
        spine.set_visible(False)
    axes.set_title("Baseline reduction time (3,370 graphs): match + scores + selection (+ graph similarity); Spark start-up and plots excluded",
                   loc="left", color=INK, fontsize=10)
    figure.legend(handles=[Patch(color=COLOR_BY_METHOD[label], label=label) for label in labels],
                  loc="outside lower center", ncol=len(labels), frameon=False, fontsize=8, labelcolor=MUTED_INK)
    figure.savefig(BASELINE_FOLDER / "timings.png", dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {(BASELINE_FOLDER / 'timings.png').relative_to(PROJECT_DIRECTORY)}")


def draw_all() -> None:
    draw_comparison()
    draw_timings()
    draw_query_log(BASELINE_FOLDER / "query_log")
    print(f"Saved {(BASELINE_FOLDER / 'query_log.png').relative_to(PROJECT_DIRECTORY)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The reduction methods on the baseline dataset.")
    parser.add_argument("--keeps", type=float, nargs="+", default=[0.01, 0.02, 0.05, 0.1], help="Shares of graphs kept.")
    parser.add_argument("--similarity_budget", type=float, default=0.2, help="Graph similarity budget.")
    parser.add_argument("--replot", action="store_true", help="Only redraw from the saved CSVs.")
    args = parser.parse_args()
    if not args.replot:
        compute(args.keeps, args.similarity_budget)
    draw_all()
