import argparse

from pyvis.network import Network

from graph_parser import read_graph_database
from pathlib import Path

def add_graph_to_network(network, graph_index, triples):
    def node_id(node):
        return f"g{graph_index}:{node}"

    node_title = f"graph {graph_index}"
    for source_node, label, target, is_edge in triples:
        network.add_node(node_id(source_node), label=str(source_node), title=node_title, group=graph_index)
        if is_edge:
            network.add_node(node_id(target), label=target, title=node_title, group=graph_index)
            network.add_edge(node_id(source_node), node_id(target), label=label)
        else:
            attribute_node_id = node_id(f"{source_node}:{label}")
            network.add_node(attribute_node_id, label=f'"{target}"', title=node_title, group=graph_index, shape="box")
            network.add_edge(node_id(source_node), attribute_node_id, label=label, dashes=True)


def main():
    argument_parser = argparse.ArgumentParser(description="Render graphs of a database file as interactive HTML.")
    argument_parser.add_argument("database_path")
    argument_parser.add_argument("graph_index", type=int, nargs="?", help="0-based line number of the graph; all graphs if omitted")
    argument_parser.add_argument("--output", default="graphs.html")
    arguments = argument_parser.parse_args()

    graphs = read_graph_database(arguments.database_path)
    selected_graph_indices = range(len(graphs)) if arguments.graph_index is None else [arguments.graph_index]

    network = Network(height="750px", width="100%", directed=True, cdn_resources="in_line")
    for graph_index in selected_graph_indices:
        add_graph_to_network(network, graph_index, graphs[graph_index])
    html = network.generate_html()
    Path(arguments.output).write_text(html, encoding="utf-8")
    print(f"{len(selected_graph_indices)} graph(s) written to {arguments.output}")


if __name__ == "__main__":
    main()
