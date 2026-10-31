import argparse
import sys
import os
from query_matcher_and_measurer.match_queries_with_variables_on_graphs import match_graphs_with_queries_using_variables
from query_matcher_and_measurer.calculate_importance_for_graphs import measure_graph_importance_based_on_full_query_coverage,measure_graph_based_on_partial_query_coverage
from query_matcher_and_measurer.text_to_dataframe_converter import create_graphs_dataframe
from query_matcher_and_measurer.best_graph_selection_by_importance_threshold import select_best_graphs_by_importance_threshold
from pyspark.sql import DataFrame, SparkSession
from pathlib import Path

def create_new_database_file_from_selected_graphs(graph_text_file: str, selected_graph_ids: list[int], output_file_path: str):
    """
    Create a new database file containing only the selected graphs.

    Args:
        graph_text_file (str): Path to the original graph text file.
        selected_graph_ids (list[int]): List of selected graph IDs.
        output_file_path (str): Path to save the new database file.
    """

    # each graph is on a new line in the graph_text_file, and the graph_id is the line index (starting from 0)
    selected_graph_ids = set(selected_graph_ids)

    with open(graph_text_file, "r", encoding="utf-8") as infile, \
         open(output_file_path, "w", encoding="utf-8") as outfile:

        for graph_id, line in enumerate(infile):
            if graph_id in selected_graph_ids:
                outfile.write(line)


measure_dict = {
    "measure_graph_importance_based_on_full_query_coverage": measure_graph_importance_based_on_full_query_coverage,
    "measure_graph_based_on_partial_query_coverage": measure_graph_based_on_partial_query_coverage,
}

if __name__ == "__main__":

    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    parser = argparse.ArgumentParser(description=" Select best graphs based on importance measure and threshold.")
    parser.add_argument("--graph_file", type=str, default="data/DatabaseX_1.txt", help="Path to the graph text file.")
    parser.add_argument("--query_log_file", type=str, default="data/QLog1_4.txt", help="Path to the query log text file.")
    parser.add_argument("--output_file", type=str, default="data/DatabaseX_1_selected.txt", help="Path to save the new database file with selected graphs.")
    parser.add_argument("--importance_measure_function", type=str, default="measure_graph_based_on_partial_query_coverage", help="Importance measure function to use.")
    parser.add_argument("--importance_threshold", type=float, default=0.5, help="Importance threshold for selecting graphs.")
    args = parser.parse_args()

    graph_file = Path(__file__).parent / args.graph_file
    query_log_file = Path(__file__).parent / args.query_log_file
    output_file = Path(__file__).parent / args.output_file
    importance_measure_function_name = args.importance_measure_function
    importance_threshold = args.importance_threshold

    spark = SparkSession.builder.master("local[*]") .appName("spark_session").getOrCreate()

    graphs_df = create_graphs_dataframe(spark, str(graph_file))

    measure_function = measure_dict.get(importance_measure_function_name)

    satisfied_matches: DataFrame = match_graphs_with_queries_using_variables(spark, str(graph_file), str(query_log_file))

    print(f"Match table with query coverage for each graph and query (pairs with coverage 0 are left out):")
    satisfied_matches.orderBy("query_id", "graph_id").show(50, truncate=False)

    graphs_importance: dict[int, float] = {}

    graphs_importance = measure_function(graphs_df, satisfied_matches)

    best_selected_graph_ids = select_best_graphs_by_importance_threshold(graphs_importance, importance_threshold)

    for graph_id in best_selected_graph_ids:
        print(f"Selected graph_id: {graph_id} with importance: {graphs_importance[graph_id]}")

    create_new_database_file_from_selected_graphs(
        str(graph_file),
        best_selected_graph_ids,
        str(output_file)
    )

    spark.stop()