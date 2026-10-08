"""Rolling-origin evaluation: train on everything before day k, skip a gap, test on day k (no leave-one-out)."""
from datetime import timedelta


def rolling_origin(rows, test_days: int = 1, gap_hours: float = 1.0, min_train: int = 20, max_folds: int = 30):
    """Yield (cutoff, train_rows, test_rows). Folds are consecutive test windows; the gap prevents session spill-over."""
    if not rows:
        return
    rows = sorted(rows, key=lambda r: r["started_at"])
    day0 = rows[0]["started_at"].replace(hour=0, minute=0, second=0, microsecond=0)
    last = rows[-1]["started_at"]
    folds, start = [], day0 + timedelta(days=1)
    while start <= last and len(folds) < max_folds:
        end = start + timedelta(days=test_days)
        train = [r for r in rows if r["started_at"] < start - timedelta(hours=gap_hours)]
        test = [r for r in rows if start <= r["started_at"] < end]
        if len(train) >= min_train and test:
            folds.append((start, train, test))
        start = end
    yield from folds
