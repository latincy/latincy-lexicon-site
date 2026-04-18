from pathlib import Path

import pytest

from latincy_lexicon_site.cache import CachedAnalyzer, SqliteCache


@pytest.fixture
def cache(tmp_path: Path) -> SqliteCache:
    return SqliteCache(tmp_path / "cache.db")


def test_first_call_computes(cache: SqliteCache):
    calls = {"n": 0}

    def compute(x: str) -> dict:
        calls["n"] += 1
        return {"x": x}

    ca = CachedAnalyzer(cache, version="v1")
    result = ca.get_or_compute("word", "amo", compute)
    assert result == {"x": "amo"}
    assert calls["n"] == 1


def test_second_call_hits_sqlite(cache: SqliteCache):
    calls = {"n": 0}

    def compute(x: str) -> dict:
        calls["n"] += 1
        return {"x": x}

    ca = CachedAnalyzer(cache, version="v1")
    ca.get_or_compute("word", "amo", compute)

    # Clear in-memory LRU to force SQLite hit
    ca.clear_memory_cache()

    result = ca.get_or_compute("word", "amo", compute)
    assert result == {"x": "amo"}
    assert calls["n"] == 1  # compute not called again


def test_version_bump_invalidates(cache: SqliteCache):
    calls = {"n": 0}

    def compute(x: str) -> dict:
        calls["n"] += 1
        return {"x": x}

    ca_v1 = CachedAnalyzer(cache, version="v1")
    ca_v1.get_or_compute("word", "amo", compute)

    ca_v2 = CachedAnalyzer(cache, version="v2")
    ca_v2.get_or_compute("word", "amo", compute)

    assert calls["n"] == 2
