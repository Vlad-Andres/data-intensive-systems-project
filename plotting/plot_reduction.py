"""
Plots of one reduction run, one folder per phase of main.py. Every plot is drawn from CSV files saved next to it, so the
plots can be redrawn without running the reduction again (uv run python -m plotting.replot).

  plots/runs/<run>/run_info.json                     title, measure, number of graphs, number kept
  plots/runs/<run>/queries.csv                       every distinct past query and how often it is asked
  plots/runs/<run>/1_match/coverage_table.csv/.png   how much of each past query each graph satisfies
  plots/runs/<run>/2_scores/graph_scores.csv/.png    the importance score of every graph and its pick order
  plots/runs/<run>/3_selection/answers.csv           which graph fully answers which past query, kept or dropped
  plots/runs/<run>/3_selection/answered_queries.png  which past queries the kept graphs still answer
  plots/runs/<run>/3_selection/kept_graphs.png       one square per graph of the database: kept or dropped
  plots/runs/<run>/4_evaluation/coverage.csv/.png    exact coverage and closeness on the past, the future and the other logs
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window that would pause the run.

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from plotting.coverage_metrics import METRICS, ClosenessIndex
from graph_parser import read_graph_database  # noqa: E402  (src/ is on the path through plotting.coverage_metrics)

# Hue = kept (blue) or dropped (gray); darker = the graph answers a query.
KEPT_ANSWERS, KEPT_NOTHING = "#256abf", "#b7d3f6"
DROPPED_ANSWERS, DROPPED_NOTHING = "#8a8984", "#e4e3df"
EXACT_COLOR, CLOSENESS_COLOR = "#2a78d6", "#9ec5f4"
INK, MUTED_INK, GRID = "#1f1f1e", "#5f5e5a", "#e4e3df"
COVERAGE_COLORMAP = LinearSegmentedColormap.from_list("coverage", ["#ffffff", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
MAX_COLUMNS = 50
MAX_SCORE_ROWS = 25
MAX_QUERY_ROWS = 40  # Larger logs show only their most asked queries.


# ----------------------------------------------------------------------------------------------------------------- files

def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def read_run(folder: Path) -> tuple[dict, Counter]:
    """The run's info and how often each distinct past query is asked (most asked first)."""
    info = json.loads((folder / "run_info.json").read_text())
    times_asked = Counter({row["query"]: int(row["times_asked"]) for row in read_csv(folder / "queries.csv")})
    return info, times_asked


# --------------------------------------------------------------------------------------------------------------- saving

def save_run_plots(graphs_matches, query_lines: list[str], graphs_importance: dict[int, float], measure_name: str,
                   selected_graph_ids: list[int], output_folder: str, title: str) -> None:
    """
    Save the data of the match, score and selection phases of a run as CSV, then draw their plots from it.

    Args:
        graphs_matches: Spark DataFrame with graph_id, query_id and query_coverage, query_id being the line index in query_lines.
        query_lines: The lines of the query log that was matched (the past, first half).
        graphs_importance: Score of every graph under the chosen measure.
        measure_name: Name of that measure (full, partial or distributed).
        selected_graph_ids: The kept graphs, in pick order.
        output_folder: plots/runs/<run>.
        title: Title shown above the plots.
    """
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    query_by_line = {line_index: line.strip() for line_index, line in enumerate(query_lines) if line.strip()}
    times_asked = Counter(query_by_line.values())
    coverage_by_graph = defaultdict(dict)  # graph_id -> {query: coverage}
    for row in graphs_matches.select("graph_id", "query_id", "query_coverage").collect():
        coverage_by_graph[row["graph_id"]][query_by_line[row["query_id"]]] = row["query_coverage"]
    pick_order = {graph_id: position for position, graph_id in enumerate(selected_graph_ids, start=1)}

    (folder / "run_info.json").write_text(json.dumps(
        {"title": title, "measure": measure_name, "graph_count": len(graphs_importance), "kept_count": len(selected_graph_ids)}, indent=2))
    write_csv(folder / "queries.csv", ["query", "times_asked"],
              [{"query": query, "times_asked": count} for query, count in times_asked.most_common()])
    write_csv(folder / "1_match" / "coverage_table.csv", ["query", "graph_id", "coverage"],
              [{"query": query, "graph_id": graph_id, "coverage": value}
               for graph_id, coverages in coverage_by_graph.items() for query, value in coverages.items()])
    write_csv(folder / "2_scores" / "graph_scores.csv", ["graph_id", "score", "pick_order"],
              [{"graph_id": graph_id, "score": score, "pick_order": pick_order.get(graph_id, "")} for graph_id, score in graphs_importance.items()])
    write_csv(folder / "3_selection" / "answers.csv", ["query", "graph_id", "pick_order"],
              [{"query": query, "graph_id": graph_id, "pick_order": pick_order.get(graph_id, "")}
               for graph_id, coverages in coverage_by_graph.items() for query, value in coverages.items() if value == 1.0])
    draw_run_plots(folder)
    print(f"\nPlots saved in {output_folder}")


