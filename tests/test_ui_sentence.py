def test_sentence_page_renders(client):
    r = client.get("/sentence", params={"text": "amo te."})
    assert r.status_code == 200
    assert "amo" in r.text.lower()
    assert "<table" in r.text


def test_sentence_page_truncates_and_shows_notice(client):
    long_text = " ".join(["verbum"] * 75)
    r = client.get("/sentence", params={"text": long_text})
    assert r.status_code == 200
    assert "analyzing the first" in r.text
    assert "75 words" in r.text


def test_single_word_input_redirects_to_word_page(client):
    r = client.get("/sentence", params={"text": "amabam"}, follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"].endswith("/word/amabam")


def test_single_word_with_trailing_punct_redirects_cleanly(client):
    r = client.get("/sentence", params={"text": "amo."}, follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"].endswith("/word/amo")
