from pyspark.pandas import DataFrame

def select_best_graphs_by_importance_threshold(graphs: dict[int, float], importance_threshold: float):
    """
    Select the best graphs based on importance threshold.

    Args:
        graphs (dict[int, float]): A dictionary mapping graph IDs to their importance scores.
        importance_threshold (float): The threshold for selecting graphs.

    Returns:
        list[int]: A list of selected graph IDs that meet the importance threshold.
    """
    ordered_graphs = sorted(graphs.items(), key=lambda item: item[1], reverse=True)
    select_amount = int(len(ordered_graphs) * importance_threshold)
    selected_graphs = [graph_id for graph_id, _ in ordered_graphs[:select_amount]]
    return selected_graphs
