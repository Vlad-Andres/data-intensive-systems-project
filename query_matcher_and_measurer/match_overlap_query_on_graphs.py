from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def match_graphs_with_every_sub_query(graph_df: DataFrame, query_df: DataFrame) -> DataFrame:
    """
    Match graphs with queries based on subject, predicate, object, and object_type.

    Args:
        graph_df (DataFrame): DataFrame containing graph triples.
        query_df (DataFrame): DataFrame containing query triples.

    Returns:
        DataFrame: A DataFrame containing matched graph and query triples.
    """
    graph = graph_df.alias("g")
    query = query_df.alias("q")

    return (
        graph.join(
            query,
            on=(
                (F.col("g.subject") == F.col("q.subject"))
                & (F.col("g.predicate") == F.col("q.predicate"))
                & (F.col("g.object") == F.col("q.object"))
                & (F.col("g.object_type") == F.col("q.object_type"))
            ),
            how="inner",
        )
        .select(
            F.col("g.graph_id").alias("graph_id"),

            F.col("g.subject").alias("graph_subject"),
            F.col("g.predicate").alias("graph_predicate"),
            F.col("g.object").alias("graph_object"),
            F.col("g.object_type").alias("graph_object_type"),

            F.col("q.query_id").alias("query_id"),
            F.col("q.query_order").alias("query_order"),

            F.col("q.subject").alias("query_subject"),
            F.col("q.predicate").alias("query_predicate"),
            F.col("q.object").alias("query_object"),
            F.col("q.object_type").alias("query_object_type"),
        )
    )