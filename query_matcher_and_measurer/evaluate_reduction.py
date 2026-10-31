from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import LongType, StructField, StructType


def measure_preserved_query_answers(
    graphs_matches: DataFrame,
    selected_graph_ids: list[int],
    answers_needed_values: list[int | None],
) -> dict[int | None, float | None]:
    """
    Measure how many query answers are still available in the reduced database.

    For every query line with at least one answer in the full database, the score is
    min(answers_needed, answers kept) / min(answers_needed, answers in the full database),
    where answers_needed is how many results a user looks at. The scores are averaged over the query lines.

    Args:
        graphs_matches: DataFrame with graph_id, query_id and query_coverage, computed on the full database.
        selected_graph_ids: IDs of the graphs kept in the reduced database.
        answers_needed_values: Values of answers_needed to report, None meaning all answers.

    Returns:
        Dictionary mapping answers_needed to the average score, or None when no query has an answer.
    """

    spark = graphs_matches.sparkSession
    selected_graphs_df = spark.createDataFrame(
        [(graph_id,) for graph_id in selected_graph_ids],
        StructType([StructField("graph_id", LongType(), False)]),
    ).withColumn("is_selected", F.lit(1))

    answer_counts = (
        graphs_matches
        .where(F.col("query_coverage") == 1.0)
        .join(selected_graphs_df, on="graph_id", how="left")
        .groupBy("query_id")
        .agg(
            F.count("graph_id").alias("answers_in_full_database"),
            F.sum(F.coalesce(F.col("is_selected"), F.lit(0))).alias("answers_in_reduced_database"),
        )
        .cache()
    )

    preserved_answers = {}
    for answers_needed in answers_needed_values:
        needed_from_full_database = F.col("answers_in_full_database")
        needed_from_reduced_database = F.col("answers_in_reduced_database")
        if answers_needed is not None:
            needed_from_full_database = F.least(F.lit(answers_needed), needed_from_full_database)
            needed_from_reduced_database = F.least(F.lit(answers_needed), needed_from_reduced_database)
        preserved_answers[answers_needed] = (
            answer_counts
            .agg(F.avg(needed_from_reduced_database / needed_from_full_database).alias("score"))
            .first()["score"]
        )

    return preserved_answers
