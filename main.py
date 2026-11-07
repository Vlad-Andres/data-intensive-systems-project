import argparse
import sys
import os
import time
from query_matcher_and_measurer.match_queries_with_variables_on_graphs import match_graphs_with_queries_using_variables
from query_matcher_and_measurer.calculate_importance_for_graphs import measure_graph_importance_based_on_full_query_coverage,measure_graph_based_on_partial_query_coverage,measure_graph_importance_based_on_current_queries
from query_matcher_and_measurer.text_to_dataframe_converter import create_graphs_dataframe
from query_matcher_and_measurer.best_graph_selection_by_importance_threshold import select_best_graphs_by_importance_threshold
from query_matcher_and_measurer.select_best_graphs_greedily import select_best_graphs_greedily
from query_matcher_and_measurer.evaluate_reduction import measure_preserved_query_answers
from pyspark.sql import DataFrame, SparkSession, functions as F
from pathlib import Path
from graph_parser import read_graph_database
from QLog_satisfaction import parse_query, query_coverage
from query_matcher_and_measurer.select_graphs_by_information_gain import select_graphs_by_information_gain
from plotting.plot_reduction import save_run_plots, save_evaluation_plot
import json


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
    "measure_graph_importance_based_on_current_queries": measure_graph_importance_based_on_current_queries,
}

