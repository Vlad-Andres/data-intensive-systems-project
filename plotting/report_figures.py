"""
Report versions of the plots, drawn at the size they are printed (ACM two-column: column 3.33 in, page 7 in) so the text
in them matches the report's font size. No titles inside the figures: the LaTeX caption says what they show.
Drawn from the CSVs the other plotting scripts saved, so nothing is re-run:

    uv run python -m plotting.report_figures      -> report_figures/*.png (except the Lucid diagram crops)
"""
import csv
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from plotting.plot_measures import MEASURES, SCORE_COLORMAP, ranks
from plotting.plot_method_comparison import COLOR_BY_METHOD, LINE_STYLES, METHODS, RANDOM_LABEL
from plotting.plot_query_logs import LOG_TYPES
from plotting.plot_reduction import DROPPED_ANSWERS, GRID, INK, KEPT_ANSWERS, MUTED_INK

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
PLOTS = PROJECT_DIRECTORY / "plots"
REPORT_FOLDER = PROJECT_DIRECTORY / "report_figures"
COLUMN_WIDTH, PAGE_WIDTH = 3.33, 7.0  # inches
FONT = 7
METHOD_LABELS = [label for label, _, _, _ in METHODS]
BARS = [RANDOM_LABEL] + METHOD_LABELS
LOG_NAMES = {1: "QLog_1 popularity", 2: "QLog_2 shifting interest", 3: "QLog_3 complex variables", 4: "QLog_4 sub-queries"}
WORKED_RUN = PLOTS / "runs" / "Database4_4_distributed_query_coverage_rounds_selection_keep_0.2"
PICK_ORDER_RUN = PLOTS / "runs" / "Database7_2_distributed_query_coverage_rounds_selection_keep_0.02"
COVERAGE_COLORMAP = LinearSegmentedColormap.from_list("coverage", ["#eef4fc", "#b7d3f6", "#5b9ae6", "#1c5cab", "#0d366b"])


# ----------------------------------------------------------------------------------------------------------- helpers

def read_rows(path: Path, numeric: tuple[str, ...] = ()) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        for column in numeric:
            row[column] = float(row[column])
    return rows


