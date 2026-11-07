"""
Two extra comparisons, each computed into a CSV and drawn from it (redraw with: uv run python -m plotting.replot):

  small-databases     the methods on the small databases 1-4 (20 graphs) with larger keep shares B
                      -> plots/comparison/small_databases/results.csv, keep_<B>/DatabaseX_<n>.png, keep_curve.png
  similarity-budgets  greedy + graph similarity for several graph similarity budgets (0 = plain greedy)
                      -> plots/comparison/similarity_budget/results.csv, similarity_budget.png

Run through plotting/compare-small-databases.sh and plotting/compare-similarity-budgets.sh, or directly:
    uv run python -m plotting.plot_extra_comparisons small-databases --databases 1 2 3 4 --keeps 0.2 0.4
    uv run python -m plotting.plot_extra_comparisons similarity-budgets --databases 5 6 7 8 --keeps 0.01 0.02 --budgets 0 0.1 0.2 0.5 1.0
    uv run python -m plotting.plot_extra_comparisons similarity-budgets --replot
"""
import argparse
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from plotting.coverage_metrics import METRICS, ClosenessIndex
from plotting.plot_method_comparison import (
    COMPARISON_FOLDER, INK, MUTED_INK, PANELS, PROJECT_DIRECTORY, QUERY_LOG_NAMES, RESULT_COLUMNS,
    compare_database, plot_database, plot_keep_curve, read_csv, reduction_file, style_percent_axes, write_csv,
)
from graph_parser import read_graph_database  # noqa: E402  (src/ is on the path through plotting.coverage_metrics)

SMALL_FOLDER = COMPARISON_FOLDER / "small_databases"
BUDGET_FOLDER = COMPARISON_FOLDER / "similarity_budget"
GREEDY_FILE_PART = "distributed_query_coverage_rounds_selection"
KEEP_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]


def formatted(rows: list[dict]) -> list[dict]:
    return [{**row, **{column: f"{row[column]:.2f}" for column in RESULT_COLUMNS}} for row in rows]


# ----------------------------------------------------------------------------------------------------- small databases

def compute_small_databases(databases: list[int], keeps: list[float], similarity_budget: float) -> None:
    results = [row for keep in keeps for database in databases for row in compare_database(database, keep, similarity_budget)]
    write_csv(SMALL_FOLDER / "results.csv", ["keep", "database", "query_log", "method", *RESULT_COLUMNS], formatted(results))
    print(f"Saved {(SMALL_FOLDER / 'results.csv').relative_to(PROJECT_DIRECTORY)}")


def draw_small_databases() -> None:
    results = read_csv(SMALL_FOLDER / "results.csv", RESULT_COLUMNS)
    keeps = sorted({row["keep"] for row in results})
    for keep in keeps:
        for database in sorted({row["database"] for row in results if row["keep"] == keep}):
            plot_database(database, [r for r in results if r["keep"] == keep and r["database"] == database], keep,
                          SMALL_FOLDER / f"keep_{keep}" / f"DatabaseX_{database}.png")
    if len(keeps) > 1:
        plot_keep_curve(results, keeps, SMALL_FOLDER / "keep_curve.png")


# --------------------------------------------------------------------------------------------- graph similarity budgets

