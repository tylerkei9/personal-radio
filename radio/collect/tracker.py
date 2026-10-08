"""Pure state machine: turns a stream of playback-state snapshots into finished plays.

Kept free of Spotify/DB code so it can be unit-tested with synthetic polls.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

COMPLETE_TAIL_MS = 10_000     # last observed progress this close to the end => completed (polls land 4-6s short)
REPEAT_REWIND_MS = 5_000      # progress jumping back to near 0 on same track => repeat
SEEK_TOLERANCE_MS = 6_000     # progress deviating from expected by more than this => seek
CHAIN_GAP_S = 30              # a new track within this of the last ending may be auto/nav continuation


def context_type(uri: str | None) -> str | None:
    if not uri:
        return None
    parts = uri.split(":")
    if len(parts) >= 3 and parts[1] == "user":
        return "collection" if parts[-1] == "collection" else "playlist"
    return parts[1] if len(parts) > 1 else None


@dataclass
class Snapshot:
    ts: datetime
    is_playing: bool
    track_uri: str | None = None
    name: str | None = None
    artist: str | None = None
    isrc: str | None = None
    duration_ms: int | None = None
    progress_ms: int = 0
    device: str | None = None
    context_uri: str | None = None
    shuffle: bool | None = None
    is_podcast: bool = False


@dataclass
class _Open:
    snap: Snapshot
    started_at: datetime
    last_progress: int
    last_ts: datetime
    max_progress: int = 0
    playing: bool = True
    seeks: int = 0
    start_kind: str = "user"


@dataclass
class Tracker:
    cur: _Open | None = None
    last_end: tuple | None = None   # (reason, context_uri, ts)
    finished: list[dict] = field(default_factory=list)

    def _close(self, reason: str | None = None):
        o = self.cur
        if not o:
            return
        d = o.snap.duration_ms or 0
        if reason is None:
            reason = "completed" if d and o.max_progress >= d - COMPLETE_TAIL_MS else "skipped"
        self.finished.append(dict(
            source="poller", started_at=o.started_at, track_uri=o.snap.track_uri,
            track_name=o.snap.name, artist=o.snap.artist, isrc=o.snap.isrc,
            duration_ms=o.snap.duration_ms, ms_played=o.max_progress, end_reason=reason,
            device=o.snap.device, context_uri=o.snap.context_uri, shuffle=o.snap.shuffle,
            incognito=False, start_kind=o.start_kind,
            context_type=context_type(o.snap.context_uri), seeks=o.seeks))
        self.last_end = (reason, o.snap.context_uri, o.last_ts)
        self.cur = None

    def update(self, s: Snapshot):
        if not s.track_uri or s.is_podcast:
            o = self.cur
            near_end = o and o.snap.duration_ms and o.max_progress >= o.snap.duration_ms - COMPLETE_TAIL_MS
            self._close("completed" if near_end else "other")   # stopping mid-track is not a preference signal
            return
        o = self.cur
        if o and o.snap.track_uri == s.track_uri:
            rewound = s.progress_ms < REPEAT_REWIND_MS and o.max_progress > s.progress_ms + REPEAT_REWIND_MS
            if rewound:
                # same track restarted: previous pass ended; a near-complete pass counts as repeat-worthy
                self._close()
            else:
                elapsed = (s.ts - o.last_ts).total_seconds() * 1000 if o.playing else 0
                if abs(s.progress_ms - (o.last_progress + elapsed)) > SEEK_TOLERANCE_MS:
                    o.seeks += 1
                o.max_progress = max(o.max_progress, s.progress_ms)
                o.last_progress, o.last_ts, o.playing = s.progress_ms, s.ts, s.is_playing
                o.snap = s if s.is_playing else o.snap
                return
        elif o:
            self._close()
        started = s.ts - timedelta(milliseconds=s.progress_ms)
        self.cur = _Open(s, started, s.progress_ms, s.ts, s.progress_ms,
                         playing=s.is_playing, start_kind=self._start_kind(s))

    def _start_kind(self, s: Snapshot) -> str:
        le = self.last_end
        if le and s.context_uri and le[1] == s.context_uri and (s.ts - le[2]).total_seconds() < CHAIN_GAP_S:
            return "auto" if le[0] == "completed" else "nav"
        return "user"

    def drain(self) -> list[dict]:
        out, self.finished = self.finished, []
        return out