def save(figure, name: str) -> None:
    figure.savefig(REPORT_FOLDER / name, dpi=300, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved report_figures/{name}")


def clean(axes, grid_axis: str = "y") -> None:
    """Recessive axes: no spines, no ticks, light grid on one axis."""
    for spine in axes.spines.values():
        spine.set_visible(False)
    axes.tick_params(length=0, labelsize=FONT - 1, labelcolor=MUTED_INK, pad=2)
    if grid_axis:
        getattr(axes, f"{grid_axis}axis").grid(True, color=GRID, linewidth=0.6)
    axes.set_axisbelow(True)


def percent_axis(axes) -> None:
    axes.set_ylim(0, 105)
    axes.set_yticks([0, 50, 100], ["0%", "50%", "100%"])


def mean(rows: list[dict], column: str, **match) -> float | None:
    values = [row[column] for row in rows if all(row[key] == value for key, value in match.items())]
    return statistics.mean(values) if values else None


def method_legend(figure, labels: list[str], with_past: bool = False, lines: bool = False, columns: int | None = None) -> None:
    """One legend row above the plot: colour = method (bars or lines), optional black tick = past."""
    if lines:
        handles = [Line2D([], [], **{**LINE_STYLES[label], "linewidth": min(LINE_STYLES[label]["linewidth"], 4), "markersize": 3},
                          color=COLOR_BY_METHOD[label], label=label) for label in labels]
    else:
        handles = [Patch(color=COLOR_BY_METHOD[label], label=label) for label in labels]
    if with_past:
        handles.append(Line2D([], [], color=INK, linewidth=1.2, label="past"))
    figure.legend(handles=handles, loc="outside upper center", ncol=columns or len(handles), frameon=False, fontsize=FONT - 1,
                  labelcolor=MUTED_INK, handlelength=1.6 if not lines else 2.6, handletextpad=0.8 if lines else 0.4, columnspacing=1.4)


def grouped_bars(axes, groups: list, rows_for, metric: str) -> None:
    """One group of bars per entry of groups (random + the methods): bar = future, short black line = past."""
    width = 0.8 / len(BARS)
    for group_index, group in enumerate(groups):
        for position, label in enumerate(BARS):
            row = rows_for(group, label)
            if row is None:
                continue
            x = group_index + (position - (len(BARS) - 1) / 2) * width
            axes.bar(x, row[f"future_{metric}"], width=width * 0.85, color=COLOR_BY_METHOD[label])
            axes.plot([x - width * 0.42, x + width * 0.42], [row[f"past_{metric}"]] * 2, color=INK, linewidth=1)


RESULT_NUMBERS = ("past_exact", "future_exact", "past_closeness", "future_closeness")


def read_results(path: Path, extra: tuple[str, ...] = ()) -> list[dict]:
    rows = read_rows(path, RESULT_NUMBERS + ("keep",) + extra)
    for row in rows:
        for column in ("database", "query_log"):
            if column in row:
                row[column] = int(row[column])
    return rows


# ------------------------------------------------------------------------------------------------------------ theory

def measures_wide(csv_path: Path, name: str) -> None:
    """The three measures as rows, every graph as a column (ordered by its best rank): one page wide, 1.5 in tall."""
    rows = read_rows(csv_path)
    scores_by_measure = {measure: {int(row["graph_id"]): float(row[measure]) for row in rows} for measure in MEASURES}
    rank_by_measure = {measure: ranks(scores) for measure, scores in scores_by_measure.items()}
    graph_ids = sorted(scores_by_measure["full"], key=lambda g: (min(rank_by_measure[m][g] for m in MEASURES), g))
    scores = np.array([[scores_by_measure[m][g] for g in graph_ids] for m in MEASURES])
    row_max = scores.max(axis=1, keepdims=True)
    relative = np.divide(scores, row_max, out=np.zeros_like(scores), where=row_max > 0)

    figure, axes = plt.subplots(figsize=(PAGE_WIDTH, 1.45), layout="constrained")
    axes.imshow(relative, cmap=SCORE_COLORMAP, vmin=0, vmax=1, aspect="auto")
    for row, measure in enumerate(MEASURES):
        for column, graph_id in enumerate(graph_ids):
            score = scores[row, column]
            axes.text(column, row, f"{score:.3g}\n#{rank_by_measure[measure][graph_id]}", ha="center", va="center", fontsize=FONT - 1.5,
                      linespacing=1.1, color="#ffffff" if relative[row, column] > 0.55 else INK)
    axes.set_xticks(range(len(graph_ids)), [str(g) for g in graph_ids], fontsize=FONT, color=INK)
    axes.xaxis.tick_top()
    axes.set_xlabel("graph", fontsize=FONT, color=MUTED_INK, labelpad=2)
    axes.xaxis.set_label_position("top")
    axes.set_yticks(range(len(MEASURES)), list(MEASURES), fontsize=FONT, color=INK)
    clean(axes, grid_axis="")
    axes.tick_params(labelcolor=INK, labelsize=FONT)
    save(figure, name)


def pick_order_compact(run_folder: Path, name: str, shown_count: int = 14) -> None:
    """The highest distributed scores of one greedy run, kept graphs labelled with their pick order: one column wide."""
    rows = read_rows(run_folder / "2_scores" / "graph_scores.csv")
    scores = {int(row["graph_id"]): float(row["score"]) for row in rows}
    pick_order = {int(row["graph_id"]): int(row["pick_order"]) for row in rows if row["pick_order"]}
    shown = sorted(scores, key=lambda g: (-scores[g], g))[:shown_count]

    figure, axes = plt.subplots(figsize=(COLUMN_WIDTH, 0.55 + 0.16 * len(shown)), layout="constrained")
    positions = np.arange(len(shown))
    axes.barh(positions, [scores[g] for g in shown], height=0.7, color=[KEPT_ANSWERS if g in pick_order else DROPPED_ANSWERS for g in shown])
    for position, graph_id in zip(positions, shown):
        label = f"{scores[graph_id]:.3g}" + (f"  picked #{pick_order[graph_id]}" if graph_id in pick_order else "")
        axes.annotate(label, (scores[graph_id], position), xytext=(3, 0), textcoords="offset points", va="center", fontsize=FONT - 1, color=MUTED_INK)
    axes.set_yticks(positions, [f"graph {g}" for g in shown])
    axes.invert_yaxis()
    axes.set_xlim(0, max(scores.values()) * 1.45)
    axes.set_xlabel("distributed importance score", fontsize=FONT, color=MUTED_INK, labelpad=2)
    clean(axes, grid_axis="x")
    axes.tick_params(axis="y", labelcolor=INK)
    if any(g not in pick_order for g in shown):  # Only needed when some shown graphs were dropped.
        axes.legend(handles=[Patch(color=KEPT_ANSWERS, label="kept"), Patch(color=DROPPED_ANSWERS, label="dropped")],
                    loc="lower right", frameon=False, fontsize=FONT - 1, labelcolor=MUTED_INK)
    save(figure, name)


# ------------------------------------------------------------------------------------------------------- query logs

def bell(counts: list[int]) -> list[int]:
    """Most asked in the middle, the others alternating to both sides (as in plotting/plot_query_logs.py)."""
    counts = sorted(counts, reverse=True)
    return counts[1::2][::-1] + counts[0::2]


def query_log_strip(name: str) -> None:
    """The four query log types side by side (DatabaseX_7), one page wide."""
    figure, axes_row = plt.subplots(1, 4, figsize=(PAGE_WIDTH, 1.35), layout="constrained")
    for axes, (log_type, log_name) in zip(axes_row, LOG_TYPES.items()):
        counts = [int(row["times_asked"]) for row in read_rows(PLOTS / "q_logs" / f"QLog_{log_type}_{log_name.replace(' ', '_')}.csv")]
        axes.bar(range(len(counts)), bell(counts), color=KEPT_ANSWERS, width=0.8)
        axes.set_title(f"QLog_{log_type} {log_name}\n{sum(counts)} lines, {len(counts)} distinct", loc="left", fontsize=FONT, color=INK, pad=3)
        axes.set_xticks([])
        clean(axes)
        axes.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True, nbins=4))
    axes_row[0].set_ylabel("times asked", fontsize=FONT, color=MUTED_INK)
    save(figure, "qlog_distributions.png")


