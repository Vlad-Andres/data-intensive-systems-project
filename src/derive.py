import argparse
import itertools
import random
import re

from graph_parser import read_graph_database, write_graph_database

HIGH_ONLY_EDGES = {"produced", "wrote", "playedRole", "inMovie"}
QUERY_PATH_PATTERN = re.compile(r'(?:"[^"]*"|[^,"])+')
PATH_COMPONENT_PATTERN = re.compile(r'"[^"]*"|[^."]+')


def pick_graphs(graphs, graph_count, seed):
    """The same seed and count always pick the same graphs, kept in file order."""
    picked = sorted(random.Random(seed).sample(range(len(graphs)), graph_count))
    return [graphs[graph_index] for graph_index in picked]


def drop_high_semantic(triples):
    """Remove the high-only edges, the role nodes and their attributes."""
    role_nodes = {int(target) for _, label, target, is_edge in triples if is_edge and label == "playedRole"}
    return [
        (source_node, label, target, is_edge)
        for source_node, label, target, is_edge in triples
        if label not in HIGH_ONLY_EDGES and source_node not in role_nodes
    ]


def limit_edges(triples, max_edges):
    """Keep max_edges edges, taken label by label in turn (each label in file order) so that every
    edge label survives when it fits, plus the attributes of the nodes they still connect."""
    edges_by_label = {}
    for triple in triples:
        if triple[3]:
            edges_by_label.setdefault(triple[1], []).append(triple)
    rounds = itertools.zip_longest(*edges_by_label.values())
    kept = set(itertools.islice((edge for edge_round in rounds for edge in edge_round if edge), max_edges))
    edges = [triple for triple in triples if triple in kept]
    connected_nodes = {source_node for source_node, _, _, _ in edges} | {int(target) for _, _, target, _ in edges}
    attributes = [triple for triple in triples if not triple[3] and triple[0] in connected_nodes]
    return edges + attributes


def derive(graphs, graph_count, max_edges, semantic, seed):
    derived = []
    for triples in pick_graphs(graphs, graph_count, seed):
        if semantic == "low":
            triples = drop_high_semantic(triples)
        derived.append(limit_edges(triples, max_edges))
    return derived


def query_labels(query):
    """Edge labels and attribute names of a query: every second component of each path."""
    labels = set()
    for path in QUERY_PATH_PATTERN.findall(query):
        components = PATH_COMPONENT_PATTERN.findall(path.strip())
        labels.update(components[1::2])
    return labels


def filter_query_log(query_log_path, output_path, graphs):
    """Keep only the queries whose labels all exist in the derived graphs."""
    database_labels = {label for triples in graphs for _, label, _, _ in triples}
    with open(query_log_path, encoding="utf-8") as query_log:
        queries = [line.strip() for line in query_log if line.strip()]
    kept = [query for query in queries if query_labels(query) <= database_labels]
    with open(output_path, "w", encoding="utf-8") as output:
        output.writelines(query + "\n" for query in kept)
    return len(kept), len(queries)


def main():
    argument_parser = argparse.ArgumentParser(description="Cut one dataset version out of the big database.")
    argument_parser.add_argument("database_path")
    argument_parser.add_argument("--graphs", type=int, required=True, help="number of graphs to pick")
    argument_parser.add_argument("--max-edges", type=int, required=True, help="maximum number of edges per graph")
    argument_parser.add_argument("--semantic", choices=("low", "high"), required=True)
    argument_parser.add_argument("--seed", type=int, default=1, help="same seed = same picked graphs")
    argument_parser.add_argument("--output", required=True)
    argument_parser.add_argument("--qlog", help="query log to filter for this version")
    argument_parser.add_argument("--qlog-output", help="where to write the filtered query log")
    arguments = argument_parser.parse_args()

    graphs = derive(read_graph_database(arguments.database_path), arguments.graphs, arguments.max_edges,
                    arguments.semantic, arguments.seed)
    write_graph_database(arguments.output, graphs)
    print(f"{len(graphs)} graph(s) written to {arguments.output}")

    if arguments.qlog:
        kept, total = filter_query_log(arguments.qlog, arguments.qlog_output, graphs)
        print(f"{kept}/{total} queries written to {arguments.qlog_output}")


if __name__ == "__main__":
    main()
