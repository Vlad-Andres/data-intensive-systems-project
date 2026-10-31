import argparse
import collections
import itertools
import random
import re
from pathlib import Path

from graph_parser import read_graph_database
from QLog_satisfaction import NODE_ID_PATTERN, parse_query

DATABASE_NUMBER_PATTERN = re.compile(r"DatabaseX_([1-8])(?:\.txt)?$")
MIN_PERSON_APPEARANCES = 2


def database_number(database_path):
    name = Path(database_path).name
    match = DATABASE_NUMBER_PATTERN.fullmatch(name)
    if match:
        return int(match.group(1))
    if name in {"imdb_big", "imdb_big.txt"}:
        return 9
    raise ValueError(
        "database filename must be DatabaseX_1.txt through DatabaseX_8.txt "
        "or imdb_big.txt so its query-log number can be determined"
    )


def quote_value(value):
    if '"' in value:
        raise ValueError(f"attribute value contains a quote and cannot be represented: {value!r}")
    return f'"{value}"'


def replace_node_ids_with_variables(query):
    variable_by_node_id = {}
    variable_paths = []
    for components in parse_query(query):
        variable_components = []
        for index, component in enumerate(components):
            if index % 2 == 0 and NODE_ID_PATTERN.fullmatch(component):
                component = variable_by_node_id.setdefault(component, f"X{len(variable_by_node_id) + 1}")
            variable_components.append(component)
        variable_paths.append(".".join(variable_components))
    return ",".join(variable_paths)


def paths_in_graph(graph, max_edge_hops=3):
    outgoing = {}
    attributes = {}
    simple_paths = set()

    for source, label, target, is_edge in graph:
        source_text = str(source)
        if is_edge:
            target_text = str(target)
            outgoing.setdefault(source_text, []).append((label, target_text))
            simple_paths.add(f"{source_text}.{label}.{target_text}")
        else:
            attributes.setdefault(source_text, []).append((label, target))
            simple_paths.add(f"{source_text}.{label}.{quote_value(target)}")

    complex_paths = set()
    for source, edges in outgoing.items():
        for label, target in edges:
            for attribute, value in attributes.get(target, []):
                complex_paths.add(
                    f"{source}.{label}.{target}.{attribute}.{quote_value(value)}"
                )

    def extend(node, components, visited_nodes, edge_hops):
        if edge_hops >= max_edge_hops:
            return
        for label, target in outgoing.get(node, []):
            if target in visited_nodes:
                continue
            extended = [*components, label, target]
            hops = edge_hops + 1
            if hops >= 2:
                complex_paths.add(".".join(extended))
            for attribute, value in attributes.get(target, []):
                complex_paths.add(
                    ".".join([*extended, attribute, quote_value(value)])
                )
            extend(target, extended, visited_nodes | {target}, hops)

    for source in outgoing:
        extend(source, [source], {source}, 0)

    return sorted(simple_paths), sorted(complex_paths)


def query_candidates(graphs):
    appearances = person_appearances(graphs)
    simple_by_graph = []
    conditions_by_graph = []
    for graph in graphs:
        simple, _ = paths_in_graph(graph)
        simple_by_graph.append(simple)
        conditions_by_graph.append(conditions_in_graph(graph, appearances))
    return simple_by_graph, conditions_by_graph


def unique_queries(paths_by_graph, rng, count, path_count_range=(1, 1)):
    candidate_groups = []
    for paths in paths_by_graph:
        if not paths:
            continue
        minimum = min(path_count_range[0], len(paths))
        maximum = min(path_count_range[1], len(paths))
        counts = list(range(minimum, maximum + 1))
        rng.shuffle(counts)
        graph_candidates = []
        for path_count in counts:
            for chosen_paths in itertools.combinations(paths, path_count):
                graph_candidates.append(",".join(chosen_paths))
        rng.shuffle(graph_candidates)
        if graph_candidates:
            candidate_groups.append(graph_candidates)

    rng.shuffle(candidate_groups)
    candidates = []
    seen = set()
    while candidate_groups and len(candidates) < count:
        remaining_groups = []
        for graph_candidates in candidate_groups:
            while graph_candidates and graph_candidates[-1] in seen:
                graph_candidates.pop()
            if graph_candidates:
                query = graph_candidates.pop()
                seen.add(query)
                candidates.append(query)
                remaining_groups.append(graph_candidates)
                if len(candidates) == count:
                    break
        candidate_groups = remaining_groups
    return candidates


def build_qlog1(simple_by_graph, rng):
    candidates = unique_queries(simple_by_graph, rng, count=12)
    if len(candidates) < 12:
        raise ValueError("database does not contain enough distinct simple query patterns")

    # Four one-off queries and eight queries repeated twelve times each make 100.
    entries = candidates[:4] + [query for query in candidates[4:] for _ in range(12)]
    rng.shuffle(entries)
    return entries


