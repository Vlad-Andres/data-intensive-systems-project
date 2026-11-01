import heapq
from collections import Counter, defaultdict
from functools import lru_cache

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


@lru_cache(maxsize=None)
def harmonic_number(count: int) -> float:
    return sum(1.0 / index for index in range(1, count + 1))


def select_best_graphs_greedily(graphs: dict[int, float], graphs_matches: DataFrame, importance_threshold: float):
    """
    Select graphs one at a time, always taking the graph that adds the most value on top of the graphs already kept.

    The k-th kept answer to a query line is worth 1 / (k * H(n)), where n is the number of graphs that fully
    answer it and H(n) = 1 + 1/2 + ... + 1/n, so all answers of a query line add up to 1 and a second answer
    is worth half the first. Gains only drop as graphs are kept, so stale gains are recomputed lazily.
    Equal gains are ordered by importance.

    Args:
        graphs (dict[int, float]): A dictionary mapping every graph ID to its importance score.
        graphs_matches (DataFrame): graph_id, query_id and query_coverage for every pair with a coverage above 0.
        importance_threshold (float): The share of graphs to select.

    Returns:
        list[int]: The selected graph IDs in pick order.
    """
    select_amount = int(len(graphs) * importance_threshold)

    answered_query_ids_by_graph = defaultdict(list)
    for row in graphs_matches.where(F.col("query_coverage") == 1.0).select("graph_id", "query_id").collect():
        answered_query_ids_by_graph[row["graph_id"]].append(row["query_id"])

    answering_graph_count_by_query = Counter(
        query_id for query_ids in answered_query_ids_by_graph.values() for query_id in query_ids
    )
    kept_answer_count_by_query = Counter()

    def gain(graph_id: int) -> float:
        return sum(
            1.0 / ((kept_answer_count_by_query[query_id] + 1) * harmonic_number(answering_graph_count_by_query[query_id]))
            for query_id in answered_query_ids_by_graph[graph_id]
        )

    candidates = [(-gain(graph_id), -importance, graph_id) for graph_id, importance in graphs.items()]
    heapq.heapify(candidates)

    selected_graphs = []
    while candidates and len(selected_graphs) < select_amount:
        negative_stored_gain, negative_importance, graph_id = heapq.heappop(candidates)
        current_gain = gain(graph_id)
        if current_gain < -negative_stored_gain:
            heapq.heappush(candidates, (-current_gain, negative_importance, graph_id))
            continue
        selected_graphs.append(graph_id)
        kept_answer_count_by_query.update(answered_query_ids_by_graph[graph_id])

    return selected_graphs
