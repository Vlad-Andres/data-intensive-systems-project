from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def convert_to_dict_graph_id_and_importance(importance_df):
    """
    Convert a DataFrame with graph_id and importance columns to a dictionary.

    Args:
        importance_df: DataFrame with columns "graph_id" and "importance".

    Returns:
        Dictionary mapping graph_id to importance.
    """

    return dict(
        importance_df
        .select("graph_id", "importance")
        .rdd
        .map(
            lambda row: (
                row["graph_id"],
                float(row["importance"]),
            )
        )
        .collect()
    )

def add_empty_matching_graphs_back_with_0_importance(graph_df, importance_df):
    return (
        graph_df
        .select("graph_id")
        .distinct()
        .join(
            importance_df,
            on="graph_id",
            how="left",
        )
        .select(
            "graph_id",
            F.coalesce(
                F.col("importance"),
                F.lit(0.0),
            ).alias("importance"),
        )
    )

def measure_graph_importance_based_on_full_query_coverage(
    graph_df: DataFrame,
    graphs_matches: DataFrame,
) -> dict[int, float]:
    """
    Measure graph importance based on full query coverage.

    Each fully matched query contributes 1.0.

    Args:
        graph_df: DataFrame containing all graphs.
        graphs_matches: DataFrame containing matches between graphs and queries.

    Returns:
        Dictionary mapping graph_id to importance.
        Every graph receives a score, including graphs with zero matches.
    """

    importance_df = (
        graphs_matches
        .where(F.col("query_coverage") == 1.0)
        .select("graph_id", "query_id")
        .distinct()
        .groupBy("graph_id")
        .agg(F.count("query_id").cast("double").alias("importance"))
    )

    importance_df = add_empty_matching_graphs_back_with_0_importance(graph_df, importance_df)

    return convert_to_dict_graph_id_and_importance(importance_df)

def measure_graph_based_on_partial_query_coverage(
    graph_df: DataFrame,
    graphs_matches: DataFrame,
) -> dict[int, float]:
    """
    Measure graph importance based on partial query coverage.

    Graph importance is calculated as the average query coverage for each query.

    Args:
        graph_df: DataFrame containing all graphs.
        graphs_matches: DataFrame containing matches between graphs and queries.

    Returns:
        Dictionary mapping graph_id to importance.
        Every graph receives a score, including graphs with zero matches.
    """

    importance_df = (
        graphs_matches
        .groupBy("graph_id", "query_id")
        .agg(F.first("query_coverage").alias("query_coverage_first_value"))
        .groupBy("graph_id")
        .agg(F.avg("query_coverage_first_value").alias("importance"))
    )

    importance_df = add_empty_matching_graphs_back_with_0_importance(graph_df, importance_df)

    return convert_to_dict_graph_id_and_importance(importance_df)