"""Ranking metrics and a paired block bootstrap over days (plays within a day are correlated, so resample days)."""
import math
import random


def ndcg_at_k(ranked, relevant: set, k: int = 10) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, u in enumerate(ranked[:k]) if u in relevant)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0


def recall_at_k(ranked, relevant: set, k: int = 10) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant) if relevant else 0.0


def paired_bootstrap(a: list[float], b: list[float], n: int = 2000, seed: int = 0):
    """Per-day metric lists for two systems -> (mean diff a-b, 95% CI, share of resamples with a > b)."""
    assert len(a) == len(b) and a
    rng = random.Random(seed)
    d = [x - y for x, y in zip(a, b)]
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return sum(d) / len(d), (means[int(0.025 * n)], means[int(0.975 * n)]), sum(m > 0 for m in means) / n