def baseline_query_log() -> None:
    counts = [int(row["times_asked"]) for row in read_rows(PLOTS / "baseline" / "query_log.csv")]
    figure, axes = plt.subplots(figsize=(COLUMN_WIDTH, 1.3), layout="constrained")
    axes.bar(range(len(counts)), bell(counts), color=KEPT_ANSWERS, width=1.0)
    axes.set_xticks([])
    axes.set_xlabel(f"{len(counts):,} distinct queries, most asked in the middle", fontsize=FONT, color=MUTED_INK, labelpad=2)
    axes.set_ylabel("times asked", fontsize=FONT, color=MUTED_INK)
    clean(axes)
    save(figure, "baseline_query_log.png")


# --------------------------------------------------------------------------------------------------- worked example

def short_query(query: str, width: int = 60) -> str:
    query = query.replace('"', "")
    return query if len(query) <= width else query[:width - 1] + "…"


def worked_example_selection() -> None:
    """
    Match, scores and selection of the worked example in one table: rows = past queries, columns = the graphs that fully
    answer at least one of them (kept in pick order, then dropped), cell = share of the query the graph satisfies,
    right = whether a kept graph still fully answers the query.
    """
    coverage = {(row["query"], int(row["graph_id"])): float(row["coverage"]) for row in read_rows(WORKED_RUN / "1_match" / "coverage_table.csv")}
    score_rows = read_rows(WORKED_RUN / "2_scores" / "graph_scores.csv")
    scores = {int(row["graph_id"]): float(row["score"]) for row in score_rows}
    pick_order = {int(row["graph_id"]): int(row["pick_order"]) for row in score_rows if row["pick_order"]}
    queries = [row["query"] for row in read_rows(WORKED_RUN / "queries.csv")]
    answering = {g for (_, g), value in coverage.items() if value == 1.0}
    kept = sorted(pick_order, key=pick_order.get)
    dropped = sorted(answering - set(kept), key=lambda g: (-scores[g], g))
    columns = kept + dropped
    # Queries grouped by the first kept graph that answers them, the lost ones last.
    def first_answer(query: str) -> int:
        return next((i for i, g in enumerate(kept) if coverage.get((query, g)) == 1.0), len(kept))
    queries.sort(key=lambda q: (first_answer(q), q))

    values = np.array([[coverage.get((q, g), 0.0) for g in columns] for q in queries])
    figure, axes = plt.subplots(figsize=(PAGE_WIDTH, 0.75 + 0.115 * len(queries)), layout="constrained")
    axes.imshow(np.ma.masked_equal(values, 0), cmap=COVERAGE_COLORMAP, vmin=0, vmax=1, aspect="auto")
    for row, query in enumerate(queries):
        for column, graph_id in enumerate(columns):
            value = values[row, column]
            if value:
                axes.text(column, row, f"{value:.2g}", ha="center", va="center", fontsize=FONT - 2,
                          color="#ffffff" if value > 0.6 else INK)
        answered = first_answer(query) < len(kept)
        axes.text(len(columns) - 0.3, row, "✓" if answered else "✗ lost", ha="left", va="center", fontsize=FONT - 1,
                  color=KEPT_ANSWERS if answered else "#b3261e")
    axes.axvline(len(kept) - 0.5, color=INK, linewidth=1)
    header = [f"graph {g}\n{scores[g]:.3g}\n#{pick_order[g]}" if g in pick_order else f"graph {g}\n{scores[g]:.3g}\ndropped" for g in columns]
    axes.set_xticks(range(len(columns)), header, fontsize=FONT - 1, color=INK, linespacing=1.15)
    axes.xaxis.tick_top()
    axes.set_yticks(range(len(queries)), [short_query(q) for q in queries], fontsize=FONT - 1.5, color=INK)
    axes.set_xlim(-0.5, len(columns) + 0.5)
    axes.text(-0.5, -0.5, "graph · distributed score · pick order", transform=axes.transData, ha="right", va="bottom",
              fontsize=FONT - 1.5, color=MUTED_INK)
    clean(axes, grid_axis="")
    axes.tick_params(labelcolor=INK)
    save(figure, "worked_example_selection.png")


