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

PATH_SPLIT = re.compile(r',(?=(?:[^"]*"[^"]*")*[^"]*$)')

TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[^."]+')

def classify_object(object_: str) -> tuple[str, str]:
    if len(object_) >= 2 and object_[0] == '"' and object_[-1] == '"':
        return object_[1:-1], "attribute"
    return object_, "relation"

def parse_graph_line(line: str) -> list[tuple]:
    tuples = []
    for subject, predicate, object_ in TRIPLE_PATTERN_REGEX_GRAPH.findall(line):
        object_, tuple_type = classify_object(object_)
        tuples.append((subject, predicate, object_, tuple_type))
    return tuples

def parse_query_line(line: str) ->list[tuple]:
    tuples = []
    for path_id, path in enumerate(PATH_SPLIT.split(line.strip())):
        tokens = TOKEN.findall(path)

        for path_order, i in enumerate(range(0, len(tokens) - 2, 2), start=1):
            subject, predicate, object_ = tokens[i:i + 3]
            object_, tuple_type = classify_object(object_)
            tuples.append((path_id, path_order, subject, predicate, object_, tuple_type))
    return tuples

def create_graphs_dataframe(spark: SparkSession, file_path: str) -> DataFrame:

    lines = spark.sparkContext.textFile(file_path)

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
                in parse_graph_line(line_index[0])
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
                    path_id,
                    path_order,
                    subject,
                    predicate,
                    obj,
                    tuple_type
                )
                for path_id,path_order,subject, predicate, obj, tuple_type
                in parse_query_line(line_index[0])
            ]
        )
    )

    query_schema = StructType([
        StructField("query_id", LongType(), False),
        StructField("path_id", LongType(), False),
        StructField("path_order", LongType(), False),
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