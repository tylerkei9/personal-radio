"""Simple baselines every learned ranker must beat. Pure Python; inputs are rows from `pipeline.build_rows`.

A "positive" is a row with label > 0. Each baseline is `fit(train_rows, now) -> score(track_uri) -> float`.
"""
import math
from collections import defaultdict
from datetime import timedelta

SESSION_GAP = timedelta(minutes=30)


def most_pop(train, now=None):
    c = defaultdict(float)
    for r in train:
        if r["label"] > 0:
            c[r["track_uri"]] += r["label"]
    return lambda uri: c.get(uri, 0.0)


def decayed_replay(train, now, half_life_days: float = 14.0):
    """Recency-weighted replay: sum of label * 0.5^(age/half_life) over positive plays. The bar to beat."""
    s = defaultdict(float)
    for r in train:
        if r["label"] > 0:
            age = (now - r["started_at"]).total_seconds() / 86400
            s[r["track_uri"]] += r["label"] * 0.5 ** (age / half_life_days)
    return lambda uri: s.get(uri, 0.0)


def sessions(rows):
    """Split plays into listening sessions at gaps > SESSION_GAP."""
    out, cur, last = [], [], None
    for r in sorted(rows, key=lambda r: r["started_at"]):
        if last is not None and r["started_at"] - last > SESSION_GAP:
            out.append(cur); cur = []
        cur.append(r); last = r["started_at"]
    return out + ([cur] if cur else [])


def item_knn(train, now, recent_n: int = 20, half_life_days: float = 14.0):
    """Item-item cosine over session co-occurrence; score = similarity to your recent positives (decayed)."""
    sess_of = defaultdict(set)
    for i, sess in enumerate(sessions(train)):
        for r in sess:
            if r["label"] > 0:
                sess_of[r["track_uri"]].add(i)
    recent = sorted((r for r in train if r["label"] > 0), key=lambda r: r["started_at"])[-recent_n:]
    w = defaultdict(float)
    for r in recent:
        w[r["track_uri"]] += 0.5 ** ((now - r["started_at"]).total_seconds() / 86400 / half_life_days)

    def score(uri):
        a = sess_of.get(uri)
        if not a:
            return 0.0
        tot = 0.0
        for seed, wt in w.items():
            if seed == uri:
                continue
            b = sess_of.get(seed, set())
            inter = len(a & b)
            if inter:
                tot += wt * inter / math.sqrt(len(a) * len(b))
        return tot
    return score


BASELINES = {"most_pop": most_pop, "decayed_replay": decayed_replay, "item_knn": item_knn}
