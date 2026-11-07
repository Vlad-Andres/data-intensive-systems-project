import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window that would pause the run.

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.patches import Patch, Rectangle
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from graph_parser import read_graph_database  # noqa: E402
from QLog_satisfaction import graph_satisfies_query, parse_query  # noqa: E402

# Hue = kept (blue) or dropped (gray); darker = the graph answers a query.
KEPT_ANSWERS, KEPT_NOTHING = "#256abf", "#b7d3f6"
DROPPED_ANSWERS, DROPPED_NOTHING = "#8a8984", "#e4e3df"
INK, MUTED_INK = "#1f1f1e", "#5f5e5a"


def save_reduction_plots(
    graphs_matches: DataFrame,
    query_lines: list[str],
    all_graph_ids: list[int],
    selected_graph_ids: list[int],
    output_folder: str,
    title: str,
) -> None:
    """
    Save two plots of a reduction in output_folder:
      answered_queries.png - which queries the reduced database still answers, weighted by how often they are asked;
      kept_graphs.png      - one square per graph of the database: kept or dropped, and whether it answers a query.

    Args:
        graphs_matches: DataFrame with graph_id, query_id and query_coverage, query_id being the line index in query_lines.
        query_lines: The lines of the query log that was matched.
        all_graph_ids: Every graph of the database.
        selected_graph_ids: The kept graphs, in pick order.
        output_folder: Folder to save the plots in.
        title: Title shown above the plots.
    """
    query_by_line = {line_index: line.strip() for line_index, line in enumerate(query_lines) if line.strip()}
    queries_answered_by_graph = defaultdict(set)
    for row in graphs_matches.where(F.col("query_coverage") == 1.0).select("graph_id", "query_id").collect():
        queries_answered_by_graph[row["graph_id"]].add(query_by_line[row["query_id"]])

    Path(output_folder).mkdir(parents=True, exist_ok=True)
    plot_answered_queries(Counter(query_by_line.values()), queries_answered_by_graph, selected_graph_ids, title,
                          Path(output_folder) / "answered_queries.png")
    plot_kept_graphs(all_graph_ids, queries_answered_by_graph, set(selected_graph_ids), title,
                     Path(output_folder) / "kept_graphs.png")
    print(f"\nPlots saved in {output_folder}")


