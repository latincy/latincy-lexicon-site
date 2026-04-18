def test_api_sentence_returns_tokens(client):
    r = client.get("/api/v1/sentence", params={"text": "Poeta bonus carmina scribit."})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "Poeta bonus carmina scribit."
    assert len(body["tokens"]) >= 4


def test_api_sentence_truncates_over_50_words(client):
    long_text = " ".join(["verbum"] * 75)
    r = client.get("/api/v1/sentence", params={"text": long_text})
    assert r.status_code == 200
    body = r.json()
    assert body["truncated"] is True
    assert body["original_word_count"] == 75
    assert body["word_cap"] == 50
