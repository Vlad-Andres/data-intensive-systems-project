import argparse
import re

from graph_parser import read_graph_database

VARIABLE_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
NODE_ID_PATTERN = re.compile(r"[0-9]+$")
LABEL_PATTERN = re.compile(r"[A-Za-z0-9]+$")


def split_unquoted(text, delimiter):
    parts = []
    start = 0
    in_quotes = False
    for index, character in enumerate(text):
        if character == '"':
            in_quotes = not in_quotes
        elif character == delimiter and not in_quotes:
            parts.append(text[start:index].strip())
            start = index + 1
    if in_quotes:
        raise ValueError("unclosed quoted string")
    parts.append(text[start:].strip())
    return parts


def parse_path(path_text):
    components = split_unquoted(path_text, ".")
    if any(not component for component in components):
        raise ValueError(f"empty component in path {path_text!r}")

    first = components[0]
    if not NODE_ID_PATTERN.fullmatch(first) and not VARIABLE_PATTERN.fullmatch(first):
        raise ValueError(f"invalid starting node in path {path_text!r}")

    for index, component in enumerate(components[1:], start=1):
        if component.startswith('"') or component.endswith('"'):
            if (
                index % 2 != 0
                or index != len(components) - 1
                or len(component) < 2
                or not (component.startswith('"') and component.endswith('"'))
            ):
                raise ValueError(f"quoted value must follow an attribute label at the end of {path_text!r}")
        elif index % 2 == 1:
            if not LABEL_PATTERN.fullmatch(component):
                raise ValueError(f"invalid edge or attribute label in path {path_text!r}")
        elif not NODE_ID_PATTERN.fullmatch(component) and not VARIABLE_PATTERN.fullmatch(component):
            raise ValueError(f"invalid node in path {path_text!r}")

    return components


def parse_query(query_text):
    path_texts = split_unquoted(query_text, ",")
    if not query_text.strip() or any(not path for path in path_texts):
        raise ValueError("query contains an empty path")
    return [parse_path(path) for path in path_texts]


def bind_node(component, node_id, bindings):
    if NODE_ID_PATTERN.fullmatch(component):
        return bindings if int(component) == node_id else None

    current = bindings.get(component)
    if current is not None:
        return bindings if current == node_id else None
    return {**bindings, component: node_id}


def graph_nodes(triples):
    nodes = {source for source, _, _, _ in triples}
    nodes.update(int(target) for _, _, target, is_edge in triples if is_edge)
    return nodes


def match_path(components, triples, bindings):
    nodes = graph_nodes(triples)
    if len(components) == 1:
        for node_id in nodes:
            result = bind_node(components[0], node_id, bindings)
            if result is not None:
                yield result
        return

    for node_id in nodes:
        result = bind_node(components[0], node_id, bindings)
        if result is not None:
            yield from match_path_from_node(components, triples, 1, node_id, result)


def match_path_from_node(components, triples, index, current_node, bindings):
    if index >= len(components):
        yield bindings
        return

    label = components[index]
    if index == len(components) - 1:
        if any(
            source == current_node and edge_label == label and is_edge
            for source, edge_label, _, is_edge in triples
        ):
            yield bindings
        return

    next_component = components[index + 1]
    if next_component.startswith('"') and next_component.endswith('"'):
        value = next_component[1:-1]
        if any(
            source == current_node and attribute == label and target == value and not is_edge
            for source, attribute, target, is_edge in triples
        ):
            yield bindings
        return

    for source, edge_label, target, is_edge in triples:
        if source != current_node or edge_label != label or not is_edge:
            continue
        next_bindings = bind_node(next_component, int(target), bindings)
        if next_bindings is not None:
            yield from match_path_from_node(
                components, triples, index + 2, int(target), next_bindings
            )


def graph_satisfies_query(triples, paths):
    bindings_to_check = [{}]
    for path in paths:
        next_bindings = []
        for bindings in bindings_to_check:
            next_bindings.extend(match_path(path, triples, bindings))
        if not next_bindings:
            return False
        bindings_to_check = next_bindings
    return bool(bindings_to_check)


def query_coverage(graphs, queries):
    if not queries:
        return 0.0
    covered = sum(
        any(graph_satisfies_query(graph, query) for graph in graphs)
        for query in queries
    )
    return 100.0 * covered / len(queries)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate the percentage of query-log queries satisfied by a graph database."
    )
    parser.add_argument("database_path", help="path to the graph database")
    parser.add_argument("query_log_path", help="path to the query log")
    arguments = parser.parse_args()

    graphs = read_graph_database(arguments.database_path)
    queries = []
    with open(arguments.query_log_path, encoding="utf-8") as query_log:
        for line_number, line in enumerate(query_log, start=1):
            if not line.strip():
                continue
            try:
                queries.append(parse_query(line.strip()))
            except ValueError as error:
                parser.error(f"{arguments.query_log_path}:{line_number}: {error}")

    print(f"{query_coverage(graphs, queries):.2f}%")


if __name__ == "__main__":
    main()