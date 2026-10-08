"""Compare baselines on your labelled plays with a rolling-origin split. Usage: python -m radio evaluate [--novel]

Per fold: fit on the past, rank every track seen so far, score against that day's positive tracks. `--novel` counts
only tracks never played in training, the case that matters for discovery (a replay baseline gets ~0 there by design).
"""
import sys

from radio.evalkit.baselines import BASELINES
from radio.evalkit.metrics import ndcg_at_k, paired_bootstrap, recall_at_k
from radio.evalkit.splits import rolling_origin


def evaluate(rows, novel_only: bool = False, k: int = 10, **split_kw):
    per_day = {name: [] for name in BASELINES}
    universe = {r["track_uri"] for r in rows}
    for start, train, test in rolling_origin(rows, **split_kw):
        seen = {r["track_uri"] for r in train}
        relevant = {r["track_uri"] for r in test if r["label"] > 0}
        if novel_only:
            relevant -= seen
        if not relevant:
            continue
        cands = sorted(universe - seen) if novel_only else sorted(universe)
        for name, fit in BASELINES.items():
            score = fit(train, start)
            ranked = sorted(cands, key=lambda u: (-score(u), u))
            per_day[name].append((ndcg_at_k(ranked, relevant, k), recall_at_k(ranked, relevant, k)))
    return per_day


def report(per_day):
    n = len(next(iter(per_day.values())))
    print(f"{n} evaluable test days")
    for name, v in per_day.items():
        if v:
            print(f"  {name:15s} NDCG@10 {sum(x[0] for x in v)/len(v):.3f}   Recall@10 {sum(x[1] for x in v)/len(v):.3f}")
    if n >= 5:
        diff, ci, p = paired_bootstrap([x[0] for x in per_day["decayed_replay"]], [x[0] for x in per_day["item_knn"]])
        print(f"  decayed_replay - item_knn NDCG diff {diff:+.3f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]  P(replay better) {p:.2f}")
    else:
        print("  too few test days for a bootstrap (need >= 5); collect more history")


if __name__ == "__main__":
    from radio.db import connect_snapshot
    from radio.taste.pipeline import load_rows
    report(evaluate(load_rows(connect_snapshot()), novel_only="--novel" in sys.argv))
