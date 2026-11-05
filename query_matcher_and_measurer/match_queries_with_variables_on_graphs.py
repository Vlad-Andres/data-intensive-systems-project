import sys
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

SOURCE_DIRECTORY = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))

from graph_parser import parse_graph_line
from QLog_satisfaction import graph_satisfies_query, parse_query


def query_coverage_of_graph(triples, paths) -> float:
    """
    Share of the query paths satisfied by the graph.

    A query only gets 1.0 when all its paths are satisfied with one consistent set of variable bindings.
    """
    if graph_satisfies_query(triples, paths):
        return 1.0
    satisfied_paths = sum(graph_satisfies_query(triples, [path]) for path in paths)
    return min(satisfied_paths, len(paths) - 1) / len(paths)


def query_coverages_of_graph_line(graph_line: str, graph_id: int, paths_by_query_text: dict) -> list[tuple]:
    triples = parse_graph_line(graph_line)
    coverages = []
    for query_text, paths in paths_by_query_text.items():
        query_coverage = query_coverage_of_graph(triples, paths)
        if query_coverage > 0:
            coverages.append((graph_id, query_text, query_coverage))
    return coverages

def match_graphs_with_queries_using_variables(spark: SparkSession, graph_file: str, query_log_file: str) -> DataFrame:
    """
    Calculate the coverage of every query on every graph, supporting variables in the query paths.

    Each distinct query text is matched once, then joined back to every query_id (log line) that has that text.

    Returns:
        DataFrame: graph_id, query_id, query_coverage for every pair with a coverage above 0.
    """
    # cause error on execution time, and i do not see why this is needed in this functionality.
    # spark.sparkContext.addPyFile(str(SOURCE_DIRECTORY / "graph_parser.py"))
    # spark.sparkContext.addPyFile(str(SOURCE_DIRECTORY / "QLog_satisfaction.py"))

    query_lines = [
        (query_id, query_text.strip())
        for query_text, query_id in spark.sparkContext.textFile(query_log_file).zipWithIndex().collect()
        if query_text.strip()
    ]
    paths_by_query_text = spark.sparkContext.broadcast(
        {query_text: parse_query(query_text) for _, query_text in query_lines}
    )

    coverage_df = (
        spark.sparkContext.textFile(graph_file)
        .zipWithIndex()
        .flatMap(
            lambda line_index: query_coverages_of_graph_line(
                line_index[0],
                line_index[1],
                paths_by_query_text.value,
            )
        )
        .toDF(["graph_id", "query_text", "query_coverage"])
    )

    query_df = spark.createDataFrame(query_lines, ["query_id", "query_text"])

    return coverage_df.join(query_df, "query_text").select("graph_id", "query_id", "query_coverage")
