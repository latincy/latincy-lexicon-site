"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
import spacy
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_nlp():
    """Load la_core_web_sm once per test session — faster than la_core_web_lg."""
    return spacy.load(
        "la_core_web_sm",
        disable=["parser", "ner", "senter", "normer", "uv_normalizer", "harmonizer", "remorpher"],
    )


@pytest.fixture(scope="session")
def monkeypatch_session():
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="session")
def client(tmp_path_factory, monkeypatch_session) -> TestClient:
    """Test client with lifespan wired to la_core_web_sm + tmp cache."""
    monkeypatch_session.setenv("LATINCY_SITE_MODEL", "la_core_web_sm")
    monkeypatch_session.setenv(
        "LATINCY_SITE_CACHE_PATH",
        str(tmp_path_factory.mktemp("cache") / "cache.db"),
    )
    from latincy_lexicon_site.main import app

    with TestClient(app) as c:
        yield c
