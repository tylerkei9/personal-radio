"""Supervisor: ingest on startup, then poll forever; re-sync library every few hours; survive crashes.

Usage: python -m radio track      (first run opens a browser for Spotify login; later runs are silent)
"""
import logging
import os
import threading
import time

from radio.collect import poller
from radio import paths, retention
from radio.collect import sync
from radio.db import connect

SYNC_EVERY_S = 6 * 3600
LOG = paths.LOG


def _periodic_sync(sp, con):
    while True:
        time.sleep(SYNC_EVERY_S)
        sync.run_all(sp, con.cursor())
        try:
            logging.getLogger("run").info("retention purge: %s", retention.purge(con.cursor()))
        except Exception:
            logging.getLogger("run").exception("retention purge failed")


def main():
    logging.basicConfig(filename=LOG, level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    log = logging.getLogger("run")
    con = connect()
    sp = poller.build_client()
    sync_sp = poller.build_client(timeout=30)           # bulk calls (top items) can be slow
    sync.run_all(sync_sp, con.cursor())                 # startup ingest
    retention.purge(con.cursor())
    threading.Thread(target=_periodic_sync, args=(sync_sp, con), daemon=True).start()
    while True:                                         # poller restarts on unexpected crash
        try:
            poller.loop(sp, con.cursor(), reconcile=sync.backfill_recent)
        except Exception:
            log.exception("poller crashed; restarting in 10s")
            time.sleep(10)


if __name__ == "__main__":
    main()