def worked_example_evaluation() -> None:
    rows = read_rows(WORKED_RUN / "4_evaluation" / "coverage.csv", ("exact", "closeness", "random_exact", "random_closeness"))
    labels = {"past (first half)": "past", "QLog4_4 second half": "future"}
    figure, axes = plt.subplots(figsize=(COLUMN_WIDTH, 1.55), layout="constrained")
    width = 0.38
    for index, row in enumerate(rows):
        for offset, metric, color in ((-width / 2, "exact", KEPT_ANSWERS), (width / 2, "closeness", "#86b6ef")):
            x = index + offset
            axes.bar(x, row[metric], width=width * 0.9, color=color)
            axes.plot([x - width * 0.45, x + width * 0.45], [row[f"random_{metric}"]] * 2, color=INK, linewidth=1)
    axes.set_xticks(range(len(rows)), [labels.get(row["query_set"], row["query_set"]) for row in rows], fontsize=FONT - 0.5, color=INK)
    percent_axis(axes)
    clean(axes)
    figure.legend(handles=[Patch(color=KEPT_ANSWERS, label="exact coverage"), Patch(color="#86b6ef", label="closeness"),
                           Line2D([], [], color=INK, linewidth=1, label="random, same size")],
                  loc="outside upper center", ncol=3, frameon=False, fontsize=FONT - 1, labelcolor=MUTED_INK, handlelength=1.6)
    save(figure, "worked_example_evaluation.png")


# ------------------------------------------------------------------------------------------------------- comparisons

def keep_curve(rows: list[dict], name: str, metrics: tuple[str, ...]) -> None:
    """Future coverage against B per query log type, averaged over the databases: one page wide."""
    keeps = sorted({row["keep"] for row in rows})
    order = [RANDOM_LABEL, "naive", "greedy + graph similarity", "greedy"]  # greedy + graph similarity wide underneath
    figure, axes_grid = plt.subplots(len(metrics), 4, figsize=(PAGE_WIDTH, 0.55 + 1.15 * len(metrics)), layout="constrained",
                                     sharex=True, sharey=True, squeeze=False)
    for row_axes, metric in zip(axes_grid, metrics):
        for axes, (query_log, log_name) in zip(row_axes, LOG_NAMES.items()):
            for method in order:
                points = [(100 * keep, mean(rows, f"future_{metric}", keep=keep, query_log=query_log, method=method)) for keep in keeps]
                points = [(x, y) for x, y in points if y is not None]
                if points:
                    style = {**LINE_STYLES[method], "linewidth": LINE_STYLES[method]["linewidth"] * 0.6, "markersize": 3}
                    axes.plot(*zip(*points), **style, color=COLOR_BY_METHOD[method])
            percent_axis(axes)
            clean(axes)
            axes.set_xscale("log")
            axes.set_xticks([100 * keep for keep in keeps], [f"{keep:.0%}" for keep in keeps])
            axes.minorticks_off()
            if metric == metrics[0]:
                axes.set_title(log_name, loc="left", fontsize=FONT, color=INK, pad=3)
        row_axes[0].set_ylabel(f"future {'exact coverage' if metric == 'exact' else 'closeness'}", fontsize=FONT, color=MUTED_INK)
    figure.supxlabel("B (share of graphs kept)", fontsize=FONT, color=MUTED_INK)
    method_legend(figure, order, lines=True)
    save(figure, name)


