"""Tracker heartbeat. The poller rewrites a small JSON file every loop; `python -m radio health` reports whether it is fresh.

A file (not the DB) so it works while the tracker holds the DuckDB write lock. Exit code 1 when stale, so cron /
Task Scheduler can alert. Usage: python -m radio health [--max-age 180] [--notify]
"""
import json
import os
import subprocess
import sys
import tempfile
import time

from radio import paths

HEARTBEAT = os.environ.get("RADIO_HEARTBEAT", paths.HEARTBEAT)


def write_heartbeat(path: str = HEARTBEAT, **info):
    """Atomic replace so a reader never sees a half-written file."""
    d = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", dir=d, delete=False, suffix=".tmp") as f:
        json.dump({"ts": time.time(), **info}, f)
    os.replace(f.name, path)


def check(path: str = HEARTBEAT, max_age_s: float = 180, now=time.time) -> tuple[bool, str]:
    try:
        with open(path) as f:
            hb = json.load(f)
    except (OSError, ValueError):
        return False, "no heartbeat file: tracker has never run or file unreadable"
    age = now() - hb["ts"]
    if age > max_age_s:
        return False, f"STALE: last heartbeat {age:.0f}s ago (limit {max_age_s:.0f}s), last status: {hb.get('status')}"
    return True, f"ok: {age:.0f}s ago, status={hb.get('status')}, last_poll_error={hb.get('error')}"


def main(argv):
    max_age = float(argv[argv.index("--max-age") + 1]) if "--max-age" in argv else 180
    ok, msg = check(max_age_s=max_age)
    print(msg)
    if not ok and "--notify" in argv and sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "Personal Radio"'])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
