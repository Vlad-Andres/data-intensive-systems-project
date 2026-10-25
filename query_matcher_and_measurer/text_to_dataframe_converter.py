import re
from pyspark.sql import DataFrame, DataFrame, SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    StringType
)

TRIPLE_PATTERN_REGEX_GRAPH = re.compile(
    r'<([^,<>]+),([^,<>]+),'
    r'("(?:\\.|[^"\\])*"|[^,<>]+)>'
)

TRIPLE_PATTERN_REGEX_QUERY = re.compile(
    r'([^,.]+)\.([^,.]+)\.'
    r'("(?:\\.|[^"\\])*"|[^,.]+)'
)

def parse_line(line: str, line_type: str):
    if line_type == "graph":
        pattern = TRIPLE_PATTERN_REGEX_GRAPH
    else:
        pattern = TRIPLE_PATTERN_REGEX_QUERY

    tuples = []

    for order_index, match in enumerate(pattern.finditer(line)):
        subject = match.group(1)
        predicate = match.group(2)
        object_ = match.group(3)

        # Determine if it is a attribute or relation based on if it has quotes or not
        if object_.startswith('"') and object_.endswith('"'):
            tuple_type = "attribute"
            object_ = object_[1:-1]  # Remove the quotes
        else:
            tuple_type = "relation"

        if line_type == "graph":
            tuples.append((subject, predicate, object_, tuple_type))
        elif line_type == "query":
            tuples.append((order_index,subject, predicate, object_, tuple_type))

    return tuples

def create_graphs_dataframe(spark: SparkSession, file_path: str) -> DataFrame:

    lines = spark.sparkContext.textFile(file_path)

    print(f"Number of lines in the file: {lines.count()}")  # Debugging line

    graphs = (
        lines.zipWithIndex()
        .flatMap(
            lambda line_index: [
                (
                    line_index[1],
                    subject,
                    predicate,
                    obj,
                    tuple_type
                )
                for  subject, predicate, obj, tuple_type
                in parse_line(line_index[0], "graph")
            ]
        )
    )

    graph_schema = StructType([
        StructField("graph_id", LongType(), False),
        StructField("subject", StringType(), False),
        StructField("predicate", StringType(), False),
        StructField("object", StringType(), False),
        StructField("object_type", StringType(), False)
    ])

    graphs_dataframe = spark.createDataFrame(
        graphs,
        schema=graph_schema
    )
    return graphs_dataframe

def create_query_log(spark: SparkSession, file_path: str) -> DataFrame:
    lines = spark.sparkContext.textFile(file_path)

    queries = (
        lines.zipWithIndex()
        .flatMap(
            lambda line_index: [
                (
                    line_index[1],
                    order_index,
                    subject,
                    predicate,
                    obj,
                    tuple_type
                )
                for order_index,subject, predicate, obj, tuple_type
                in parse_line(line_index[0], "query")
            ]
        )
    )

    query_schema = StructType([
        StructField("query_id", LongType(), False),
        StructField("query_order", LongType(), False),
        StructField("subject", StringType(), False),
        StructField("predicate", StringType(), False),
        StructField("object", StringType(), False),
        StructField("object_type", StringType(), False)
    ])

    queries_dataframe = spark.createDataFrame(
        queries,
        schema=query_schema
    )

    return queries_dataframe