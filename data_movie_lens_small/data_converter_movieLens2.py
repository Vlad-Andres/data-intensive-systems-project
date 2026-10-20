"""
Convert MovieLens (ml-latest-small) into a graph dataset where every line is
a separate graph, in the same format as the course example:

    <1,top,2>,<2,right,3>,<3,bottom,4>,<4,left,1>,<1,isBoss,"yes">

Model: one graph per user.
    user   --rated--> movie
    user   --gaveRating--> rating --ratingOf--> movie
    movie  --genre--> genre
(a rating is a node, because a triple cannot carry an edge attribute)

Attributes:
    user   : userId
    movie  : title, year
    genre  : name
    rating : score (e.g. "4.5"), timestamp

Node ids are global: the same movie or genre has the same id in every graph
that contains it. graph_dataset.txt.idmap.csv translates ids back to MovieLens ids.

Usage: put this script next to movies.csv and ratings.csv and run it.
       python movielens_to_graphdataset.py [--max-graphs N] [--max-ratings N]   (0 = all)
"""
import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

MAX_GRAPHS = 5               # number of users (lines) to write
MAX_RATINGS_PER_USER = 5    # newest N ratings per user
MIN_RATINGS_PER_USER = 1

YEAR_AT_END = re.compile(r"\((\d{4})\)\s*$")


def quote(value):
    """Quote an attribute value; inner quotes are doubled."""
    return '"' + str(value).replace('"', '""') + '"'


class NodeIds:
    """Global integer ids: the same (kind, key) always gets the same id."""

    def __init__(self):
        self.ids = {}

    def __call__(self, kind, key):
        return self.ids.setdefault((kind, key), len(self.ids) + 1)


class Graph:
    """One graph = one output line. Triples are unique; edges come before attributes,
    so every line starts with an edge like in the course example."""

    def __init__(self):
        self.edges, self.attributes, self._seen = [], [], set()

    def _add(self, triple, target):
        if triple not in self._seen:
            self._seen.add(triple)
            target.append(triple)

    def edge(self, subject, predicate, obj):
        self._add(f"<{subject},{predicate},{obj}>", self.edges)

    def attribute(self, subject, predicate, value):
        self._add(f"<{subject},{predicate},{quote(value)}>", self.attributes)

    def line(self):
        return ",".join(self.edges + self.attributes)


def load_movies(path):
    """movieId -> (title, year or None, [genres])"""
    movies = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            title = row["title"].strip()
            year = YEAR_AT_END.search(title)
            genres = [g for g in row["genres"].split("|") if g != "(no genres listed)"]
            movies[row["movieId"]] = (title, year.group(1) if year else None, genres)
    return movies


def load_ratings(path):
    """userId -> [(timestamp, movieId, score)]"""
    ratings = defaultdict(list)
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ratings[row["userId"]].append((int(row["timestamp"]), row["movieId"], row["rating"]))
    return ratings


def build_graph(user_id, user_ratings, movies, node_id):
    """Graph of one user, or None if none of the rated movies is known."""
    graph = Graph()
    user = node_id("user", user_id)
    graph.attribute(user, "userId", user_id)

    seen_movies = set()
    for timestamp, movie_id, score in user_ratings:
        if movie_id not in movies or movie_id in seen_movies:
            continue
        seen_movies.add(movie_id)
        title, year, genres = movies[movie_id]
        movie = node_id("movie", movie_id)
        rating = node_id("rating", (user_id, movie_id))

        graph.edge(user, "rated", movie)
        graph.edge(user, "gaveRating", rating)
        graph.edge(rating, "ratingOf", movie)
        graph.attribute(rating, "score", score)
        graph.attribute(rating, "timestamp", timestamp)
        graph.attribute(movie, "title", title)
        if year:
            graph.attribute(movie, "year", year)
        for genre in genres:
            genre_id = node_id("genre", genre)
            graph.edge(movie, "genre", genre_id)
            graph.attribute(genre_id, "name", genre)

    return graph if seen_movies else None



