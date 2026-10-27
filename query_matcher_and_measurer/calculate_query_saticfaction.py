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

    matched_path_counts = (
        matches.groupBy("query_id","query_path_id")
        .agg(F.countDistinct("query_path_order").alias("total_matched_path_transitions"))
    )

    path_coverage_df = (
        query_path_counts
        .join(
            matched_path_counts,
            on=["query_id", "query_path_id"],
            how="left"
        )
        .fillna(
            0,
            subset=["total_matched_path_transitions"]
        )
        .withColumn(
            "path_coverage",
            F.col("total_matched_path_transitions")
            / F.col("total_path_transitions")
        )
    )

    query_coverage_df = (
        path_coverage_df
        .groupBy("query_id")
        .agg(
            F.avg("path_coverage").alias("query_coverage")
        )
)   

    return (
            matches
            .join(
                path_coverage_df,
                (
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