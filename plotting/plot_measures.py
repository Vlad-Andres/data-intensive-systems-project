"""
Show what the three importance measures (full, partial, distributed) give every graph, side by side.

    uv run python -m plotting.plot_measures --graph data/DatabaseX_3.txt --qlog data/QLog3_3.txt

Rows are all graphs of the database (best rank first), columns are measures; use a small database so every graph fits. Each cell shows the score and the graph's rank in that column; the colour is the score
relative to the highest score of that column (white = 0, dark blue = highest), because the three measures use different scales.
For demonstration the scores use the whole query log (main.py only uses its first half).
Saves plots/measures/<database>_<query log>.csv (the scores) and .png, drawn from the CSV (redraw with plotting.replot).
"""
import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from pyspark.sql import SparkSession

from query_matcher_and_measurer.calculate_importance_for_graphs import (
    measure_graph_based_on_partial_query_coverage,
    measure_graph_importance_based_on_current_queries,
    measure_graph_importance_based_on_full_query_coverage,
)
from query_matcher_and_measurer.match_queries_with_variables_on_graphs import match_graphs_with_queries_using_variables
from query_matcher_and_measurer.text_to_dataframe_converter import create_graphs_dataframe

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
MEASURES = {
    "full": measure_graph_importance_based_on_full_query_coverage,
    "partial": measure_graph_based_on_partial_query_coverage,
    "distributed": measure_graph_importance_based_on_current_queries,
}
SCORE_COLORMAP = LinearSegmentedColormap.from_list("score", ["#ffffff", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
INK, MUTED_INK = "#1f1f1e", "#5f5e5a"


def ranks(scores: dict[int, float]) -> dict[int, int]:
    """Rank 1 = highest score; equal scores share a rank."""
    ordered = sorted(scores.values(), reverse=True)
    return {graph_id: ordered.index(score) + 1 for graph_id, score in scores.items()}


def plot_measures(scores_by_measure: dict[str, dict[int, float]], title: str, output_path: Path) -> None:
    # Every graph, ordered by its best rank in any measure.
    rank_by_measure = {measure: ranks(scores) for measure, scores in scores_by_measure.items()}
    graph_ids = sorted(scores_by_measure["full"], key=lambda graph_id: (min(rank_by_measure[m][graph_id] for m in MEASURES), graph_id))

    scores = np.array([[scores_by_measure[m][graph_id] for m in MEASURES] for graph_id in graph_ids])
    column_max = scores.max(axis=0)
    relative = np.divide(scores, column_max, out=np.zeros_like(scores), where=column_max > 0)

    figure, axes = plt.subplots(figsize=(7.5, 1.6 + 0.42 * len(graph_ids)), layout="constrained")
    axes.imshow(relative, cmap=SCORE_COLORMAP, vmin=0, vmax=1, aspect="auto")
    for row, graph_id in enumerate(graph_ids):
        for column, measure in enumerate(MEASURES):
            score = scores[row, column]
            label = f"{score:.3g}   #{rank_by_measure[measure][graph_id]}" if score > 0 else "0"
            axes.text(column, row, label, ha="center", va="center", fontsize=9,
                      color="#ffffff" if relative[row, column] > 0.55 else INK)
    axes.set_xticks(range(len(MEASURES)), list(MEASURES), fontsize=10, color=INK)
    axes.xaxis.tick_top()
    axes.set_yticks(range(len(graph_ids)), [f"graph {graph_id}" for graph_id in graph_ids], fontsize=9, color=INK)
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)
    note = "score   #rank · colour = score / highest score of the column"
    figure.suptitle(f"{title}\n{note}", x=0.01, ha="left", fontsize=10, color=INK)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)
    print(f"Saved {output_path.relative_to(PROJECT_DIRECTORY)}")


def save_measures(scores_by_measure: dict[str, dict[int, float]], title: str, base_path: Path) -> None:
    """Save the scores (base_path.csv) and the title (base_path.json), then draw base_path.png from them."""
    base_path.parent.mkdir(parents=True, exist_ok=True)
    with open(base_path.with_suffix(".csv"), "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["graph_id", *MEASURES])
        for graph_id in sorted(scores_by_measure["full"]):
            writer.writerow([graph_id, *(scores_by_measure[measure][graph_id] for measure in MEASURES)])
    base_path.with_suffix(".json").write_text(json.dumps({"title": title}))
    draw_measures(base_path)


def draw_measures(base_path: Path) -> None:
    """Draw base_path.png from base_path.csv and base_path.json."""
    with open(base_path.with_suffix(".csv"), newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    scores_by_measure = {measure: {int(row["graph_id"]): float(row[measure]) for row in rows} for measure in MEASURES}
    title = json.loads(base_path.with_suffix(".json").read_text())["title"]
    plot_measures(scores_by_measure, title, base_path.with_suffix(".png"))


if __name__ == "__main__":
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    parser = argparse.ArgumentParser(description="Compare the full, partial and distributed importance of every graph.")
    parser.add_argument("--graph", default="data/DatabaseX_3.txt", help="Graph database (a small one, so every graph fits).")
    parser.add_argument("--qlog", default="data/QLog3_3.txt", help="Query log.")
    args = parser.parse_args()

    graph_file, query_log_file = PROJECT_DIRECTORY / args.graph, PROJECT_DIRECTORY / args.qlog
    query_lines = query_log_file.read_text(encoding="utf-8").splitlines()

    spark = SparkSession.builder.master("local[*]").appName("plot_measures").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8") as matched_log:
        matched_log.write("\n".join(query_lines))
        matched_log.flush()
        matches = match_graphs_with_queries_using_variables(spark, str(graph_file), matched_log.name)
        graphs_df = create_graphs_dataframe(spark, str(graph_file))
        scores_by_measure = {name: measure(graphs_df, matches) for name, measure in MEASURES.items()}
    spark.stop()

    save_measures(
        scores_by_measure,
        f"Graph importance per measure: {graph_file.stem} · {query_log_file.stem} (whole log)",
        PROJECT_DIRECTORY / "plots" / "measures" / f"{graph_file.stem}_{query_log_file.stem}",
    )