def plot_answered_queries(times_asked: Counter, queries_answered_by_graph: dict, selected_graph_ids: list[int], title: str, output_path: Path) -> None:
    """
    One row per distinct query, most asked first.
    Left: a bar as long as the number of times the query is asked; blue if a kept graph still answers it, gray if it is lost.
    Right: the graphs that fully answer a query, kept graphs (in pick order) left of the line, dropped graphs right of it.
    """
    queries = [query for query, _ in times_asked.most_common()]
    kept = set(selected_graph_ids)
    kept_columns = [graph_id for graph_id in selected_graph_ids if graph_id in queries_answered_by_graph]
    dropped_columns = sorted(
        (graph_id for graph_id in queries_answered_by_graph if graph_id not in kept),
        key=lambda graph_id: -sum(times_asked[query] for query in queries_answered_by_graph[graph_id]),
    )
    columns = kept_columns + dropped_columns
    if not columns:
        print("No graph fully answers any query, so there is no answered queries plot to draw.")
        return

    # Cells: 0 = no answer, 1 = answer in a dropped graph, 2 = answer in a kept graph.
    cells = np.zeros((len(queries), len(columns)))
    for column, graph_id in enumerate(columns):
        for row, query in enumerate(queries):
            if query in queries_answered_by_graph[graph_id]:
                cells[row, column] = 2 if graph_id in kept else 1
    is_answered = [any(query in queries_answered_by_graph[graph_id] for graph_id in kept_columns) for query in queries]
    answered_asks = sum(times_asked[query] for query, answered in zip(queries, is_answered) if answered)
    total_asks = sum(times_asked.values())

    heatmap_width = min(max(0.22 * len(columns), 2.5), 16)
    figure, (bar_axes, heatmap_axes) = plt.subplots(
        1, 2, sharey=True, layout="constrained",
        figsize=(6 + heatmap_width, min(1.5 + 0.3 * len(queries), 16)),
        gridspec_kw={"width_ratios": [2.5, heatmap_width]},
    )
    rows = np.arange(len(queries)) + 0.5

    bar_axes.barh(
        rows, [times_asked[query] for query in queries], height=0.7,
        color=[KEPT_ANSWERS if answered else DROPPED_ANSWERS for answered in is_answered],
    )
    for row, query in zip(rows, queries):
        bar_axes.annotate(f"{times_asked[query]}", (times_asked[query], row), xytext=(3, 0), textcoords="offset points",
                          va="center", fontsize=8, color=MUTED_INK)
    bar_axes.set_yticks(rows, [query if len(query) <= 45 else query[:44] + "…" for query in queries], fontsize=8, color=INK)
    bar_axes.set_xticks([])
    bar_axes.set_xlabel("times asked", color=MUTED_INK, fontsize=9)
    bar_axes.set_title(
        f"{title}\nAsks still answered: {answered_asks}/{total_asks} ({answered_asks / total_asks:.0%})",
        loc="left", color=INK, fontsize=10,
    )

    heatmap_axes.pcolormesh(
        cells, cmap=ListedColormap(["#ffffff", DROPPED_ANSWERS, KEPT_ANSWERS]), vmin=-0.5, vmax=2.5,
        edgecolors="#ffffff" if len(columns) <= 80 else "face", linewidth=1.5 if len(columns) <= 80 else 0,
    )
    heatmap_axes.axvline(len(kept_columns), color=INK, linewidth=1.2)
    heatmap_axes.text(len(kept_columns) - 0.3, -0.2, "kept", ha="right", va="bottom", fontsize=8, color=INK)
    if dropped_columns:
        heatmap_axes.text(len(kept_columns) + 0.3, -0.2, "dropped", ha="left", va="bottom", fontsize=8, color=INK)
    if len(columns) <= 40:
        heatmap_axes.set_xticks(np.arange(len(columns)) + 0.5, columns, fontsize=7, color=MUTED_INK)
    else:
        heatmap_axes.set_xticks([])
    heatmap_axes.set_xlabel("graph_id, kept in pick order | dropped", color=MUTED_INK, fontsize=9)

    bar_axes.invert_yaxis()  # Most asked query at the top (shared with the heatmap).
    for axes in (bar_axes, heatmap_axes):
        axes.tick_params(length=0)
        for spine in axes.spines.values():
            spine.set_visible(False)

    figure.legend(
        handles=[Patch(color=KEPT_ANSWERS, label="kept / still answered"), Patch(color=DROPPED_ANSWERS, label="dropped / lost")],
        loc="outside lower center", ncol=2, frameon=False, fontsize=8, labelcolor=MUTED_INK,
    )
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)