def bars_per_query_log(panels: list[tuple[str, list[dict], str]], name: str) -> None:
    """One column wide: per panel, one group of bars per query log type (random + methods; bar = future, line = past)."""
    figure, axes_list = plt.subplots(len(panels), 1, figsize=(COLUMN_WIDTH, 0.45 + 1.1 * len(panels)), layout="constrained", sharex=True)
    for axes, (panel_title, rows, metric) in zip(np.atleast_1d(axes_list), panels):
        grouped_bars(axes, list(LOG_NAMES), lambda query_log, label: next(
            ({**r} for r in rows if r["query_log"] == query_log and r["method"] == label), None), metric)
        percent_axis(axes)
        clean(axes)
        axes.set_title(panel_title, loc="left", fontsize=FONT, color=INK, pad=2)
    np.atleast_1d(axes_list)[-1].set_xticks(range(4), [f"QLog_{n}" for n in LOG_NAMES], fontsize=FONT, color=INK)
    method_legend(figure, BARS, with_past=True, columns=3)
    save(figure, name)


def small_databases(rows: list[dict]) -> None:
    """Future and past exact coverage per query log type, averaged over DatabaseX_1-4, one panel per B."""
    averaged = []
    for keep in sorted({row["keep"] for row in rows}):
        for query_log in LOG_NAMES:
            for label in BARS:
                averaged.append({"keep": keep, "query_log": query_log, "method": label,
                                 **{column: mean(rows, column, keep=keep, query_log=query_log, method=label) for column in RESULT_NUMBERS}})
    keeps = sorted({row["keep"] for row in rows})
    bars_per_query_log([(f"B = {keep:.0%} ({round(20 * keep)} of 20 graphs): exact coverage",
                         [r for r in averaged if r["keep"] == keep], "exact") for keep in keeps], "small_databases.png")


def similarity_budget() -> None:
    rows = read_results(PLOTS / "comparison" / "similarity_budget" / "results.csv", ("budget",))
    budgets = sorted({row["budget"] for row in rows})
    keeps = sorted({row["keep"] for row in rows})
    colors = ["#2a78d6", "#eb6834"]
    figure, axes_row = plt.subplots(1, 4, figsize=(PAGE_WIDTH, 1.75), layout="constrained", sharey=True)
    for axes, (query_log, log_name) in zip(axes_row, LOG_NAMES.items()):
        for color, keep in zip(colors, keeps):
            for phase, linestyle in (("past", "--"), ("future", "-")):
                points = [(i, mean(rows, f"{phase}_exact", keep=keep, query_log=query_log, budget=b)) for i, b in enumerate(budgets)]
                axes.plot(*zip(*points), color=color, linestyle=linestyle, linewidth=1.2, marker="o", markersize=2.5)
        percent_axis(axes)
        clean(axes)
        axes.set_xticks(range(len(budgets)), ["0" if b == 0 else f"{b:g}" for b in budgets])
        axes.set_title(log_name, loc="left", fontsize=FONT, color=INK, pad=3)
    figure.supxlabel("graph similarity budget s (0 = greedy alone)", fontsize=FONT, color=MUTED_INK)
    axes_row[0].set_ylabel("exact coverage", fontsize=FONT, color=MUTED_INK)
    handles = [Line2D([], [], color=c, linewidth=2, label=f"B = {k:.0%}") for c, k in zip(colors, keeps)]
    handles += [Line2D([], [], color=MUTED_INK, linewidth=1.2, label="future"), Line2D([], [], color=MUTED_INK, linewidth=1.2, linestyle="--", label="past")]
    figure.legend(handles=handles, loc="outside upper center", ncol=4, frameon=False, fontsize=FONT - 1, labelcolor=MUTED_INK, handlelength=2.6)
    save(figure, "similarity_budget.png")


