"""Label engine: graded implicit feedback from plays. Context stays attached; labels are re-derivable."""
from dataclasses import dataclass

STRONG_NEG_MS = 10_000
WEAK_NEG_MS = 30_000
COMPLETE_FRAC = 0.9


@dataclass(frozen=True)
class Label:
    value: float   # -1.0 .. +1.0
    name: str


def label_play(ms_played: int, duration_ms: int | None, end_reason: str,
               saved: bool = False, repeated: bool = False, incognito: bool = False) -> Label | None:
    """Return a graded label, or None if the play should be excluded. `saved` must mean "saved within the
    window after this play" (see pipeline.SAVE_WINDOW); a save that predates the play is only a familiarity feature."""
    if incognito:
        return None
    if end_reason == "completed" or (
        duration_ms and ms_played >= COMPLETE_FRAC * duration_ms
    ):
        if saved or repeated:
            return Label(1.0, "strong_pos")
        return Label(0.4, "weak_pos")
    if end_reason == "skipped":
        if ms_played < STRONG_NEG_MS:
            return Label(-1.0, "strong_neg")
        if ms_played >= WEAK_NEG_MS:
            return Label(-0.3, "weak_neg")
        return Label(-0.6, "neg")
    return None  # logout, app closed, etc.: not evidence of preference


def skip_streaks(end_reasons: list[str]) -> list[int]:
    """Consecutive-skip count at each position (feeds the pivot-not-nudge rule later)."""
    out, n = [], 0
    for r in end_reasons:
        n = n + 1 if r == "skipped" else 0
        out.append(n)
    return out