def plot_kept_graphs(all_graph_ids: list[int], queries_answered_by_graph: dict, kept: set[int], title: str, output_path: Path) -> None:
    """One square per graph of the database, grouped: kept and answers a query, kept and answers nothing, dropped and answered a query, dropped and answers nothing."""
    answers = set(queries_answered_by_graph)
    graphs = set(all_graph_ids)
    groups = [
        ("kept, answers a query", KEPT_ANSWERS, len(kept & answers)),
        ("kept, answers no query", KEPT_NOTHING, len(kept - answers)),
        ("dropped, answered a query", DROPPED_ANSWERS, len(answers - kept)),
        ("dropped, answers no query", DROPPED_NOTHING, len(graphs - kept - answers)),
    ]
    squares = [color for _, color, count in groups for _ in range(count)]

    per_row = 10 if len(squares) <= 40 else 50
    square_size = 0.32 if per_row == 10 else 0.16
    rows = -(-len(squares) // per_row)
    figure, axes = plt.subplots(figsize=(per_row * square_size + 0.4, rows * square_size + 1.6))
    for index, color in enumerate(squares):
        row, column = divmod(index, per_row)
        axes.add_patch(Rectangle((column + 0.06, row + 0.06), 0.88, 0.88, color=color, linewidth=0))
    axes.set_xlim(0, per_row)
    axes.set_ylim(rows, 0)
    axes.set_aspect("equal")
    axes.axis("off")
    axes.set_title(f"{title}\n{len(kept)} of {len(graphs)} graphs kept ({len(kept) / len(graphs):.0%})",
                   loc="left", color=INK, fontsize=10)
    axes.legend(
        handles=[Patch(color=color, label=f"{label} ({count})") for label, color, count in groups],
        loc="upper left", bbox_to_anchor=(0, 0), ncol=2, frameon=False, fontsize=8, labelcolor=MUTED_INK,
    )
    figure.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#ffffff")
    plt.close(figure)


ANSWERS_NEEDED = [1, 3, 10, None]  # None = all answers
PRESERVED_COLORMAP = LinearSegmentedColormap.from_list("preserved", ["#f3f7fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])


def preserved_answers(answering_graphs_per_line: list[set[int]], kept: set[int], answers_needed: int | None) -> float | None:
    """
    Same score as evaluate_reduction.measure_preserved_query_answers: for every query line with at least one answer in the
    full database, min(answers_needed, answers kept) / min(answers_needed, answers in the full database), averaged over those lines.
    """
    scores = []
    for answering_graphs in answering_graphs_per_line:
        if not answering_graphs:
            continue
        answers_kept, answers_in_full_database = len(answering_graphs & kept), len(answering_graphs)
        if answers_needed is not None:
            answers_kept, answers_in_full_database = min(answers_needed, answers_kept), min(answers_needed, answers_in_full_database)
        scores.append(answers_kept / answers_in_full_database)
    return sum(scores) / len(scores) if scores else None


def save_future_plot(graph_file: str, selected_graph_ids: list[int], future_query_logs: list[tuple[str, list[str]]], output_folder: str, title: str) -> None:
    """
    Save output_folder/preserved_answers.png: for every unseen query log (rows) and every number of answers a user needs (columns),
    the share of those answers the reduced database still has. Query lines with no answer in the full database are left out.
    """
    graphs = read_graph_database(graph_file)
    kept = set(selected_graph_ids)
    answering_graphs_by_query = {}
    rows = []
    for label, lines in future_query_logs:
        answering_graphs_per_line = []
        for query in (line.strip() for line in lines if line.strip()):
            if query not in answering_graphs_by_query:
                paths = parse_query(query)
                answering_graphs_by_query[query] = {graph_id for graph_id, graph in enumerate(graphs) if graph_satisfies_query(graph, paths)}
            answering_graphs_per_line.append(answering_graphs_by_query[query])
        rows.append((label.removesuffix(".txt"), answering_graphs_per_line))
    rows.append(("all unseen queries", [answering for _, per_line in rows for answering in per_line]))

    scores = np.array([[preserved_answers(per_line, kept, needed) for needed in ANSWERS_NEEDED] for _, per_line in rows], dtype=float)
    row_labels = [f"{label}  ({sum(1 for answering in per_line if answering)}/{len(per_line)} answerable)" for label, per_line in rows]

    figure, axes = plt.subplots(figsize=(9, 1.6 + 0.45 * len(rows)), layout="constrained")
    axes.imshow(np.nan_to_num(scores, nan=0.0), cmap=PRESERVED_COLORMAP, vmin=0.0, vmax=1.0, aspect="auto")
    for row in range(len(rows)):
        for column in range(len(ANSWERS_NEEDED)):
            score = scores[row, column]
            axes.text(column, row, "–" if np.isnan(score) else f"{score:.0%}", ha="center", va="center", fontsize=9,
                      color="#ffffff" if score > 0.55 else INK, fontweight="bold" if row == len(rows) - 1 else "normal")
    axes.axhline(len(rows) - 1.5, color="#ffffff", linewidth=4)  # Separates the combined row.
    axes.set_xticks(range(len(ANSWERS_NEEDED)), ["1" if needed == 1 else "all" if needed is None else str(needed) for needed in ANSWERS_NEEDED],
                    fontsize=9, color=INK)
    axes.set_yticks(range(len(rows)), row_labels, fontsize=9, color=INK)
    axes.set_xlabel("answers a user needs (c)", color=MUTED_INK, fontsize=9)
    figure.suptitle(f"{title}\nAnswers still in the reduced database for unseen queries", x=0.01, ha="left", color=INK, fontsize=10)
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)

    Path(output_folder).mkdir(parents=True, exist_ok=True)
    figure.savefig(Path(output_folder) / "preserved_answers.png", dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Future plot saved in {output_folder}")