def timing_bars(groups: list[str], value_for, name: str, height: float) -> None:
    """One column wide: reduction seconds per group, one bar per method, value on top."""
    width = 0.8 / len(METHOD_LABELS)
    figure, axes = plt.subplots(figsize=(COLUMN_WIDTH, height), layout="constrained")
    top = 0
    for group_index, group in enumerate(groups):
        for position, label in enumerate(METHOD_LABELS):
            value = value_for(group, label)
            if value is None:
                continue
            x = group_index + (position - (len(METHOD_LABELS) - 1) / 2) * width
            axes.bar(x, value, width=width * 0.85, color=COLOR_BY_METHOD[label])
            axes.annotate(f"{value:.0f}" if value >= 10 else f"{value:.1f}", (x, value), xytext=(0, 1), textcoords="offset points",
                          ha="center", va="bottom", fontsize=FONT - 2, color=MUTED_INK)
            top = max(top, value)
    axes.set_ylim(0, top * 1.18)
    axes.set_xticks(range(len(groups)), groups, fontsize=FONT - 0.5, color=INK)
    axes.set_ylabel("seconds", fontsize=FONT, color=MUTED_INK)
    clean(axes)
    method_legend(figure, METHOD_LABELS)
    save(figure, name)


def comparison_timings(keep: float = 0.02) -> None:
    rows = read_rows(PLOTS / "comparison" / "timings.csv", ("keep", "reduction_seconds"))
    databases = sorted({int(row["database"]) for row in rows})
    timing_bars([f"DatabaseX_{d}" for d in databases],
                lambda group, label: mean(rows, "reduction_seconds", keep=keep, database=group.split("_")[1], method=label),
                "comparison_timings.png", 1.5)


def baseline() -> None:
    rows = read_rows(PLOTS / "baseline" / "results.csv", RESULT_NUMBERS + ("keep",))
    keeps = sorted({row["keep"] for row in rows})
    figure, axes_list = plt.subplots(2, 1, figsize=(COLUMN_WIDTH, 2.6), layout="constrained", sharex=True)
    for axes, (metric, title) in zip(axes_list, (("exact", "exact coverage"), ("closeness", "closeness"))):
        grouped_bars(axes, keeps, lambda keep, label: next((r for r in rows if r["keep"] == keep and r["method"] == label), None), metric)
        percent_axis(axes)
        clean(axes)
        axes.set_title(title, loc="left", fontsize=FONT, color=INK, pad=2)
    axes_list[-1].set_xticks(range(len(keeps)), [f"B = {keep:.0%}" for keep in keeps], fontsize=FONT, color=INK)
    method_legend(figure, BARS, with_past=True, columns=3)
    save(figure, "baseline_comparison.png")

    timings = read_rows(PLOTS / "baseline" / "timings.csv", ("keep", "reduction_seconds"))
    timing_bars([f"B = {keep:.0%}" for keep in keeps],
                lambda group, label: mean(timings, "reduction_seconds", keep=keeps[[f"B = {k:.0%}" for k in keeps].index(group)], method=label),
                "baseline_timings.png", 1.4)


if __name__ == "__main__":
    measures_wide(PLOTS / "measures" / "DatabaseX_3_QLog3_3.csv", "measures_databasex3.png")
    pick_order_compact(PICK_ORDER_RUN, "greedy_pick_order_databasex7.png")
    query_log_strip("qlog_distributions.png")
    baseline_query_log()
    worked_example_selection()
    worked_example_evaluation()
    results = read_results(PLOTS / "comparison" / "results.csv")
    keep_curve(results, "comparison_keep_curve.png", ("exact", "closeness"))
    bars_per_query_log([("exact coverage", [r for r in results if r["database"] == 7 and r["keep"] == 0.01], "exact"),
                        ("closeness", [r for r in results if r["database"] == 7 and r["keep"] == 0.01], "closeness")],
                       "comparison_databasex7_keep1.png")
    small_databases(read_results(PLOTS / "comparison" / "small_databases" / "results.csv"))
    similarity_budget()
    comparison_timings()
    baseline()
