def test_word_page_cache_header(client):
    r = client.get("/word/amo")
    assert r.headers.get("cache-control") == "public, max-age=86400"


def test_paradigm_page_cache_header(client):
    r = client.get("/paradigm/amo")
    assert r.headers.get("cache-control") == "public, max-age=86400"


def test_sentence_page_cache_header(client):
    r = client.get("/sentence", params={"text": "amo te."})
    assert r.headers.get("cache-control") == "public, max-age=3600"


def test_api_word_cache_header(client):
    r = client.get("/api/v1/word/amo")
    assert r.headers.get("cache-control") == "public, max-age=86400"


def test_api_sentence_cache_header(client):
    r = client.get("/api/v1/sentence", params={"text": "amo te."})
    assert r.headers.get("cache-control") == "public, max-age=3600"


def test_fragments_no_store(client):
    r = client.get("/fragments/word/amo")
    assert "no-store" in r.headers.get("cache-control", "")