if __name__ == "__main__":

    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    parser = argparse.ArgumentParser(description=" Select best graphs based on importance measure and threshold.")
    parser.add_argument("--graph", type=str, default="data/DatabaseX_1.txt", help="Path to the graph text file.")
    parser.add_argument("--qlog", type=str, default="data/QLog1_1.txt", help="Path to the query log text file.")
    parser.add_argument("--graph_similarity", type=bool, default=False, help="Whether to consider graph similarity in the selection process.")
    parser.add_argument("--similarity_budget",type=float,default=0.2,help="Fraction of the selected-graph budget reserved for information-gain selection (0 to 1).")
    parser.add_argument("--query_coverage", type=str, default="full", choices=["full", "partial","distributed"], help="Query coverage type: 'full' or 'partial'. or 'distributed'" )
    parser.add_argument("--graph_selection", type=str, default="simple", choices=["simple", "rounds"], help="Selection method to use: 'simple' or 'rounds'.")
    parser.add_argument("--importance_threshold", type=float, default=0.9, help="Percentage of the db we want to keep.")
    parser.add_argument("--tests", type=bool, default=False, help="Whether to run tests on the reduced database.")
    parser.add_argument("--performance", type=bool, default=False, help="Whether to measure performance of the reduction and testing functions.")

    args = parser.parse_args()

    original_db_number = args.qlog.split("QLog")[1].split("_")[0].split(".")[0]
    original_qlog_number = args.qlog.split("QLog")[1].split("_")[1].split(".")[0]

    graph_file = Path(__file__).parent / args.graph
    query_log_file = Path(__file__).parent / args.qlog
    output_file = f"data/reductions/Database{original_db_number}_{original_qlog_number}"
    if args.query_coverage == "full":
        output_file += "_full_query_coverage"
    elif args.query_coverage == "partial":
        output_file += "_partial_query_coverage"
    elif args.query_coverage == "distributed":
        output_file += "_distributed_query_coverage"
    output_file += f"_{args.graph_selection}_selection_keep_{args.importance_threshold}"
    if args.graph_similarity:
        output_file += f"_graph_similarity_{args.similarity_budget}"
    output_file += ".txt"

    start_time = time.time()
    spark_startup_start_time = time.time()

    spark = SparkSession.builder.master("local[*]").appName("spark_session").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR") # Avoid verbose logging from Spark
    spark_startup_time = time.time() - spark_startup_start_time

    reduction_start_time = time.time()

    # DB goes into a Spark Dataframe
    graph_creation_start_time = time.time()
    graphs_df = create_graphs_dataframe(spark, str(graph_file))
    graph_creation_time = time.time() - graph_creation_start_time

    # I want to halve the qlog file: 
    # half will be used for the selection of the best graphs, and 
    # the other half will be used to test the reducted db

    # I need to create a new query log file with the first half of the queries, and another with the second half of the queries

    query_log_file_lines = query_log_file.read_text(encoding="utf-8").splitlines()
    half_index = len(query_log_file_lines) // 2
    query_log_file_first_half = query_log_file_lines[:half_index]
    query_log_file_second_half = query_log_file_lines[half_index:]
    query_log_file_first_half_path = query_log_file.parent / f"QLog{original_db_number}_{original_qlog_number}_first_half.txt"
    query_log_file_second_half_path = query_log_file.parent / f"QLog{original_db_number}_{original_qlog_number}_second_half.txt"
    query_log_file_first_half_path.write_text("\n".join(query_log_file_first_half), encoding="utf-8")
    query_log_file_second_half_path.write_text("\n".join(query_log_file_second_half), encoding="utf-8")

    # Match Phase: Match graphs with queries

    qlog_creation_start_time = time.time() # How much time it takes to create the match table with query coverage for each graph and query and load it onto a Spark DataFrame
    qlog_creation_time = 0
    satisfied_matches: DataFrame = match_graphs_with_queries_using_variables(spark, str(graph_file), str(query_log_file_first_half_path))
    qlog_creation_time = time.time() - qlog_creation_start_time
    #print(f"Match table with query coverage for each graph and query (pairs with coverage 0 are left out):")
    #satisfied_matches.orderBy("query_id", "graph_id").show(50, truncate=False)


    graphs_importance: dict[int, float] = {}

    # Determine the importance measure function based on the presence of subqueries
    measure_function = None
    if args.query_coverage == "full":  # 1 point per query line the graph fully answers
        measure_function = measure_graph_importance_based_on_full_query_coverage
    elif args.query_coverage == "partial":  # per query line, the share of its paths the graph satisfies (e.g. 1 of 2 = 0.5)
        measure_function = measure_graph_based_on_partial_query_coverage
    elif args.query_coverage == "distributed":  # each query line gives 1 point, split over the graphs that fully answer it: w(q) / |A(q)|
        measure_function = measure_graph_importance_based_on_current_queries

    # Calculate the importance of each graph based on the selected measure function   
    if measure_function is None:
        raise ValueError(f"Unsupported query coverage type: {args.query_coverage}")
    
    selection_start_time = time.time()

    graphs_importance = measure_function(graphs_df, satisfied_matches)
    importance_threshold = args.importance_threshold

    if args.graph_selection == "simple":  # sort once by importance, keep the top B·|D|
        best_selected_graph_ids = select_best_graphs_by_importance_threshold(graphs_importance, importance_threshold)
    elif args.graph_selection == "rounds":  # greedy: keep the highest gain w(q) / ((have(q)+1)·H(|A(q)|)), recompute, repeat;
        best_selected_graph_ids = select_best_graphs_greedily(graphs_importance, satisfied_matches, importance_threshold)
    else:
        raise ValueError(f"Unsupported graph selection method: {args.graph_selection}")

    selection_time = time.time() - selection_start_time

    ## Here I want to integrate graph similarity in the choice of the worse graphs:
    #  between the 2 lowest scoring graphs, which is adding the least new information to the selected graphs,
    #  and thus is the most similar to the already selected graphs, should be removed first.

    best_selected_graph_ids_copy = best_selected_graph_ids.copy()  # Create a copy to avoid modifying the original list during iteration

    graph_similarity_start_time = time.time()
    if args.graph_similarity: # Reserve % of the selected-graph budget for raw information-gain selection, and the rest for query-based selection
        best_selected_graph_ids = select_graphs_by_information_gain(graphs_df,graphs_importance,best_selected_graph_ids,args.similarity_budget)
        graph_similarity_time = time.time() - graph_similarity_start_time

        # I print the difference between the original best_selected_graph_ids and the new best_selected_graph_ids after considering graph similarity
        removed_graphs = set(best_selected_graph_ids_copy) - set(best_selected_graph_ids)
        added_graphs = set(best_selected_graph_ids) - set(best_selected_graph_ids_copy)

        if removed_graphs:
            print("\n============================= Graphs removed due to similarity consideration: =============================")
            for graph_id in sorted(removed_graphs):
                print(f"Removed graph_id {graph_id} with importance: {graphs_importance[graph_id]}")

            print("\n============================= Graphs added due to similarity consideration: =============================")
            for graph_id in sorted(added_graphs):
                print(f"Added graph_id {graph_id} with importance: {graphs_importance[graph_id]}")

    # Plots of the match, score and selection phases, saved in plots/runs/<name of the reduction>/ (not counted in the timings)
    plotting_start_time = time.time()
    plots_folder = Path(__file__).parent / "plots" / "runs" / Path(output_file).stem
    plot_title = (f"{Path(args.graph).stem} · {Path(args.qlog).stem} · {args.graph_selection} selection, {args.query_coverage} measure, "
                  f"keep {args.importance_threshold:.0%}" + (f", graph similarity budget {args.similarity_budget}" if args.graph_similarity else ""))
    save_run_plots(satisfied_matches, query_log_file_first_half, graphs_importance, args.query_coverage, best_selected_graph_ids, str(plots_folder), plot_title)
    plotting_time = time.time() - plotting_start_time

    print(f"\n============================= Selected graph IDs in pick order: =============================")
    for pick_order, graph_id in enumerate(best_selected_graph_ids, start=1):
        print(f"Pick {pick_order}: graph_id {graph_id} with importance: {graphs_importance[graph_id]}")
    print("\n============================= Removed graphs  =============================") # Just one time, to see which graphs were not selected
    for graph_id in graphs_importance.keys():
        if graph_id not in best_selected_graph_ids:
            print(f"Removed graph_id {graph_id} with importance: {graphs_importance[graph_id]}")

    # Now I want to print the results of the reduction on all the corresponding qlogs:
    # - The other half of the qlog that was not used for the selection of the best graphs, and
    # - The next 3 qlogs of the corresponding db, to see how well the reduced database generalizes to unseen queries.


    # Now I want to create a new database file with only the selected graphs, and save it to the output path   
    reductions_folder = Path(__file__).parent / "data/reductions"
    reductions_folder.mkdir(parents=True, exist_ok=True) 
    create_new_database_file_from_selected_graphs(str(graph_file),best_selected_graph_ids,str(output_file))

    spark_stop_start_time = time.time()
    spark.stop()
    spark_stop_time = time.time() - spark_stop_start_time

    reduction_func_time = time.time() - reduction_start_time - plotting_time

    # ================== TESTING =======================

    start_time = time.time()

    if args.tests:
        other_qlog_files = [(f"QLog{original_db_number}_{original_qlog_number} second half",query_log_file_second_half)]
        for i in range(1, 5):
            if i != int(original_qlog_number):
                other_qlog_file = query_log_file.parent / f"QLog{original_db_number}_{i}.txt"
                if other_qlog_file.exists():
                    other_qlog_files.append((other_qlog_file.name, other_qlog_file.read_text(encoding="utf-8").splitlines()))
        reduced_graphs = read_graph_database(str(output_file))
        total_coverage = 0.0
        total_queries = 0
        print(f"\n============================= Testing the reduced database on other query logs =============================")
        for qlog_label, qlog_lines in other_qlog_files:
            queries = [parse_query(line.strip()) for line in qlog_lines if line.strip()]

            coverage = query_coverage(reduced_graphs, queries)
            total_coverage += coverage * len(queries)
            total_queries += len(queries)

            print(f"Query coverage for {qlog_label}: {coverage:.2f}%")

        if total_queries:
            print(f"Average query coverage: {total_coverage / total_queries:.2f}%")

        # Evaluation plot: exact coverage and closeness on the past, the future and the other logs, in plots/runs/<run>/4_evaluation/
        save_evaluation_plot(str(graph_file), best_selected_graph_ids,
                             [("past (first half)", query_log_file_first_half)] + other_qlog_files, str(plots_folder))

    testing_func_time = time.time() - start_time

    # Timings of this run, read by the method comparison (plotting/plot_method_comparison.py)
    (plots_folder / "timings.json").write_text(json.dumps({
        "reduction_seconds": reduction_func_time,
        "selection_seconds": selection_time,
        "similarity_seconds": graph_similarity_time if args.graph_similarity else 0.0,
        "spark_startup_seconds": spark_startup_time,
        "graphs": len(graphs_importance),
        "kept": len(best_selected_graph_ids),
    }, indent=2))

    if args.performance:
        print("\n============================= Performances =============================")
        print(f"Time taken for reduction function: {reduction_func_time:.2f} seconds")
        print(f"Time taken for {args.graph_selection} selection with {args.query_coverage} query coverage time: {selection_time:.2f} seconds")
        print(f"Time taken for graph loading on Spark: {graph_creation_time:.2f} seconds")
        print(f"Time taken for QLog loading on Spark (match phase): {qlog_creation_time:.2f} seconds")
        print(f"Time taken for Spark startup: {spark_startup_time:.2f} seconds")
        print(f"Time taken for Spark shutdown: {spark_stop_time:.2f} seconds")
        if args.graph_similarity:
            print(f"Time taken for graph similarity selection: {graph_similarity_time:.2f} seconds")
        db_file_size = os.path.getsize(graph_file)
        reduced_db_file_size = os.path.getsize(output_file)
        print(f"Original database file size: {db_file_size / (1024*1024):.2f} MB")
        print(f"Reduced database file size: {reduced_db_file_size / (1024*1024):.2f} MB")
        if args.tests:
            print(f"Time taken for testing function: {testing_func_time:.2f} seconds")