def save_evaluation_plot(graph_file: str, selected_graph_ids: list[int], query_sets: list[tuple[str, list[str]]], output_folder: str) -> None:
    """
    Save output_folder/4_evaluation/coverage.csv and its plot: for every query set (the past half, the future half, the other
    logs of the database) the exact coverage and the closeness of the reduced database, and of a random reduction of the same size.
    """
    graphs = read_graph_database(graph_file)
    kept = set(selected_graph_ids)
    index = ClosenessIndex(graphs)
    rows = []
    for label, lines in query_sets:
        closeness = index.of_lines(lines)
        if not closeness:
            continue
        row = {"query_set": label.removesuffix(".txt"), "lines": len(closeness)}
        for metric, (method_metric, random_metric) in METRICS.items():
            row[metric] = method_metric(closeness, kept)
            row[f"random_{metric}"] = random_metric(closeness, len(graphs), len(kept))
        rows.append(row)
    folder = Path(output_folder)
    write_csv(folder / "4_evaluation" / "coverage.csv", ["query_set", "lines", "exact", "closeness", "random_exact", "random_closeness"], rows)
    draw_evaluation(folder)
    print(f"Evaluation plot saved in {folder / '4_evaluation'}")


# -------------------------------------------------------------------------------------------------------------- drawing

def draw_run_plots(folder: Path) -> None:
    """Draw every plot of a run from its CSV files."""
    info, times_asked = read_run(folder)
    coverage_by_graph = defaultdict(dict)
    for row in read_csv(folder / "1_match" / "coverage_table.csv"):
        coverage_by_graph[int(row["graph_id"])][row["query"]] = float(row["coverage"])
    scores = {int(row["graph_id"]): float(row["score"]) for row in read_csv(folder / "2_scores" / "graph_scores.csv")}
    pick_order = {int(row["graph_id"]): int(row["pick_order"]) for row in read_csv(folder / "2_scores" / "graph_scores.csv") if row["pick_order"]}
    selected = sorted(pick_order, key=pick_order.get)
    answered = defaultdict(set)
    for row in read_csv(folder / "3_selection" / "answers.csv"):
        answered[int(row["graph_id"])].add(row["query"])

    draw_coverage_table(times_asked, coverage_by_graph, info["graph_count"], info["title"], folder / "1_match" / "coverage_table.png")
    draw_graph_scores(scores, info["measure"], selected, info["title"], folder / "2_scores" / "graph_scores.png")
    draw_answered_queries(times_asked, answered, selected, info["title"], folder / "3_selection" / "answered_queries.png")
    draw_kept_graphs(list(scores), answered, set(selected), info["title"], folder / "3_selection" / "kept_graphs.png")
    if (folder / "4_evaluation" / "coverage.csv").exists():
        draw_evaluation(folder)


def shorten(text: str, length: int = 45) -> str:
    return text if len(text) <= length else text[: length - 1] + "…"


def clean(axes) -> None:
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)


