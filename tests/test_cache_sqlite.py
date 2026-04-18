from pathlib import Path

import pytest

from latincy_lexicon_site.cache import SqliteCache


@pytest.fixture
def cache(tmp_path: Path) -> SqliteCache:
    return SqliteCache(tmp_path / "cache.db")


def test_miss_returns_none(cache: SqliteCache):
    assert cache.get("missing") is None


def test_round_trip(cache: SqliteCache):
    cache.set("k", b'{"hello": "world"}')
    assert cache.get("k") == b'{"hello": "world"}'


def test_overwrite(cache: SqliteCache):
    cache.set("k", b"first")
    cache.set("k", b"second")
    assert cache.get("k") == b"second"


def test_row_count(cache: SqliteCache):
    cache.set("a", b"1")
    cache.set("b", b"2")
    assert cache.rows() == 2
