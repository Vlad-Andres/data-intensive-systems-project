"""
Convert MovieLens (ml-latest-small) into a graph dataset where every line is
a separate graph, in the same format as the course example:

    <1,top,2>,<2,right,3>,<3,bottom,4>,<4,left,1>,<1,isBoss,"yes">
    <5,married,7>,<7,city,"Amsterdam">,<5,city,"Utrecht">

Model: one graph per user.
    user  --rated_<score>--> movie     (e.g. rated_4.5, the score is in the edge label)
    movie --genre--> genre
    user  --tagged--> movie            (only if the user tagged the movie)
Attributes:
    user  : userId
    movie : title, year
    genre : name

Node ids are global: the same movie or genre has the same id in every graph
that contains it (like nodes 5 and 7 in the example). A mapping file
(graph_dataset.txt.idmap.csv) translates ids back to the MovieLens ids.

Usage:
    Put this script in the folder with movies.csv, ratings.csv and tags.csv
    and run it. Output is written next to the script.
"""
import argparse
import csv
import re
from collections import defaultdict
from itertools import count
from pathlib import Path

# Keep each graph small and readable: only the N most recent ratings per user.
# Set to None to keep all ratings (some users have thousands, so graphs get huge).
MAX_RATINGS_PER_USER = 20

# Only write the first N graphs (users). Set to None for all 610 users.
# Can be overridden on the command line: python movielens_to_graphdataset.py --max-graphs 10
MAX_GRAPHS = 5

# Skip users with fewer than this many ratings.
MIN_RATINGS_PER_USER = 1


def q(value):
    """Quote an attribute value and escape inner quotes."""
    return '"' + str(value).replace('"', '""') + '"'


def convert(src_dir, out_path, max_graphs=MAX_GRAPHS, max_ratings=MAX_RATINGS_PER_USER):
    ids = {}
    next_id = count(1)

    def node(kind, key):
        k = (kind, key)
        if k not in ids:
            ids[k] = next(next_id)
        return ids[k]

    # --- movies: title, year, genres ---
    movies = {}  # movieId -> (title, year or None, [genres])
    with open(Path(src_dir) / "movies.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            title = row["title"].strip()
            m = re.search(r"\((\d{4})\)\s*$", title)
            year = m.group(1) if m else None
            genres = [g for g in row["genres"].split("|") if g != "(no genres listed)"]
            movies[row["movieId"]] = (title, year, genres)

    # --- ratings grouped per user ---
    ratings = defaultdict(list)  # userId -> [(timestamp, movieId, rating)]
    with open(Path(src_dir) / "ratings.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ratings[row["userId"]].append(
                (int(row["timestamp"]), row["movieId"], row["rating"])
            )

    # --- tags grouped per user ---
    tagged = defaultdict(set)  # userId -> {movieId}
    tags_file = Path(src_dir) / "tags.csv"
    if tags_file.exists():
        with open(tags_file, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                tagged[row["userId"]].add(row["movieId"])

    # --- write one graph per line ---
    n_graphs = 0
    with open(out_path, "w", encoding="utf-8", newline="") as out:
        for user_id in sorted(ratings, key=int):
            if max_graphs is not None and n_graphs >= max_graphs:
                break
            user_ratings = sorted(ratings[user_id], reverse=True)  # newest first
            if len(user_ratings) < MIN_RATINGS_PER_USER:
                continue
            if max_ratings is not None:
                user_ratings = user_ratings[:max_ratings]

            u = node("user", user_id)
            triples = [f'<{u},userId,{q(user_id)}>']
            seen_movies = set()

            for _, movie_id, rating in user_ratings:
                if movie_id not in movies or movie_id in seen_movies:
                    continue
                seen_movies.add(movie_id)
                title, year, genres = movies[movie_id]
                mv = node("movie", movie_id)

                triples.append(f"<{u},rated_{rating},{mv}>")
                triples.append(f"<{mv},title,{q(title)}>")
                if year:
                    triples.append(f"<{mv},year,{q(year)}>")
                for g in genres:
                    gid = node("genre", g)
                    triples.append(f"<{mv},genre,{gid}>")
                    triples.append(f"<{gid},name,{q(g)}>")
                if movie_id in tagged[user_id]:
                    triples.append(f"<{u},tagged,{mv}>")

            out.write(",".join(triples) + "\n")
            n_graphs += 1

    # --- id mapping ---
    with open(str(out_path) + ".idmap.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "type", "original_key"])
        for (kind, key), nid in ids.items():
            w.writerow([nid, kind, key])

    print(f"Done: {n_graphs} graphs, {len(ids)} distinct nodes, written to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-graphs", type=int, default=MAX_GRAPHS,
                        help="number of graphs (lines) to write; 0 = all")
    parser.add_argument("--max-ratings", type=int, default=MAX_RATINGS_PER_USER,
                        help="ratings per graph; 0 = all")
    args = parser.parse_args()

    current_path = Path(__file__).parent
    out_path = current_path / "graph_dataset.txt"
    convert(current_path, out_path,
            max_graphs=args.max_graphs or None,
            max_ratings=args.max_ratings or None)