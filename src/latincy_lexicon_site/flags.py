"""Crowdsourced correction flags — SQLite-backed, off by default.

Users can flag a token / entry as wrong (bad lemma, bad gloss, …) via the UI
or POST /flags/submit. The FlagStore writes rows to its own SQLite DB,
separate from the analysis cache so wiping cache doesn't drop user reports.

Gated behind LATINCY_SITE_FLAGS_ENABLED=1 at the route + template level.
When the env var is unset or "0", the feature is invisible: endpoints 404,
UI omits the flag button. Built ready so the env var flip is the full
activation step — no code change needed to deploy.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path


def flags_enabled() -> bool:
    """Read per-request so tests can toggle with monkeypatch.setenv."""
    return os.environ.get("LATINCY_SITE_FLAGS_ENABLED", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class FlagStore:
    """SQLite-backed store for user-reported corrections."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS flags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at REAL NOT NULL,
        target_type TEXT NOT NULL,
        subject TEXT NOT NULL,
        target_ref TEXT,
        issue TEXT NOT NULL,
        note TEXT,
        client_ip_hash TEXT
    );
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(self._SCHEMA)
        self._conn.commit()

    def record(
        self,
        *,
        target_type: str,
        subject: str,
        issue: str,
        target_ref: str | None = None,
        note: str | None = None,
        client_ip_hash: str | None = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO flags"
            " (created_at, target_type, subject, target_ref, issue, note, client_ip_hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), target_type, subject, target_ref, issue, note, client_ip_hash),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM flags").fetchone()
        return int(row[0])

    def close(self) -> None:
        self._conn.close()