def build_qlog2(simple_by_graph, rng):
    candidates = unique_queries(simple_by_graph, rng, count=300)
    if len(candidates) < 11:
        raise ValueError("database does not contain enough distinct simple query patterns")

    entries = []
    next_candidate = 0
    previous_queries = []
    for batch_index in range(5):
        dominant = candidates[next_candidate]
        second = candidates[next_candidate + 1]
        next_candidate += 2
        recurring = rng.choice(previous_queries) if previous_queries else candidates[next_candidate]
        if not previous_queries:
            next_candidate += 1

        previous_queries.extend((dominant, second))
        batch = [dominant] * 26 + [second] * 10 + [recurring] * 4
        rng.shuffle(batch)
        entries.extend(batch)
    return entries


def person_appearances(graphs):
    appearances = collections.Counter()
    for graph in graphs:
        appearances.update({value for _, label, value, is_edge in graph if label == "name" and not is_edge})
    return appearances


def conditions_in_graph(graph, appearances):
    names = {source: value for source, label, value, is_edge in graph if label == "name" and not is_edge}
    person_conditions = []
    movie_conditions = []
    for source, label, target, is_edge in graph:
        if is_edge and label in ("actedIn", "directed") and appearances[names.get(source)] >= MIN_PERSON_APPEARANCES:
            person_conditions.append((f"{source}.name.{quote_value(names[source])}", f"{source}.{label}.{target}"))
        elif not is_edge and label in ("genre", "released"):
            movie_conditions.append((f"{source}.{label}.{quote_value(target)}",))
    return person_conditions, movie_conditions


def query_from_conditions(conditions):
    return replace_node_ids_with_variables(",".join(path for condition in conditions for path in condition))


def build_qlog3(conditions_by_graph, rng):
    queries = []
    seen = set()
    graph_indexes = list(range(len(conditions_by_graph)))
    rng.shuffle(graph_indexes)
    for index in itertools.islice(itertools.cycle(graph_indexes), 5 * len(graph_indexes)):
        person_conditions, movie_conditions = conditions_by_graph[index]
        if len(queries) % 2 == 1 and person_conditions and movie_conditions:
            movie_condition_count = rng.randint(1, min(2, len(movie_conditions)))
            chosen = rng.sample(person_conditions, 1) + rng.sample(movie_conditions, movie_condition_count)
        elif len(movie_conditions) >= 2:
            chosen = rng.sample(movie_conditions, 2)
        else:
            continue
        query = query_from_conditions(chosen)
        if query not in seen:
            queries.append(query)
            seen.add(query)
        if len(queries) == 20:
            return queries
    raise ValueError("database does not contain enough graphs for 20 distinct complex queries")


def build_qlog4(conditions_by_graph, rng):
    graph_indexes = list(range(len(conditions_by_graph)))
    rng.shuffle(graph_indexes)
    parent_queries = []
    subqueries = []
    used_parents = set()

    for index in graph_indexes:
        person_conditions, movie_conditions = conditions_by_graph[index]
        people = rng.sample(person_conditions, min(2, len(person_conditions)))
        movie_facts = rng.sample(movie_conditions, min(4 - len(people), len(movie_conditions)))
        parent_conditions = people + movie_facts
        if len(parent_conditions) < 4:
            continue

        parent = query_from_conditions(parent_conditions)
        if parent in used_parents:
            continue

        possible_subsets = [
            subset
            for size in (2, 3)
            for subset in itertools.combinations(parent_conditions, size)
        ]
        rng.shuffle(possible_subsets)
        child_queries = [query_from_conditions(subset) for subset in possible_subsets[:9]]

        used_parents.add(parent)
        parent_queries.append(parent)
        subqueries.extend(child_queries)
        if len(parent_queries) == 5:
            return parent_queries + subqueries

    raise ValueError(
        "database does not contain five graphs with at least four query conditions to create "
        "five large queries and 45 subqueries"
    )


def generate_query_logs(database_path, seed=1):
    database_path = Path(database_path)
    db_number = database_number(database_path)
    graphs = read_graph_database(database_path)
    if not graphs:
        raise ValueError("database contains no graphs")

    rng = random.Random(seed)
    simple_by_graph, conditions_by_graph = query_candidates(graphs)
    logs = [
        build_qlog1(simple_by_graph, rng),
        build_qlog2(simple_by_graph, rng),
        build_qlog3(conditions_by_graph, rng),
        build_qlog4(conditions_by_graph, rng),
    ]
    output_directory = Path(__file__).resolve().parent.parent / "data"
    output_paths = []
    for log_type, queries in enumerate(logs, start=1):
        output_path = output_directory / f"QLog{db_number}_{log_type}.txt"
        output_path.write_text("\n".join(queries) + "\n", encoding="utf-8")
        output_paths.append(output_path)
    return output_paths


def main():
    parser = argparse.ArgumentParser(
        description="Generate four query logs from paths found in one graph database."
    )
    parser.add_argument("database_path", help="DatabaseX_1.txt through DatabaseX_8.txt, or imdb_big.txt")
    parser.add_argument("--seed", type=int, default=1, help="seed for reproducible query-log generation")
    arguments = parser.parse_args()

    try:
        output_paths = generate_query_logs(arguments.database_path, arguments.seed)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    for output_path in output_paths:
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
