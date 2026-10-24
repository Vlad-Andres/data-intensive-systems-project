import gzip
import io
import json
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from models import Movie, Credit, Person

# IMDb category -> predicate (all other categories, e.g. composer or editor, are ignored)
CATEGORY_TO_PREDICATE = {
    "actor": "actedIn", "actress": "actedIn", "self": "actedIn",
    "director": "directed", "writer": "wrote", "producer": "produced",
}

NULL = "\\N"

def value(row, key):
    """Cell value, or None for IMDb's \\N."""
    v = row.get(key)
    return None if v in (None, NULL, "") else v

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
            response.close()
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
    """Yield rows from <name>.tsv(.gz) as dicts, optionally filtering by wanted keys or stopping after a key.
    IMDb files are sorted by id as text (tt10000000 comes before tt1000001), so keys are compared as text."""
    if stop_after is None and wanted:
        stop_after = max(wanted)

    with open_tsv(source, name) as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            key = line[:line.find("\t")]
            if stop_after is not None and key > stop_after:
                return
            if wanted is not None and key not in wanted:
                continue
            yield dict(zip(header, line.rstrip("\n").split("\t")))

def select_movies(source, max_movies, max_tconst):
    """Select movies with the most votes, up to max_movies,
    and only tconst <= max_tconst."""

    ratings = {
        r["tconst"]: (r["averageRating"], int(r["numVotes"]))
        for r in read_rows(source, "title.ratings", stop_after=f"tt{max_tconst:07d}")
    }

    movies = {}

    for r in read_rows(source, "title.basics", stop_after=f"tt{max_tconst:07d}"):
        tconst = r["tconst"]

        if (
            r["titleType"] == "movie"
            and r["isAdult"] == "0"
            and tconst in ratings
            and int(tconst[2:]) <= max_tconst
        ):
            rating, votes = ratings[tconst]
            genres = set(value(r, "genres").split(",")) if value(r, "genres") else set()

            movies[tconst] = Movie(
                tconst,
                r["primaryTitle"],
                value(r, "startYear"),
                value(r, "runtimeMinutes"),
                rating,
                votes,
                genres,
            )

    top = sorted(movies, key=lambda t: -movies[t].votes)[:max_movies]

    return {t: movies[t] for t in top}

def parse_roles(text):
    """Parse the IMDb "characters" field, which is a JSON array of strings, single string or empty."""
    if text in (None, NULL, ""):
        return []
    try:
        return [str(role) for role in json.loads(text)]
    except (ValueError, TypeError):
        return [text.strip('[]"')]

def load_credits(source, movies: dict[str, Movie], max_nconst):
    """return tconst -> list of Credit objects for movies in the given dict, filtering by max_nconst."""

    def allowed(nconst: str):
        return (
            nconst.startswith("nm")
            and nconst[2:].isdigit()
            and int(nconst[2:]) <= max_nconst
        )

    credits = {movie: {} for movie in movies}

    for r in read_rows(source, "title.principals", wanted=movies):
        nconst = r["nconst"]
        predicate = CATEGORY_TO_PREDICATE.get(r["category"])

        if predicate and allowed(nconst):
            key = (nconst, predicate)
            credit = credits[r["tconst"]].get(key)

            if credit is None:
                credit = Credit(nconst, predicate)
                credits[r["tconst"]][key] = credit

            for role in parse_roles(r["characters"]):
                if role not in credit.roles:
                    credit.roles.append(role)

    try:
        for r in read_rows(source, "title.crew", wanted=movies):
            for column, predicate in (
                ("directors", "directed"),
                ("writers", "wrote"),
            ):
                for nconst in (value(r, column) or "").split(","):
                    if nconst and allowed(nconst):
                        key = (nconst, predicate)
                        credits[r["tconst"]].setdefault(
                            key, Credit(nconst, predicate)
                        )

    except FileNotFoundError:
        pass

    return {
        tconst: list(movie_credits.values())
        for tconst, movie_credits in credits.items()
    }

def load_people(source, credits: dict[str, list[Credit]]):
    """Return nconst -> (name, born) for all people in the given credits dict."""

    needed = {
        credit.nconst
        for entries in credits.values()
        for credit in entries
    }
    people = {}

    for person_record in read_rows(source, "name.basics", wanted=needed):
        person = Person(
            person_record["nconst"],
            person_record["primaryName"],
            value(person_record, "birthYear")
        )
        people[person.nconst] = person

    return people