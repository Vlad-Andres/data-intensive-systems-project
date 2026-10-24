import argparse
import re

from graph_parser import read_graph_database

NODE_VARIABLE_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def split_unquoted(text, delimiter):
    """Split on a delimiter outside double-quoted string literals."""
    parts = []
    start = 0
    in_string = False
    for index, character in enumerate(text):
        if character == '"':
            in_string = not in_string
        elif character == delimiter and not in_string:
            parts.append(text[start:index].strip())
            start = index + 1
    if in_string:
        raise ValueError("unterminated quoted string")
    parts.append(text[start:].strip())
    return parts


def parse_path(path):
    components = split_unquoted(path, ".")
    if not components or any(not component for component in components):
        raise ValueError("path contains an empty component")

    for index, component in enumerate(components):
        quoted = component.startswith('"') and component.endswith('"') and len(component) >= 2
        if component.startswith('"') != component.endswith('"'):
            raise ValueError(f"invalid quoted component {component!r}")

        if quoted:
            if index % 2 != 0 or index != len(components) - 1:
                raise ValueError("a quoted value must be the final path component")
        elif index % 2 == 0:
            if not component.isdigit() and not NODE_VARIABLE_PATTERN.fullmatch(component):
                raise ValueError(f"invalid node identifier {component!r}")
        elif not component.isalnum():
            raise ValueError(f"invalid edge or attribute label {component!r}")

    return components


def parse_query(query):
    paths = split_unquoted(query, ",")
    if not paths or any(not path for path in paths):
        raise ValueError("query contains an empty path")
    return [parse_path(path) for path in paths]


def graph_nodes(graph):
    nodes = set()
    for source, _, target, is_edge in graph:
        nodes.add(str(source))
        if is_edge:
            nodes.add(str(target))
    return nodes


def path_satisfied(path, graph, nodes=None):
    """Return whether one graph contains a walk matching a query path."""
    nodes = graph_nodes(graph) if nodes is None else nodes
    first = path[0]
    if first.isdigit():
        starts = [(str(int(first)), {})]
        starts = [(node, bindings) for node, bindings in starts if node in nodes]
    else:
        starts = [(node, {first: node}) for node in nodes]

    states = starts
    for label_index in range(1, len(path), 2):
        label = path[label_index]
        terminal_label = label_index == len(path) - 1
        next_component = None if terminal_label else path[label_index + 1]
        next_states = []

        for current_node, bindings in states:
            for source, edge_label, target, is_edge in graph:
                if str(source) != current_node or edge_label != label:
                    continue

                if terminal_label:
                    if is_edge:
                        return True
                    continue

                if next_component.startswith('"'):
                    if not is_edge and target == next_component[1:-1]:
                        return True
                    continue

                terminal_component = label_index + 1 == len(path) - 1
                if terminal_component and not next_component.isdigit() and not is_edge:
                    if next_component not in bindings or bindings[next_component] == target:
                        return True
                    continue

                if not is_edge:
                    continue
                target_node = str(target)
                if next_component.isdigit():
                    if target_node == str(int(next_component)):
                        next_states.append((target_node, bindings))
                elif next_component not in bindings or bindings[next_component] == target_node:
                    updated_bindings = bindings | {next_component: target_node}
                    next_states.append((target_node, updated_bindings))

        if terminal_label:
            return False
        states = next_states
        if not states:
            return False

    return bool(states)


def query_satisfied(query, graphs):
    paths = parse_query(query)
    for graph in graphs:
        nodes = graph_nodes(graph)
        if all(path_satisfied(path, graph, nodes) for path in paths):
            return True
    return False


def validate_query_log(database_path, query_log_path):
    graphs = read_graph_database(database_path)
    failures = []

    with open(query_log_path, encoding="utf-8") as query_log:
        for line_number, line in enumerate(query_log, start=1):
            query = line.strip()
            if not query:
                continue
            try:
                satisfied = query_satisfied(query, graphs)
            except ValueError as error:
                failures.append((line_number, query, f"invalid query: {error}"))
                continue
            if not satisfied:
                failures.append((line_number, query, "no graph satisfies every path"))

    return failures


def main():
    parser = argparse.ArgumentParser(
        description="Check that every query in a query log is satisfied by a graph in a database."
    )
    parser.add_argument("database_path", help="path to the graph database")
    parser.add_argument("query_log_path", help="path to the query log")
    arguments = parser.parse_args()

    try:
        failures = validate_query_log(arguments.database_path, arguments.query_log_path)
    except OSError as error:
        parser.error(str(error))

    if not failures:
        print("👌Satisfied")
        return

    print(f"❌Unsatisfied: {len(failures)} failing query/queries")
    for line_number, query, reason in failures:
        print(f"Line {line_number}: {reason}: {query}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