def draw_coverage_table(times_asked: Counter, coverage_by_graph: dict, graph_count: int, title: str, output_path: Path) -> None:
    """One row per distinct past query (with how often it is asked), one column per graph that fully answers at least one query."""
    queries = [query for query, _ in times_asked.most_common(MAX_QUERY_ROWS)]
    rows_note = f" · the {len(queries)} most asked of {len(times_asked)} queries shown" if len(times_asked) > len(queries) else ""
    answering = [graph_id for graph_id, coverages in coverage_by_graph.items() if 1.0 in coverages.values()]
    columns = sorted(answering, key=lambda graph_id: (-sum(times_asked[q] for q, v in coverage_by_graph[graph_id].items() if v == 1.0), graph_id))
    hidden = max(len(columns) - MAX_COLUMNS, 0)
    columns = columns[:MAX_COLUMNS]
    if not columns:
        print("No graph fully answers any query, so there is no coverage table to draw.")
        return

    cells = np.array([[coverage_by_graph[graph_id].get(query, 0.0) for graph_id in columns] for query in queries])
    figure, axes = plt.subplots(figsize=(max(11, 6 + 0.3 * len(columns)), 1.8 + 0.32 * len(queries)), layout="constrained")
    axes.pcolormesh(cells, cmap=COVERAGE_COLORMAP, vmin=0, vmax=1, edgecolors="#ffffff", linewidth=1.5)
    if cells.size <= 600:
        for row in range(len(queries)):
            for column in range(len(columns)):
                value = cells[row, column]
                if value > 0:
                    axes.text(column + 0.5, row + 0.5, "1" if value == 1.0 else f"{value:.2g}", ha="center", va="center",
                              fontsize=7, color="#ffffff" if value > 0.6 else INK)
    axes.invert_yaxis()
    axes.set_yticks(np.arange(len(queries)) + 0.5, [f"{shorten(query)}  ×{times_asked[query]}" for query in queries], fontsize=8, color=INK)
    axes.set_xticks(np.arange(len(columns)) + 0.5, columns, fontsize=7, color=MUTED_INK, rotation=90 if len(columns) > 20 else 0)
    note = f" (first {MAX_COLUMNS} shown, {hidden} more)" if hidden else ""
    axes.set_xlabel(f"graph_id: the {len(answering)} of {graph_count} graphs that fully answer at least one query{note}", color=MUTED_INK, fontsize=9)
    clean(axes)
    axes.set_title(f"{title}\nMatch: share of each query's parts a graph satisfies (1 = full answer) · ×n = times asked{rows_note}",
                   loc="left", color=INK, fontsize=10)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)


def draw_graph_scores(scores: dict[int, float], measure_name: str, selected_graph_ids: list[int], title: str, output_path: Path) -> None:
    """The highest scoring graphs under the measure, coloured kept / dropped, kept graphs labelled with their pick order."""
    pick_order = {graph_id: position for position, graph_id in enumerate(selected_graph_ids, start=1)}
    ranked = sorted(scores, key=lambda graph_id: (-scores[graph_id], graph_id))
    shown = [graph_id for graph_id in ranked if scores[graph_id] > 0 or graph_id in pick_order][:MAX_SCORE_ROWS]
    kept_not_shown = [graph_id for graph_id in selected_graph_ids if graph_id not in shown]

    figure, axes = plt.subplots(figsize=(10, 1.6 + 0.3 * len(shown)), layout="constrained")
    rows = np.arange(len(shown))
    axes.barh(rows, [scores[g] for g in shown], height=0.7, color=[KEPT_ANSWERS if g in pick_order else DROPPED_ANSWERS for g in shown])
    for row, graph_id in zip(rows, shown):
        label = f"{scores[graph_id]:.3g}" + (f"   picked #{pick_order[graph_id]}" if graph_id in pick_order else "")
        axes.annotate(label, (scores[graph_id], row), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=MUTED_INK)
    axes.set_yticks(rows, [f"graph {graph_id}" for graph_id in shown], fontsize=8, color=INK)
    axes.invert_yaxis()
    axes.set_xlabel(f"importance score ({measure_name})", color=MUTED_INK, fontsize=9)
    axes.xaxis.grid(True, color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(labelsize=8, labelcolor=MUTED_INK)
    clean(axes)
    note = f" · {len(kept_not_shown)} kept graphs rank lower and are not shown" if kept_not_shown else ""
    axes.set_title(f"{title}\nScores: the {len(shown)} highest of {len(scores)} graphs under the {measure_name} measure{note}",
                   loc="left", color=INK, fontsize=10)
    figure.legend(handles=[Patch(color=KEPT_ANSWERS, label="kept (pick order shown)"), Patch(color=DROPPED_ANSWERS, label="dropped")],
                  loc="outside lower center", ncol=2, frameon=False, fontsize=8, labelcolor=MUTED_INK)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)


