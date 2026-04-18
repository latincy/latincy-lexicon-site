"""Two-tier cache: functools.lru_cache + SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path


def make_cache_key(endpoint: str, input_text: str, *, version: str) -> str:
    """Build a deterministic sha1 cache key.

    Input is lowercased + stripped before hashing so "AMO" and "amo " share a key.
    The version prefix guarantees that any upstream bump (model, lexicon, or site)
    silently invalidates the entire cache.
    """
    normalized = input_text.strip().lower()
    payload = f"{version}|{endpoint}|{normalized}".encode()
    return hashlib.sha1(payload).hexdigest()


class SqliteCache:
    """Simple key→bytes store backed by SQLite.

    Used as the persistent tier below functools.lru_cache. Bytes payload
    (rather than str) so we can stash either JSON strings or pickled values.
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        value BLOB NOT NULL,
        created_at REAL NOT NULL
    );
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(self._SCHEMA)
        self._conn.commit()

    def get(self, key: str) -> bytes | None:
        row = self._conn.execute(
            "SELECT value FROM cache WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: bytes) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        self._conn.commit()

    def rows(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()
        return int(row[0])

    def close(self) -> None:
        self._conn.close()


class CachedAnalyzer:
    """Two-tier cache wrapper.

    Layer 1: functools.lru_cache (in-memory, process-lifetime)
    Layer 2: SqliteCache (on-disk, survives restarts)

    The version string is baked into every key. Bump the version when
    latincy-lexicon, the spaCy model, or serialization format changes.
    """

    def __init__(
        self, sqlite: SqliteCache, *, version: str, lru_size: int = 1000
    ) -> None:
        self._sqlite = sqlite
        self._version = version

        @lru_cache(maxsize=lru_size)
        def _memo(key: str) -> bytes | None:
            return self._sqlite.get(key)

        self._memo = _memo

    def get_or_compute(
        self, endpoint: str, input_text: str, compute: Callable[[str], dict]
    ) -> dict:
        key = make_cache_key(endpoint, input_text, version=self._version)

        cached = self._memo(key)
        if cached is not None:
            return json.loads(cached)

        result = compute(input_text)
        serialized = json.dumps(result).encode("utf-8")
        self._sqlite.set(key, serialized)
        # Prime LRU so next call skips SQLite
        self._memo.cache_clear()
        self._memo(key)
        return result

    def clear_memory_cache(self) -> None:
        self._memo.cache_clear()