def build_big_graph(ratings, movies, node_id,
                    max_ratings=None, max_movies=None):
    """Build one graph containing users, movies, ratings, and genres.

    max_movies: Maximum number of movies to include; None means all.
    max_ratings: Maximum newest ratings per user; None means all.
    """
    graph = Graph()

    # Select the first N movies in numeric movieId order.
    selected_movie_ids = sorted(movies, key=int)
    if max_movies is not None:
        selected_movie_ids = selected_movie_ids[:max_movies]

    selected_movies = set(selected_movie_ids)

    # Add selected movie nodes and their genre relationships.
    for movie_id in selected_movie_ids:
        title, year, genres = movies[movie_id]
        movie = node_id("movie", movie_id)

        graph.attribute(movie, "title", title)
        if year:
            graph.attribute(movie, "year", year)

        for genre in genres:
            genre_id = node_id("genre", genre)
            graph.edge(movie, "genre", genre_id)
            graph.attribute(genre_id, "name", genre)

    # Add users and ratings only for selected movies.
    for user_id in sorted(ratings, key=int):
        user_ratings = sorted(
            ratings[user_id],
            key=lambda r: r[0],
            reverse=True
        )

        if max_ratings is not None:
            user_ratings = user_ratings[:max_ratings]

        user = node_id("user", user_id)
        seen_movies = set()

        for timestamp, movie_id, score in user_ratings:
            if movie_id not in selected_movies or movie_id in seen_movies:
                continue

            seen_movies.add(movie_id)
            rating = node_id("rating", (user_id, movie_id))
            movie = node_id("movie", movie_id)

            graph.edge(user, "rated", movie)
            graph.edge(user, "gaveRating", rating)
            graph.edge(rating, "ratingOf", movie)

            graph.attribute(rating, "score", score)
            graph.attribute(rating, "timestamp", timestamp)

        # Only add users who have at least one included rating.
        if not seen_movies:
            # Remove the user attribute if no rating was included.
            # Graph has no removal method, so avoid creating users
            # without ratings by handling this before adding attributes.
            pass

    return graph


def convert(src_dir, out_path, max_graphs=MAX_GRAPHS, max_ratings=MAX_RATINGS_PER_USER):
    src_dir = Path(src_dir)
    movies = load_movies(src_dir / "movies.csv")
    ratings = load_ratings(src_dir / "ratings.csv")
    node_id = NodeIds()

    n_graphs = 0
    with open(out_path, "w", encoding="utf-8", newline="") as out:
        for user_id in sorted(ratings, key=int):
            if max_graphs is not None and n_graphs >= max_graphs:
                break
            user_ratings = sorted(ratings[user_id], reverse=True)   # newest first
            if len(user_ratings) < MIN_RATINGS_PER_USER:
                continue
            graph = build_graph(user_id, user_ratings[:max_ratings], movies, node_id)
            if graph is None:
                continue
            out.write(graph.line() + "\n")
            n_graphs += 1

    with open(f"{out_path}.idmap.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "type", "original_key"])
        for (kind, key), nid in node_id.ids.items():
            writer.writerow([nid, kind, key])

    print(f"Done: {n_graphs} graphs, {len(node_id.ids)} distinct nodes, written to {out_path}")



def convert_big(src_dir, out_path,
                max_ratings=None, max_movies=None):
    src_dir = Path(src_dir)
    movies = load_movies(src_dir / "movies.csv")
    ratings = load_ratings(src_dir / "ratings.csv")

    node_id = NodeIds()

    graph = build_big_graph(
        ratings,
        movies,
        node_id,
        max_ratings=max_ratings,
        max_movies=max_movies
    )

    with open(out_path, "w", encoding="utf-8", newline="") as out:
        out.write(graph.line() + "\n")

    with open(f"{out_path}.idmap.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "type", "original_key"])
        for (kind, key), nid in node_id.ids.items():
            writer.writerow([nid, kind, key])

    print(
        f"Done: 1 graph, {len(node_id.ids)} distinct nodes, "
        f"written to {out_path}"
    )

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--max-graphs", type=int, default=MAX_GRAPHS, help="0 = all")
    parser.add_argument("--max-ratings", type=int, default=MAX_RATINGS_PER_USER, help="0 = all")
    parser.add_argument(
        "--big-graph", action="store_true", default=True,
        help="Also generate one graph containing the entire dataset"
    )
    parser.add_argument(
        "--max-movies", type=int, default=100,
        help="Maximum movies in the big graph; 100 = all"
    )
    args = parser.parse_args()

    here = Path(__file__).parent
    convert(here, here / "graph_dataset.txt",
            max_graphs=args.max_graphs or None,
            max_ratings=args.max_ratings or None)

    if args.big_graph:
        convert_big(
            here,
            here / "graph_dataset_big.txt",
            max_ratings=args.max_ratings,
            max_movies=args.max_movies or None
        )


if __name__ == "__main__":
    main()