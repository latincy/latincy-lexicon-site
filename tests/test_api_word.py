def test_api_word_returns_analyses(client):
    r = client.get("/api/v1/word/amo")
    assert r.status_code == 200
    body = r.json()
    assert body["form"] == "amo"
    assert "normalized" in body
    assert isinstance(body["analyses"], list)


def test_api_word_cached_second_call(client):
    r1 = client.get("/api/v1/word/amo").json()
    r2 = client.get("/api/v1/word/amo").json()
    assert r1 == r2
