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

class Movie:
    def __init__(self, tconst, title, released, runtime, rating, votes, genres):
        self.tconst = tconst
        self.title = title
        self.released = released
        self.runtime = runtime
        self.rating = rating
        self.votes = votes
        self.genres = genres

class Credit:
    def __init__(self, nconst, predicate, roles=None):
        self.nconst = nconst
        self.predicate = predicate
        self.roles = roles if roles is not None else []

class Person:
    def __init__(self, nconst, name, born):
        self.nconst = nconst
        self.name = name
        self.born = born