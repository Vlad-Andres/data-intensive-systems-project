"""
Evaluation metrics of a reduced database on a list of query lines, shared by the per-run and the comparison plots.

  exact coverage  - % of query lines that at least one kept graph fully answers;
  closeness       - per query line the best closeness of a kept graph (share of the query's parts it satisfies,
                    1 = full answer, as computed by the matcher), averaged over the lines.

Every query line is described by the closeness of each graph that matches at least part of it: {graph_id: closeness}.
"""
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from QLog_satisfaction import parse_query  # noqa: E402
from query_matcher_and_measurer.match_queries_with_variables_on_graphs import query_coverage_of_graph  # noqa: E402


class ClosenessIndex:
    """Closeness of every graph to a query, computed once per distinct query."""

    def __init__(self, graphs: list):
        self.graphs = graphs
        self.cache: dict[str, dict[int, float]] = {}

    def of(self, query: str) -> dict[int, float]:
        if query not in self.cache:
            paths = parse_query(query)
            values = {graph_id: query_coverage_of_graph(graph, paths) for graph_id, graph in enumerate(self.graphs)}
            self.cache[query] = {graph_id: value for graph_id, value in values.items() if value > 0}
        return self.cache[query]

    def of_lines(self, lines: list[str]) -> list[dict[int, float]]:
        return [self.of(line.strip()) for line in lines if line.strip()]


def exact_coverage(lines: list[dict[int, float]], kept: set[int]) -> float:
    """% of query lines that at least one kept graph fully answers."""
    return 100.0 * sum(1 for closeness in lines if any(value == 1.0 and graph_id in kept for graph_id, value in closeness.items())) / len(lines)


def average_closeness(lines: list[dict[int, float]], kept: set[int]) -> float:
    """Per query line the best closeness of a kept graph (0 if none matches), averaged over the lines, in %."""
    return 100.0 * sum(max((value for graph_id, value in closeness.items() if graph_id in kept), default=0.0) for closeness in lines) / len(lines)


def chance_at_least_one(graphs_with_it: int, graph_count: int, kept_count: int) -> float:
    """Probability that kept_count random graphs include at least one of graphs_with_it given graphs."""
    return 1 - comb(graph_count - graphs_with_it, kept_count) / comb(graph_count, kept_count)


def random_exact_coverage(lines: list[dict[int, float]], graph_count: int, kept_count: int) -> float:
    """Expected exact coverage when kept_count graphs are kept at random."""
    return 100.0 * sum(chance_at_least_one(sum(value == 1.0 for value in closeness.values()), graph_count, kept_count)
                       for closeness in lines) / len(lines)


def random_average_closeness(lines: list[dict[int, float]], graph_count: int, kept_count: int) -> float:
    """Expected average closeness when kept_count graphs are kept at random: E[best] = sum of (step up) x P(best >= that level)."""
    total = 0.0
    for closeness in lines:
        previous_level = 0.0
        for level in sorted(set(closeness.values())):
            graphs_at_least = sum(value >= level for value in closeness.values())
            total += (level - previous_level) * chance_at_least_one(graphs_at_least, graph_count, kept_count)
            previous_level = level
    return 100.0 * total / len(lines)


# name -> (metric of a reduction, expected metric of a random reduction of the same size)
METRICS = {"exact": (exact_coverage, random_exact_coverage), "closeness": (average_closeness, random_average_closeness)}