def draw_answered_queries(times_asked: Counter, answered: dict, selected_graph_ids: list[int], title: str, output_path: Path) -> None:
    """
    One row per distinct past query, most asked first.
    Left: a bar as long as the number of times the query is asked; blue if a kept graph still answers it, gray if it is lost.
    Right: the graphs that fully answer a query, kept graphs (in pick order) left of the line, dropped graphs right of it.
    """
    all_queries = [query for query, _ in times_asked.most_common()]
    queries = all_queries[:MAX_QUERY_ROWS]
    kept = set(selected_graph_ids)
    kept_answering_any = [graph_id for graph_id in selected_graph_ids if graph_id in answered]
    shown = set(queries)
    # Columns: graphs that answer a shown query, kept ones first, at most MAX_COLUMNS (kept graphs take priority).
    kept_columns = [graph_id for graph_id in kept_answering_any if answered[graph_id] & shown][:MAX_COLUMNS - 10]
    dropped_columns = sorted((graph_id for graph_id in answered if graph_id not in kept and answered[graph_id] & shown),
                             key=lambda graph_id: -sum(times_asked[query] for query in answered[graph_id] & shown))
    hidden_columns = max(len(kept_columns) + len(dropped_columns) - MAX_COLUMNS, 0)
    dropped_columns = dropped_columns[:MAX_COLUMNS - len(kept_columns)]
    columns = kept_columns + dropped_columns
    if not columns:
        print("No graph fully answers any query, so there is no answered queries plot to draw.")
        return

    # Cells: 0 = no answer, 1 = answer in a dropped graph, 2 = answer in a kept graph.
    cells = np.zeros((len(queries), len(columns)))
    for column, graph_id in enumerate(columns):
        for row, query in enumerate(queries):
            if query in answered[graph_id]:
                cells[row, column] = 2 if graph_id in kept else 1
    is_answered = [any(query in answered[graph_id] for graph_id in kept_answering_any) for query in queries]
    answered_asks = sum(times_asked[query] for query in all_queries if any(query in answered[graph_id] for graph_id in kept_answering_any))
    total_asks = sum(times_asked.values())
    rows_note = f" · the {len(queries)} most asked of {len(all_queries)} queries shown" if len(all_queries) > len(queries) else ""

    heatmap_width = min(max(0.22 * len(columns), 2.5), 16)
    figure, (bar_axes, heatmap_axes) = plt.subplots(1, 2, sharey=True, layout="constrained",
                                                    figsize=(max(11, 6 + heatmap_width), min(1.8 + 0.3 * len(queries), 16)),
                                                    gridspec_kw={"width_ratios": [2.5, heatmap_width]})
    rows = np.arange(len(queries)) + 0.5
    bar_axes.barh(rows, [times_asked[query] for query in queries], height=0.7,
                  color=[KEPT_ANSWERS if ok else DROPPED_ANSWERS for ok in is_answered])
    for row, query in zip(rows, queries):
        bar_axes.annotate(f"{times_asked[query]}", (times_asked[query], row), xytext=(3, 0), textcoords="offset points",
                          va="center", fontsize=8, color=MUTED_INK)
    bar_axes.set_yticks(rows, [shorten(query) for query in queries], fontsize=8, color=INK)
    bar_axes.set_xticks([])
    bar_axes.set_xlabel("times the query is asked", color=MUTED_INK, fontsize=9)
    bar_axes.set_title(f"{title}\nSelection: past query lines still fully answered by a kept graph: "
                       f"{answered_asks}/{total_asks} ({answered_asks / total_asks:.0%}){rows_note}", loc="left", color=INK, fontsize=10)

    heatmap_axes.pcolormesh(cells, cmap=ListedColormap(["#ffffff", DROPPED_ANSWERS, KEPT_ANSWERS]), vmin=-0.5, vmax=2.5,
                            edgecolors="#ffffff" if len(columns) <= 80 else "face", linewidth=1.5 if len(columns) <= 80 else 0)
    heatmap_axes.axvline(len(kept_columns), color=INK, linewidth=1.2)
    header = heatmap_axes.get_xaxis_transform()  # x in data coordinates, y in axes coordinates (1 = top edge).
    heatmap_axes.annotate("kept", (len(kept_columns), 1), xycoords=header, xytext=(-3, 3), textcoords="offset points",
                          ha="right", va="bottom", fontsize=8, color=INK)
    if dropped_columns:
        heatmap_axes.annotate("dropped", (len(kept_columns), 1), xycoords=header, xytext=(3, 3), textcoords="offset points",
                              ha="left", va="bottom", fontsize=8, color=INK)
    if len(columns) <= 40:
        heatmap_axes.set_xticks(np.arange(len(columns)) + 0.5, columns, fontsize=7, color=MUTED_INK)
    else:
        heatmap_axes.set_xticks([])
    column_note = f" ({len(columns)} shown, {hidden_columns} more)" if hidden_columns else ""
    heatmap_axes.set_xlabel(f"graphs that fully answer a shown query (graph_id)\nkept in pick order | dropped{column_note}", color=MUTED_INK, fontsize=9)
    bar_axes.invert_yaxis()  # Most asked query at the top (shared with the heatmap).
    clean(bar_axes)
    clean(heatmap_axes)
    figure.legend(handles=[Patch(color=KEPT_ANSWERS, label="query still answered / answer in a kept graph"),
                           Patch(color=DROPPED_ANSWERS, label="query lost / answer only in a dropped graph")],
                  loc="outside lower center", ncol=2, frameon=False, fontsize=8, labelcolor=MUTED_INK)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)


