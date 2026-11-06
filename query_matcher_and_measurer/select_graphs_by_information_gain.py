import heapq

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def select_graphs_by_information_gain(graphs_df: DataFrame,graphs_importance: dict[int, float],selected_graph_ids: list[int],similarity_budget: float) -> list[int]:
    """
    Refine a selection so part of the keep "budget" goes to the graphs that add the most new information to the DB, without taking the queries into acount.

    The number of selected graphs does not change. The information a graph adds is the
    number of its triples that no kept graph contains yet, so the query log plays no part in this step.
   Initially keeps graphs with importance greater than zero, 
    then fills the remaining slots by choosing graphs based on the number of new triples they contribute.
    At least one reserved slot when the budget is nonzero. So with a share of 0, still reserves one slot.

    Args:
        graphs_df: DataFrame with one row per triple: graph_id, subject, predicate, object, object_type.
        graphs_importance: A dictionary mapping every graph ID to its importance score.
        selected_graph_ids: The IDs picked by importance, most valuable first.
        similarity_budget: The budget reserved for information gain. At least one slot is reserved.

    Returns:
        list[int]: The selected graph IDs in pick order.
    """
    budget = len(selected_graph_ids)
    reserved_slots = min(budget, max(1, int(budget * similarity_budget)))
    important_graph_ids = [graph_id for graph_id in selected_graph_ids if graphs_importance[graph_id] > 0]
    selected_graphs = important_graph_ids[:budget - reserved_slots]

    triple_columns = ["subject", "predicate", "object", "object_type"]
    triples_by_graph = {
        row["graph_id"]: {tuple(triple) for triple in row["triples"]}
        for row in graphs_df
        .groupBy("graph_id")
        .agg(F.collect_set(F.struct(*triple_columns)).alias("triples"))
        .collect()
    }

    kept_triples = set().union(*(triples_by_graph[graph_id] for graph_id in selected_graphs))
    already_selected = set(selected_graphs)

    candidates = [
        (-len(triples - kept_triples), -graphs_importance[graph_id], graph_id)
        for graph_id, triples in triples_by_graph.items()
        if graph_id not in already_selected
    ]
    heapq.heapify(candidates)

    while candidates and len(selected_graphs) < budget:
        negative_stored_gain, negative_importance, graph_id = heapq.heappop(candidates)
        current_gain = len(triples_by_graph[graph_id] - kept_triples)
        if current_gain < -negative_stored_gain:
            heapq.heappush(candidates, (-current_gain, negative_importance, graph_id))
            continue
        selected_graphs.append(graph_id)
        kept_triples |= triples_by_graph[graph_id]

    return selected_graphs
