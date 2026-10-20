"""
Convert the official IMDb datasets (https://datasets.imdbws.com) into ONE graph (one line)
with the same structure as the Neo4j movies example, in the same format as the course
example (<1,top,2>,<2,right,3>,<1,isBoss,"yes">).

Model (same as the Neo4j movies graph):
    person --actedIn--> movie
    person --directed--> movie
    person --produced--> movie
    person --wrote--> movie
    person --playedRole--> role --inMovie--> movie     (a role is a node: a triple cannot
                                                        carry the edge attribute "roles")
Attributes:
    movie  : title, released, runtime, rating, votes, genre (one triple per genre)
    person : name, born
    role   : roleName
    all    : type ("Movie" / "Person" / "Role"); set TYPE_TRIPLES = False to drop

Differences with Neo4j: IMDb has no tagline and no individual reviews, so there is no
REVIEWED / FOLLOWS. IMDb only has one aggregate score per movie: rating and votes.

WHY IT IS FAST
All IMDb files are sorted by id. The script only looks at movies with an id up to
--max-tconst, and stops reading every file as soon as it is past the last id it needs.
With --source https://datasets.imdbws.com (the default) the files are streamed from the
IMDb server and the download is stopped at that point, so the big files (title.principals
is ~700 MB) are never downloaded completely. People with an id above --max-nconst are skipped.

Usage:
    python imdb_to_graphdataset.py                          # stream from IMDb, 20 movies
    python imdb_to_graphdataset.py --source imdb_data       # or read local .tsv / .tsv.gz files
    python imdb_to_graphdataset.py --max-movies 40
The movies chosen are the --max-movies most voted feature films with id <= --max-tconst.
"""
import argparse
import csv
import gzip
import io
import json
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

NULL = "\\N"
TYPE_TRIPLES = True

# IMDb category -> predicate (all other categories, e.g. composer or editor, are ignored)
CATEGORY_TO_PREDICATE = {
    "actor": "actedIn", "actress": "actedIn", "self": "actedIn",
    "director": "directed", "writer": "wrote", "producer": "produced",
}


def quote(value):
    """Quote an attribute value; inner quotes are doubled."""
    return '"' + str(value).replace('"', '""') + '"'


class NodeIds:
    """Global integer ids: the same (kind, key) always gets the same id."""

    def __init__(self):
        self.ids = {}
        self.labels = {}

    def __call__(self, kind, key, label=""):
        node = self.ids.setdefault((kind, key), len(self.ids) + 1)
        self.labels.setdefault(node, label)
        return node


class Graph:
    """One graph = one output line; triples are unique, edges come before attributes."""

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


@contextmanager
def open_tsv(source, name):
    """Text stream of <name>.tsv(.gz) from a folder or an http(s) URL."""
    source = str(source)
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(f"{source.rstrip('/')}/{name}.tsv.gz",
                                         headers={"User-Agent": "imdb-graph-converter"})
        response = urllib.request.urlopen(request, timeout=60)
        try:
            with io.TextIOWrapper(gzip.GzipFile(fileobj=response), encoding="utf-8") as f:
                yield f
        finally:
            response.close()      # stops the download
        return
    for suffix in ("", ".gz"):
        path = Path(source) / f"{name}.tsv{suffix}"
        if path.exists():
            opener = gzip.open if suffix else open
            with opener(path, "rt", encoding="utf-8") as f:
                yield f
            return
    raise FileNotFoundError(f"{name}.tsv(.gz) not found in {source}")


def read_rows(source, name, wanted=None, stop_after=None):
    """Stream a TSV as dicts. Only rows whose first column is in `wanted` are parsed, and
    reading stops after the first id beyond `stop_after` (files are sorted by id).
    Without stop_after it defaults to the largest id in `wanted`."""
    if stop_after is None and wanted:
        stop_after = max(wanted, key=lambda k: (len(k), k))
    stop_len = len(stop_after) if stop_after else 0

    with open_tsv(source, name) as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            key = line[:line.find("\t")]
            # longer-or-equal id that sorts after stop_after is numerically larger: stop
            if stop_after is not None and len(key) >= stop_len and key > stop_after:
                return
            if wanted is not None and key not in wanted:
                continue
            yield dict(zip(header, line.rstrip("\n").split("\t")))


def value(row, key):
    """Cell value, or None for IMDb's \\N."""
    v = row.get(key)
    return None if v in (None, NULL, "") else v


