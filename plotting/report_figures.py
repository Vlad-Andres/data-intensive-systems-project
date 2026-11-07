"""
Report versions of plots, drawn at the size they are printed (ACM two-column: column 3.33 in, page 7 in) so the text
in them matches the report's font size. No titles inside the figures: the LaTeX caption says what they show.
Drawn from the saved CSVs, so nothing is re-run:

    uv run python -m plotting.report_figures      -> report_figures/measures_databasex3.png, greedy_pick_order_databasex7.png
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from plotting.plot_measures import MEASURES, SCORE_COLORMAP, ranks
from plotting.plot_reduction import DROPPED_ANSWERS, GRID, INK, KEPT_ANSWERS, MUTED_INK

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
REPORT_FOLDER = PROJECT_DIRECTORY / "report_figures"
COLUMN_WIDTH, PAGE_WIDTH = 3.33, 7.0  # inches
FONT = 7


def read_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save(figure, name: str) -> None:
    figure.savefig(REPORT_FOLDER / name, dpi=300, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved report_figures/{name}")


def measures_wide(csv_path: Path, name: str) -> None:
    """The three measures as rows, every graph as a column (ordered by its best rank): fits one page width, 1.5 in tall."""
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
    axes.tick_params(length=0, pad=2)
    for spine in axes.spines.values():
        spine.set_visible(False)
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
    axes.set_yticks(positions, [f"graph {g}" for g in shown], fontsize=FONT - 0.5, color=INK)
    axes.invert_yaxis()
    axes.set_xlim(0, max(scores.values()) * 1.45)
    axes.set_xlabel("distributed importance score", fontsize=FONT, color=MUTED_INK, labelpad=2)
    axes.xaxis.grid(True, color=GRID, linewidth=0.6)
    axes.set_axisbelow(True)
    axes.tick_params(length=0, labelsize=FONT - 1, labelcolor=MUTED_INK, pad=2)
    for spine in axes.spines.values():
        spine.set_visible(False)
    if any(g not in pick_order for g in shown):  # Only needed when some shown graphs were dropped.
        axes.legend(handles=[Patch(color=KEPT_ANSWERS, label="kept"), Patch(color=DROPPED_ANSWERS, label="dropped")],
                    loc="lower right", frameon=False, fontsize=FONT - 1, labelcolor=MUTED_INK)
    save(figure, name)


if __name__ == "__main__":
    measures_wide(PROJECT_DIRECTORY / "plots" / "measures" / "DatabaseX_3_QLog3_3.csv", "measures_databasex3.png")
    pick_order_compact(PROJECT_DIRECTORY / "plots" / "runs" / "Database7_2_distributed_query_coverage_rounds_selection_keep_0.02",
                       "greedy_pick_order_databasex7.png")