def compute_similarity_budgets(databases: list[int], keeps: list[float], budgets: list[float]) -> None:
    """Past and future metrics of greedy + graph similarity for every budget; budget 0 is the plain greedy run."""
    rows = []
    for database in databases:
        database_file = PROJECT_DIRECTORY / "data" / f"DatabaseX_{database}.txt"
        database_lines = [line for line in database_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        index = ClosenessIndex(read_graph_database(str(database_file)))
        for query_log in QUERY_LOG_NAMES:
            log_lines = (PROJECT_DIRECTORY / "data" / f"QLog{database}_{query_log}.txt").read_text(encoding="utf-8").splitlines()
            half = len(log_lines) // 2  # Same split as main.py: first half = past, second half = future.
            past, future = index.of_lines(log_lines[:half]), index.of_lines(log_lines[half:])
            for keep in keeps:
                for budget in budgets:
                    path = reduction_file(database, query_log, GREEDY_FILE_PART, keep, None if budget == 0 else budget)
                    if not path.exists():
                        print(f"Missing {path.relative_to(PROJECT_DIRECTORY)}: run plotting/compare-methods.sh and "
                              f"plotting/compare-similarity-budgets.sh first.")
                        continue
                    kept_lines = set(path.read_text(encoding="utf-8").splitlines())
                    kept = {graph_id for graph_id, line in enumerate(database_lines) if line in kept_lines}
                    row = {"keep": keep, "database": database, "query_log": query_log, "budget": budget}
                    for metric, (method_metric, _) in METRICS.items():
                        row[f"past_{metric}"] = method_metric(past, kept)
                        row[f"future_{metric}"] = method_metric(future, kept)
                    rows.append(row)
    write_csv(BUDGET_FOLDER / "results.csv", ["keep", "database", "query_log", "budget", *RESULT_COLUMNS], formatted(rows))
    print(f"Saved {(BUDGET_FOLDER / 'results.csv').relative_to(PROJECT_DIRECTORY)}")


def draw_similarity_budgets() -> None:
    """Past (dashed) and future (solid) coverage against the graph similarity budget, one colour per B, averaged over the databases."""
    rows = read_csv(BUDGET_FOLDER / "results.csv", [*RESULT_COLUMNS, "budget"])
    budgets = sorted({row["budget"] for row in rows})
    keeps = sorted({row["keep"] for row in rows})
    figure, axes_grid = plt.subplots(2, len(QUERY_LOG_NAMES), figsize=(13, 7), layout="constrained", sharex=True, sharey=True)
    for row_axes, metric in zip(axes_grid, PANELS):
        for axes, (query_log, log_name) in zip(row_axes, QUERY_LOG_NAMES.items()):
            for color, keep in zip(KEEP_COLORS, keeps):
                for phase, linestyle in (("past", "--"), ("future", "-")):
                    points = []
                    for budget in budgets:
                        values = [r[f"{phase}_{metric}"] for r in rows if r["keep"] == keep and r["query_log"] == query_log and r["budget"] == budget]
                        if values:
                            points.append((budget, statistics.mean(values)))
                    if points:
                        xs, ys = zip(*points)
                        axes.plot(xs, ys, color=color, linestyle=linestyle, linewidth=2, marker="o", markersize=5)
            style_percent_axes(axes)
            axes.set_xticks(budgets, ["0\ngreedy" if budget == 0 else f"{budget:g}" for budget in budgets], fontsize=8, color=MUTED_INK)
            if metric == "exact":
                axes.set_title(log_name.replace("\n", " · "), loc="left", color=INK, fontsize=10)
        row_axes[0].set_ylabel("exact coverage" if metric == "exact" else "closeness", color=MUTED_INK, fontsize=9)
    for axes in axes_grid[-1]:
        axes.set_xlabel("graph similarity budget", color=MUTED_INK, fontsize=9)
    figure.suptitle("Effect of the graph similarity budget (share of the kept slots refilled by most new facts), averaged over the databases",
                    x=0.01, ha="left", color=INK, fontsize=12)
    # Colour = B, line style = past or future.
    handles = [Line2D([], [], color=color, linewidth=3, label=f"B = {keep:.0%}") for color, keep in zip(KEEP_COLORS, keeps)]
    handles += [Line2D([], [], color=MUTED_INK, linewidth=2, linestyle="-", label="future (second half)"),
                Line2D([], [], color=MUTED_INK, linewidth=2, linestyle="--", label="past (first half)")]
    figure.legend(handles=handles, loc="outside lower center", ncol=len(handles), frameon=False, fontsize=9, labelcolor=MUTED_INK,
                  handlelength=3.5)
    BUDGET_FOLDER.mkdir(parents=True, exist_ok=True)
    output_path = BUDGET_FOLDER / "similarity_budget.png"
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {output_path.relative_to(PROJECT_DIRECTORY)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extra comparisons: small databases and graph similarity budgets.")
    parser.add_argument("comparison", choices=["small-databases", "similarity-budgets"])
    parser.add_argument("--databases", type=int, nargs="+", help="Database numbers.")
    parser.add_argument("--keeps", type=float, nargs="+", help="Shares of graphs kept.")
    parser.add_argument("--budgets", type=float, nargs="+", default=[0, 0.1, 0.2, 0.5, 1.0], help="Graph similarity budgets (0 = plain greedy).")
    parser.add_argument("--similarity_budget", type=float, default=0.2, help="Graph similarity budget of the small-database comparison.")
    parser.add_argument("--replot", action="store_true", help="Only redraw from the saved results.csv.")
    args = parser.parse_args()

    if args.comparison == "small-databases":
        if not args.replot:
            compute_small_databases(args.databases or [1, 2, 3, 4], args.keeps or [0.2, 0.4], args.similarity_budget)
        draw_small_databases()
    else:
        if not args.replot:
            compute_similarity_budgets(args.databases or [5, 6, 7, 8], args.keeps or [0.01, 0.02], sorted(set(args.budgets)))
        draw_similarity_budgets()
