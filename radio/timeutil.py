"""Local-time helpers. Plays are stored as naive UTC; context features (hour, weekday) need the listener's local time.

Set RADIO_TZ to an IANA name (e.g. America/New_York); default is the machine's local zone. Stored data stays UTC,
so changing the zone (or travelling) never requires a migration, and DST is handled by zoneinfo.
"""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def local_tz():
    name = os.environ.get("RADIO_TZ")
    return ZoneInfo(name) if name else datetime.now().astimezone().tzinfo


def to_local(ts_utc: datetime, tz=None) -> datetime:
    """Naive-UTC datetime -> aware local datetime."""
    return ts_utc.replace(tzinfo=timezone.utc).astimezone(tz or local_tz())


def hour_weekday(ts_utc: datetime, tz=None) -> tuple[int, int]:
    t = to_local(ts_utc, tz)
    return t.hour, t.weekday()
