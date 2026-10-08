"""Turn scored candidate tracks into a playlist with exploration, logging each pick's slot, probability and reason.

Slots: confident (top by score, deterministic), deepcut (capped share, sampled from known-artist candidates),
explore (softmax-sampled from the next band), wildcard (uniform from the tail). Final order is shuffled so position
is independent of score (lets us estimate position bias).

Propensity = P(track appears in the playlist), estimated by replaying the whole generator `runs` times with fresh
seeds and counting. A closed form like k*softmax is wrong: sampling without replacement (plus the per-artist cap)
makes inclusion probabilities non-additive, and k*softmax can exceed 1.
"""
import math
import random
from collections import Counter

DEEP_SHARE = 0.2        # cap on "deep cuts from artists you already like"
REPLAY_RUNS = 10_000


def _generate(cands: list[dict], n: int, conf: float, explore: float, deep: float, rng: random.Random,
              max_per_artist: int, temperature: float) -> list[dict]:
    deep_pool = sorted((c for c in cands if c.get("kind") == "deepcut"), key=lambda c: -c["score"])
    pool = sorted((c for c in cands if c.get("kind") != "deepcut"), key=lambda c: -c["score"])
    n_deep = min(round(n * deep), len(deep_pool)) if deep_pool else 0
    n_exp = round(n * explore)
    n_wild = round(n * (1 - conf - explore - deep))
    n_conf = n - n_deep - n_exp - n_wild
    taken, per_artist, out = set(), {}, []

    def ok(c):
        return c["track_uri"] not in taken and per_artist.get(c["artist"], 0) < max_per_artist

    def take(c, slot):
        taken.add(c["track_uri"]); per_artist[c["artist"]] = per_artist.get(c["artist"], 0) + 1
        out.append({**c, "slot": slot})

    for c in pool:
        if sum(o["slot"] == "confident" for o in out) >= n_conf:
            break
        if ok(c):
            take(c, "confident")

    def sample(slot, k, band, weights):
        band = [c for c in band if ok(c)]
        if not band or k <= 0:
            return
        w = weights(band)
        chosen = []
        for _ in range(min(k, len(band))):         # sequential draws without replacement
            left = [i for i in range(len(band)) if i not in chosen]
            r, acc = rng.random() * sum(w[i] for i in left), 0.0
            for i in left:
                acc += w[i]
                if acc >= r:
                    chosen.append(i); break
            else:
                chosen.append(left[-1])
        for i in chosen:
            if ok(band[i]):
                take(band[i], slot)

    sample("deepcut", n_deep, deep_pool[: max(3 * n_deep, 1)], lambda b: [1.0] * len(b))
    rest = [c for c in pool if c["track_uri"] not in taken]
    sample("explore", n_exp, rest[: max(3 * n_exp, 1)],
           lambda b: [math.exp(c["score"] / (temperature * (b[0]["score"] or 1))) for c in b])
    rest = [c for c in pool if c["track_uri"] not in taken]
    sample("wildcard", n_wild, rest, lambda b: [1.0] * len(b))
    rng.shuffle(out)
    return out


def pick(cands: list[dict], n: int = 30, conf: float = 0.5, explore: float = 0.2, deep: float = DEEP_SHARE,
         rng: random.Random | None = None, max_per_artist: int = 2, temperature: float = 1.0,
         runs: int = REPLAY_RUNS) -> list[dict]:
    """cands: dicts with track_uri, artist, score, reason, optional kind='deepcut'. Returns picks with slot, position
    and propensity (Monte Carlo inclusion probability over `runs` replays; 0 < p <= 1)."""
    rng = rng or random.Random()
    # deepcut is clamped by the pool actually available, so conf is whatever remains
    if not any(c.get("kind") == "deepcut" for c in cands):
        conf, deep = conf + deep, 0.0
    args = (n, conf, explore, deep)
    out = _generate(cands, *args, rng, max_per_artist, temperature)
    counts = Counter()
    replay = random.Random(rng.random())
    for _ in range(runs):
        counts.update(o["track_uri"] for o in _generate(cands, *args, replay, max_per_artist, temperature))
    for i, o in enumerate(out):
        o["position"] = i
        o["propensity"] = min(1.0, max(counts[o["track_uri"]], 1) / runs)   # picked once, so >= 1/runs
    return out