def draw_kept_graphs(all_graph_ids: list[int], answered: dict, kept: set[int], title: str, output_path: Path) -> None:
    """One square per graph of the database: kept / dropped x answers a past query or not."""
    answers = set(answered)
    graphs = set(all_graph_ids)
    groups = [
        ("kept, fully answers a past query", KEPT_ANSWERS, len(kept & answers)),
        ("kept, answers no past query", KEPT_NOTHING, len(kept - answers)),
        ("dropped, fully answered a past query", DROPPED_ANSWERS, len(answers - kept)),
        ("dropped, answers no past query", DROPPED_NOTHING, len(graphs - kept - answers)),
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
    axes.set_title(f"{title}\nSelection: one square per graph of the database · {len(kept)} of {len(graphs)} kept ({len(kept) / len(graphs):.0%})",
                   loc="left", color=INK, fontsize=10)
    axes.legend(handles=[Patch(color=color, label=f"{label} ({count})") for label, color, count in groups],
                loc="upper left", bbox_to_anchor=(0, 0), ncol=2, frameon=False, fontsize=8, labelcolor=MUTED_INK)
    figure.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#ffffff")
    plt.close(figure)


def draw_evaluation(folder: Path) -> None:
    """Exact coverage and closeness per query set, with the random reduction of the same size as a black line."""
    info = json.loads((folder / "run_info.json").read_text())
    rows = read_csv(folder / "4_evaluation" / "coverage.csv")
    labels = [f"{row['query_set']}\n({row['lines']} lines)" for row in rows]

    figure, axes = plt.subplots(figsize=(2 + 1.6 * len(labels), 4.6), layout="constrained")
    width = 0.36
    for offset, metric, color, name in ((-width / 2, "exact", EXACT_COLOR, "exact: fully answered"),
                                         (width / 2, "closeness", CLOSENESS_COLOR, "closeness: near answers count partly")):
        x = np.arange(len(labels)) + offset
        values = [float(row[metric]) for row in rows]
        baselines = [float(row[f"random_{metric}"]) for row in rows]
        axes.bar(x, values, width=width * 0.9, color=color, label=name)
        for position, value, baseline in zip(x, values, baselines):
            axes.annotate(f"{value:.0f}%", (position, value), xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=7, color=MUTED_INK)
            axes.plot([position - width * 0.42, position + width * 0.42], [baseline, baseline], color=INK, linewidth=1.6)
    axes.set_xticks(range(len(labels)), labels, fontsize=8, color=INK)
    axes.set_ylim(0, 108)
    axes.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], fontsize=8, color=MUTED_INK)
    axes.set_ylabel("query lines", color=MUTED_INK, fontsize=9)
    axes.yaxis.grid(True, color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    clean(axes)
    axes.set_title(f"{info['title']}\nEvaluation: how well the reduced database answers each set of queries", loc="left", color=INK, fontsize=10)
    handles, _ = axes.get_legend_handles_labels()
    figure.legend(handles=handles + [Line2D([], [], color=INK, linewidth=1.6, label="random reduction of the same size")],
                  loc="outside lower center", ncol=3, frameon=False, fontsize=8, labelcolor=MUTED_INK)
    figure.savefig(folder / "4_evaluation" / "coverage.png", dpi=150, facecolor="#ffffff")
    plt.close(figure)
