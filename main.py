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
    parser.add_argument("--query_coverage", type=str, default="full", choices=["full", "partial","distributed"], help="Query coverage type: 'full' or 'partial'. or 'distributed'" )
    parser.add_argument("--graph_selection", type=str, default="simple", choices=["simple", "rounds"], help="Selection method to use: 'simple' or 'rounds'.")
    parser.add_argument("--importance_threshold", type=float, default=0.9, help="Threshold for selecting graphs based on importance.")
    parser.add_argument("--check_qlog_satisfaction", type=bool, default=False, help="Whether to check if all queries are satisfied by the selected graphs.")
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
    if args.graph_similarity:
        output_file += "_graph_similarity"
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

    # I assume that all the queries are satisfied
    satisfied_matches: DataFrame = spark.createDataFrame([], schema="query_id: int, graph_id: int")

    # I want to halve the qlog file: 
    # half will be used for the selection of the best graphs, and 
    # the other half will be used to test the reducted db

    query_log_file_lines = query_log_file.read_text(encoding="utf-8").splitlines()
    half_index = len(query_log_file_lines) // 2
    query_log_file_first_half = query_log_file_lines[:half_index]
    query_log_file_second_half = query_log_file_lines[half_index:]

    # QLog Goes Into a Spark Dataframe

    qlog_creation_start_time = time.time()
    qlog_creation_time = 0

    if args.check_qlog_satisfaction:
        satisfied_matches: DataFrame = match_graphs_with_queries_using_variables(spark, str(graph_file), str(query_log_file_first_half))
        qlog_creation_time = time.time() - qlog_creation_start_time
        #print(f"Match table with query coverage for each graph and query (pairs with coverage 0 are left out):")
        #satisfied_matches.orderBy("query_id", "graph_id").show(50, truncate=False)
    else:
        # If we are not checking for satisfaction, we assume all queries are satisfied by all graphs
        query_ids = spark.createDataFrame([(i,) for i, line in enumerate(query_log_file_first_half) if line.strip()],["query_id"],)
        graph_ids = graphs_df.select("graph_id")
        satisfied_matches = query_ids.crossJoin(graph_ids).withColumn("query_coverage", F.lit(1.0))
        qlog_creation_time = time.time() - qlog_creation_start_time



    graphs_importance: dict[int, float] = {}

    # Determine the importance measure function based on the presence of subqueries
    measure_function = None
    if args.query_coverage == "full":
        measure_function = measure_graph_importance_based_on_full_query_coverage
    elif args.query_coverage == "partial":
        measure_function = measure_graph_based_on_partial_query_coverage
    elif args.query_coverage == "distributed":
        measure_function = measure_graph_importance_based_on_current_queries

    # Calculate the importance of each graph based on the selected measure function   
    
    selection_start_time = time.time()

    graphs_importance = measure_function(graphs_df, satisfied_matches)
    importance_threshold = args.importance_threshold
    if args.graph_similarity and int(len(graphs_df) * args.importance_threshold)<1:
        importance_threshold = 2 / len(graphs_df)

    if args.graph_selection == "simple":
        best_selected_graph_ids = select_best_graphs_by_importance_threshold(graphs_importance, importance_threshold)
    elif args.graph_selection == "rounds":
        best_selected_graph_ids = select_best_graphs_greedily(graphs_importance, satisfied_matches, importance_threshold)

    selection_time = time.time() - selection_start_time

    ## Here I want to integrate graph similarity in the choice of the worse graphs:
    #  between the 2 lowest scoring graphs, which is adding the least new information to the selected graphs,
    #  and thus is the most similar to the already selected graphs, should be removed first.

    if args.graph_similarity:
        # Implement graph similarity logic here
        pass  # Placeholder for graph similarity logic

    print(f"\n============================= Selected graph IDs in pick order: =============================")
    for pick_order, graph_id in enumerate(best_selected_graph_ids, start=1):
        print(f"Pick {pick_order}: graph_id {graph_id} with importance: {graphs_importance[graph_id]}")
    print("\n============================= Removed graphs (not selected) =============================") # Just one time, to see which graphs were not selected
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

    reduction_func_time = time.time() - reduction_start_time

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

    testing_func_time = time.time() - start_time

    if args.performance:
        print("\n============================= Performances =============================")
        print(f"Time taken for reduction function: {reduction_func_time:.2f} seconds")
        print(f"Time taken for {args.graph_selection} selection with {args.query_coverage} query coverage time: {selection_time:.2f} seconds")
        print(f"Time taken for graph creation: {graph_creation_time:.2f} seconds")
        print(f"Time taken for QLog creation: {qlog_creation_time:.2f} seconds")
        print(f"Time taken for Spark startup: {spark_startup_time:.2f} seconds")
        print(f"Time taken for Spark shutdown: {spark_stop_time:.2f} seconds")
        db_file_size = os.path.getsize(graph_file)
        reduced_db_file_size = os.path.getsize(output_file)
        print(f"Original database file size: {db_file_size / (1024*1024):.2f} MB")
        print(f"Reduced database file size: {reduced_db_file_size / (1024*1024):.2f} MB")
        if args.tests:
            print(f"Time taken for testing function: {testing_func_time:.2f} seconds")