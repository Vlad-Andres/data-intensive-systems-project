
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

def measure_graph_importance_based_on_query_exsisting_paths(
    graph_df: DataFrame,
    graphs_matches: DataFrame,
) -> dict[int, float]:
    """
    Measure graph importance based on query coverage.

    Each matching query path contributes 1.0.

    Args:
        graph_df: DataFrame containing all graphs.
        graphs_matches: DataFrame containing matches between graphs and queries.

    Returns:
        Dictionary mapping graph_id to importance.
        Every graph receives a score, including graphs with zero matches.
    """

    importance_df = (
        graphs_matches
        .groupBy("graph_id")
        .agg(
            F.count("query_path_id").alias("importance")
        )
    )

    importance_df = add_empty_matching_graphs_back_with_0_importance(graph_df, importance_df)

    return convert_to_dict_graph_id_and_importance(importance_df)


def measure_graph_importance_based_on_exsisting_paths_and_query_size(
    graph_df: DataFrame,
    graphs_matches: DataFrame,
    query_df: DataFrame,
    query_size_importance: float = 0.1,
) -> dict[int, float]:
    """
    Measure graph importance based on query coverage,
    weighted by query size.

    Each matching query triple contributes:

        1.0 + query_size_importance * query_size

    Args:
        graph_df: DataFrame containing all graphs.
        graphs_matches: DataFrame containing matches between graphs and queries.
        query_df: DataFrame containing all queries.
        query_size_importance: Non-negative weight applied to query size.
    
    Returns:
        Dictionary mapping graph_id to importance.
        Every graph receives a score, including graphs with zero matches.
    """

    if query_size_importance < 0:
        raise ValueError(
            "query_size_importance must be non-negative."
        )

    query_sizes = (
        query_df
        .groupBy("query_id")
        .agg(
            F.count("path_id").alias("query_size")
        )
        .select(
            "query_id",
            "query_size",
            (
                F.lit(1.0)
                + F.lit(float(query_size_importance))
                * F.col("query_size")
            ).alias("query_importance"),
        )
    )

    weighted_matches = (
        graphs_matches
        .join(
            query_sizes.select(
                "query_id",
                "query_importance",
            ),
            on="query_id",
            how="inner",
        )
        .select(
            "graph_id",
            "query_id",
            "query_path_id",
            "query_path_order",
            "query_importance",
        )
    )

    importance_df = (
        weighted_matches
        .groupBy("graph_id")
        .agg(
            F.sum("query_importance").alias("importance")
        )
    )

    importance_df = add_empty_matching_graphs_back_with_0_importance(graph_df, importance_df)

    return convert_to_dict_graph_id_and_importance(importance_df)

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