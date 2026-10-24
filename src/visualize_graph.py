import argparse
import math
from collections import Counter

from pyvis.network import Network

from graph_parser import read_graph_database
from pathlib import Path

GRID_CELL = 400


def grid_positions(cell, columns, triples):
    """Hub node in the middle of the graph's grid cell, the other nodes on a circle around it."""
    degree = Counter()
    for source_node, _, target, is_edge in triples:
        degree[str(source_node)] += 1
        if is_edge:
            degree[target] += 1
    hub, _ = degree.most_common(1)[0]
    others = [node for node in degree if node != hub]
    center_x = (cell % columns) * GRID_CELL
    center_y = (cell // columns) * GRID_CELL
    positions = {hub: (center_x, center_y)}
    for i, node in enumerate(others):
        angle = 2 * math.pi * i / len(others)
        positions[node] = (center_x + GRID_CELL * 0.4 * math.cos(angle), center_y + GRID_CELL * 0.4 * math.sin(angle))
    return positions


def add_graph_to_network(network, graph_index, triples, positions=None):
    def node_id(node):
        return f"g{graph_index}:{node}"

    def position(node):
        if positions is None:
            return {}
        x, y = positions[str(node)]
        return {"x": x, "y": y, "physics": False}

    node_title = f"graph {graph_index}"
    for source_node, label, target, is_edge in triples:
        network.add_node(node_id(source_node), label=str(source_node), title=node_title, group=graph_index,
                         **position(source_node))
        if is_edge:
            network.add_node(node_id(target), label=target, title=node_title, group=graph_index, **position(target))
            network.add_edge(node_id(source_node), node_id(target), label=label)
        else:
            attribute_node_id = node_id(
                f"{source_node}:{label}:{target}"
            )
            network.add_node(attribute_node_id, label=f'"{target}"', title=node_title, group=graph_index, shape="box")
            network.add_edge(node_id(source_node), attribute_node_id, label=label, dashes=True)


def main():
    argument_parser = argparse.ArgumentParser(description="Render graphs of a database file as interactive HTML.")
    argument_parser.add_argument("database_path")
    argument_parser.add_argument("graph_indices", type=int, nargs="*", help="0-based line numbers of the graphs; all graphs if omitted")
    argument_parser.add_argument("--output", default="graphs.html")
    argument_parser.add_argument("--height", default="750px", help="canvas height, e.g. 1500px")
    argument_parser.add_argument("--overview", action="store_true",
                                 help="no attributes, each graph in its own grid cell, no physics (fast for many graphs)")
    arguments = argument_parser.parse_args()

    graphs = read_graph_database(arguments.database_path)
    selected_graph_indices = arguments.graph_indices or range(len(graphs))
    columns = math.ceil(math.sqrt(len(selected_graph_indices)))

    network = Network(height=arguments.height, width="100%", directed=True, cdn_resources="in_line")
    if arguments.overview:
        network.toggle_physics(False)
    for cell, graph_index in enumerate(selected_graph_indices):
        triples = graphs[graph_index]
        positions = None
        if arguments.overview:
            triples = [triple for triple in triples if triple[3]]
            positions = grid_positions(cell, columns, triples)
        add_graph_to_network(network, graph_index, triples, positions)
    html = network.generate_html()
    Path(arguments.output).write_text(html, encoding="utf-8")
    print(f"{len(selected_graph_indices)} graph(s) written to {arguments.output}")


if __name__ == "__main__":
    main()
