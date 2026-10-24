import re

TRIPLE_PATTERN = re.compile(r'<\s*(\d+)\s*,\s*([A-Za-z0-9]+)\s*,\s*(\d+|"[^"]*")\s*>')


def parse_graph_line(graph_line):
    triples = []
    for source_node, label, third_element in TRIPLE_PATTERN.findall(graph_line):
        is_edge = not third_element.startswith('"')
        target = third_element if is_edge else third_element.strip('"')
        triples.append((int(source_node), label, target, is_edge))
    return triples


def read_graph_database(database_path):
    with open(database_path, "r", encoding="utf-8") as database_file:
        return [parse_graph_line(line) for line in database_file if line.strip()]


def format_graph_line(triples):
    return ",".join(
        f"<{source_node},{label},{target}>" if is_edge else f'<{source_node},{label},"{target}">'
        for source_node, label, target, is_edge in triples
    )


def write_graph_database(database_path, graphs):
    with open(database_path, "w", encoding="utf-8") as database_file:
        for triples in graphs:
            database_file.write(format_graph_line(triples) + "\n")
