"""
Convert the official IMDb datasets (https://datasets.imdbws.com) into a graph.

Model:
    person --actedIn--> movie
    person --directed--> movie
    person --produced--> movie
    person --wrote--> movie
    person --playedRole--> role --inMovie--> movie
Attributes:
    movie  : title, released, runtime, rating, votes, genre
    person : name, born
    role   : roleName
"""
import argparse
from models import Credit, Graph, Movie, NodeIds, Person
from data_reader import select_movies, load_credits, load_people


def limit_movie_credits(
    credits: dict[str, list[Credit]],
    max_edges_for_each_movie: int,
) -> dict[str, list[Credit]]:
    """Keep complete credits within each movie's edge limit."""
    filtered = {}

    for tconst, movie_credits in credits.items():
        kept = []
        edge_count = 0

        for credit in movie_credits:
            credit_edges = 1

            if credit.predicate == "actedIn":
                credit_edges += 2 * len(credit.roles)

            if edge_count + credit_edges <= max_edges_for_each_movie:
                kept.append(credit)
                edge_count += credit_edges

        filtered[tconst] = kept

    return filtered

def add_movie(graph: Graph, node_id: NodeIds, movie: Movie, credits: list[Credit], people: dict[str, Person]):
    
    m = node_id("movie", movie.tconst, movie.title)

    graph.attribute(m, "type", "Movie")

    graph.attribute(m, "title", movie.title)

    for attribute in ("released", "runtime", "rating", "votes"):
        value = getattr(movie, attribute)
        if value is not None:
            graph.attribute(m, attribute, value)

    for genre in movie.genres:
        graph.attribute(m, "genre", genre)
        

    for credit in credits:
        person = people.get(credit.nconst)
        name = person.name if person else credit.nconst
        p = node_id("person", credit.nconst, name)  
        
        graph.edge(p, credit.predicate, m)

        graph.attribute(p, "type", "Person")

        graph.attribute(p, "name", name)

        if person and person.born:
            graph.attribute(p, "born", person.born)

        if credit.predicate == "actedIn":
            for role in credit.roles:
                r = node_id(
                    "role",
                    f"{movie.tconst}:{credit.nconst}:{role}",
                    role,
                )

                graph.edge(p, "playedRole", r)
                
                graph.edge(r, "inMovie", m)

                graph.attribute(r, "type", "Role")

                graph.attribute(r, "roleName", role)

def group_movies(
    selected: dict[str, Movie],
    credits: dict[str, list[Credit]],
) -> list[list[str]]:
    """Group movies into connected components through shared people."""

    parent = {tconst: tconst for tconst in selected}

    def find(movie):
        while parent[movie] != movie:
            parent[movie] = parent[parent[movie]]
            movie = parent[movie]
        return movie

    def union(a, b):
        root_a = find(a)
        root_b = find(b)

        if root_a != root_b:
            parent[root_b] = root_a

    first_movie_by_person = {}

    for tconst, entries in credits.items():
        for credit in entries:
            nconst = credit.nconst

            if nconst in first_movie_by_person:
                union(tconst, first_movie_by_person[nconst])
            else:
                first_movie_by_person[nconst] = tconst

    groups = {}

    for tconst in selected:
        root = find(tconst)
        groups.setdefault(root, []).append(tconst)

    return list(groups.values())

def convert(source, out_path, max_movies, max_tconst, max_nconst, max_edges_for_each_movie, max_graphs):

    selected: dict[str, Movie] = select_movies(source, max_movies, max_tconst)
    credits: dict[str, list[Credit]] = load_credits(source, selected, max_nconst)
    people: dict[str, Person] = load_people(source, credits)

    credits = limit_movie_credits(
        credits, max_edges_for_each_movie
    )

    groups = group_movies(selected, credits)
    sorted(groups, key=lambda group: -len(group))
    node_id = NodeIds()

    with open(out_path, "w", encoding="utf-8", newline="") as out:
        for group in groups[:max_graphs]:
            graph = Graph()

            for tconst in group:
                add_movie(
                    graph,
                    node_id,
                    selected[tconst],
                    credits[tconst],
                    people,
                )

            out.write(graph.line() + "\n")

def main():
    parser = argparse.ArgumentParser(description="IMDb datasets -> one graph")
    parser.add_argument("--source", default="https://datasets.imdbws.com",
                        help="URL or folder with the IMDb .tsv(.gz) files")
    parser.add_argument("--output", default="imdb_graph_dataset.txt")
    parser.add_argument("--max-movies", type=int, default=20, help="number of movies in the graph")
    parser.add_argument("--max-tconst", type=int, default=1_500_000,
                        help="only movies with id tt<=this number (smaller = faster)")
    parser.add_argument("--max-nconst", type=int, default=5_000_000,
                        help="skip people with id nm<=this number (smaller = faster)")
    parser.add_argument("--max-edges-for-each-movie", type=int, default=10,
                        help="maximum number of edges for each movie")
    parser.add_argument("--max-graphs", type=int, default=3,
                    help="maximum number of graphs to generate")
    args = parser.parse_args()
    convert(args.source, args.output, args.max_movies, args.max_tconst, args.max_nconst, args.max_edges_for_each_movie, max_graphs=args.max_graphs)


if __name__ == "__main__":
    main()