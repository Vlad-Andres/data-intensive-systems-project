from pyspark.sql import DataFrame
import pandas as pd
import pyspark.sql.functions as F

def calculate_query_satisfaction(matches: DataFrame, query_df: DataFrame) -> DataFrame:
    """
    Calculate first the path coverage percentage
    Calculate secondly the query satisfaction percentage based on the path coverage percentage.

    Args:
        matches (DataFrame): A DataFrame containing the matches between graphs and queries.
        query_df (DataFrame): A DataFrame containing the queries.

    Returns:
        DataFrame: A DataFrame containing the satisfaction of each query.
    """

    query_path_counts = (
        query_df.groupBy("query_id", F.col("path_id").alias("query_path_id"))
        .agg(F.countDistinct("path_order").alias("total_path_transitions"))
    )

    query_n_paths = (
        query_path_counts
        .groupBy("query_id")
        .agg(F.count("*").alias("n_paths"))
    )

    matched_path_counts = (
        matches.groupBy("graph_id","query_id","query_path_id")
        .agg(F.countDistinct("query_path_order").alias("total_matched_path_transitions"))
    )

    path_coverage_df = (
        matched_path_counts
        .join(query_path_counts, ["query_id", "query_path_id"], "inner")
        .withColumn(
            "path_coverage",
            F.col("total_matched_path_transitions") / F.col("total_path_transitions"),
        )
    )

    query_coverage_df = (
        path_coverage_df
        .groupBy("graph_id", "query_id")
        .agg(F.sum("path_coverage").alias("cov_sum"))
        .join(query_n_paths, "query_id")
        .withColumn("query_coverage", F.col("cov_sum") / F.col("n_paths"))
        .select("graph_id", "query_id", "query_coverage")
    )

    return (
            matches
            .join(
                path_coverage_df,
                (
                    matches["graph_id"] == path_coverage_df["graph_id"]
                ) & (
                    matches["query_id"] == path_coverage_df["query_id"]
                ) & (
                    matches["query_path_id"] == path_coverage_df["query_path_id"]
                ),
                how="left"
            )
            .join(
                query_coverage_df,
                on="query_id",
                how="left"
            )
            .select(
                matches["*"],
                path_coverage_df["path_coverage"],
                query_coverage_df["query_coverage"]
            )
 
        )