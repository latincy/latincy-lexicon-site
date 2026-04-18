def test_word_page_renders(client):
    r = client.get("/word/amo")
    assert r.status_code == 200
    assert "amo" in r.text


def test_word_page_handles_inflected_form(client):
    r = client.get("/word/amabam")
    assert r.status_code == 200
    # Should show some entry, lemma should resolve
    assert "amabam" in r.text or "amo" in r.text.lower()