def select_movies(source, max_movies, max_tconst):
    """tconst -> attributes, the most voted feature films with id <= max_tconst."""
    stop = f"tt{max_tconst:07d}"
    ratings = {r["tconst"]: (r["averageRating"], int(r["numVotes"]))
               for r in read_rows(source, "title.ratings", stop_after=stop)}

    movies = {}
    for r in read_rows(source, "title.basics", stop_after=stop):
        if r["titleType"] == "movie" and r["isAdult"] == "0" and r["tconst"] in ratings:
            rating, votes = ratings[r["tconst"]]
            genres = value(r, "genres")
            movies[r["tconst"]] = {
                "title": r["primaryTitle"], "released": value(r, "startYear"),
                "runtime": value(r, "runtimeMinutes"), "rating": rating, "votes": votes,
                "genres": genres.split(",") if genres else [],
            }
    top = sorted(movies, key=lambda t: -movies[t]["votes"])[:max_movies]
    return {t: movies[t] for t in top}


def parse_roles(text):
    """principals 'characters' column is a JSON list like ["Neo"]; \\N means unknown."""
    if text in (None, NULL, ""):
        return []
    try:
        return [str(role) for role in json.loads(text)]
    except (ValueError, TypeError):
        return [text.strip('[]"')]


def load_credits(source, selected, max_nconst):
    """tconst -> ordered list of (nconst, predicate, roles), without duplicates.
    People with an id above max_nconst are skipped (keeps the name lookup short)."""
    def allowed(nconst):
        return nconst.startswith("nm") and nconst[2:].isdigit() and int(nconst[2:]) <= max_nconst

    credits = {t: {} for t in selected}
    for r in read_rows(source, "title.principals", wanted=selected):
        predicate = CATEGORY_TO_PREDICATE.get(r["category"])
        if predicate and allowed(r["nconst"]):
            entry = credits[r["tconst"]].setdefault((r["nconst"], predicate), [])
            entry.extend(role for role in parse_roles(r["characters"]) if role not in entry)

    try:  # title.crew lists ALL directors and writers; principals only the top-billed ones
        for r in read_rows(source, "title.crew", wanted=selected):
            for column, predicate in (("directors", "directed"), ("writers", "wrote")):
                for nconst in (value(r, column) or "").split(","):
                    if nconst and allowed(nconst):
                        credits[r["tconst"]].setdefault((nconst, predicate), [])
    except FileNotFoundError:
        pass
    return {t: [(n, p, roles) for (n, p), roles in c.items()] for t, c in credits.items()}


def load_people(source, credits):
    needed = {nconst for entries in credits.values() for nconst, _, _ in entries}
    return {r["nconst"]: (r["primaryName"], value(r, "birthYear"))
            for r in read_rows(source, "name.basics", wanted=needed)}


def add_movie(graph, node_id, tconst, movie, entries, people):
    m = node_id("movie", tconst, movie["title"])
    if TYPE_TRIPLES:
        graph.attribute(m, "type", "Movie")
    graph.attribute(m, "title", movie["title"])
    for predicate in ("released", "runtime", "rating", "votes"):
        if movie[predicate] is not None:
            graph.attribute(m, predicate, movie[predicate])
    for genre in movie["genres"]:
        graph.attribute(m, "genre", genre)

    for nconst, predicate, roles in entries:
        name, born = people.get(nconst, (nconst, None))
        p = node_id("person", nconst, name)
        graph.edge(p, predicate, m)
        if TYPE_TRIPLES:
            graph.attribute(p, "type", "Person")
        graph.attribute(p, "name", name)
        if born:
            graph.attribute(p, "born", born)
        if predicate == "actedIn":
            for role in roles:
                r = node_id("role", f"{tconst}:{nconst}:{role}", role)
                graph.edge(p, "playedRole", r)
                graph.edge(r, "inMovie", m)
                if TYPE_TRIPLES:
                    graph.attribute(r, "type", "Role")
                graph.attribute(r, "roleName", role)


def convert(source, out_path, max_movies, max_tconst, max_nconst):
    start = time.time()

    def log(message):
        print(f"[{time.time() - start:5.1f}s] {message}")

    selected = select_movies(source, max_movies, max_tconst)
    log(f"{len(selected)} movies selected")
    credits = load_credits(source, selected, max_nconst)
    log(f"{sum(len(c) for c in credits.values())} credits read")
    people = load_people(source, credits)
    log(f"{len(people)} people read")

    graph, node_id = Graph(), NodeIds()
    for tconst, movie in selected.items():
        add_movie(graph, node_id, tconst, movie, credits[tconst], people)

    with open(out_path, "w", encoding="utf-8", newline="") as out:
        out.write(graph.line() + "\n")

    with open(f"{out_path}.idmap.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "type", "original_key", "label"])
        for (kind, key), nid in node_id.ids.items():
            writer.writerow([nid, kind, key, node_id.labels[nid]])

    log(f"Done: 1 graph, {len(node_id.ids)} nodes, "
        f"{len(graph.edges) + len(graph.attributes)} triples, written to {out_path}")


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
    args = parser.parse_args()
    convert(args.source, args.output, args.max_movies, args.max_tconst, args.max_nconst)


if __name__ == "__main__":
    main()