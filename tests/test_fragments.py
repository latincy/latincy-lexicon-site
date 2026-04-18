def test_fragment_word_returns_partial(client):
    r = client.get("/fragments/word/amo")
    assert r.status_code == 200
    # Partial should not include page chrome
    assert "<!doctype html>" not in r.text.lower()
    assert 'class="entry"' in r.text or "No dictionary entries" in r.text


def test_fragment_paradigm_returns_partial(client):
    r = client.get("/fragments/paradigm/amo")
    assert r.status_code == 200
    assert "<!doctype html>" not in r.text.lower()
