def test_word_page_renders(client):
    r = client.get("/word/amo")
    assert r.status_code == 200
    assert "amo" in r.text


def test_word_page_handles_inflected_form(client):
    r = client.get("/word/amabam")
    assert r.status_code == 200
    # Should show some entry, lemma should resolve
    assert "amabam" in r.text or "amo" in r.text.lower()


def test_word_page_expands_whitaker_codes(client):
    """Age/freq/area codes should render as human labels, not raw letters.

    `arma` has age=X (all eras), freq=A (very frequent), area=W (military).
    """
    r = client.get("/word/arma")
    assert r.status_code == 200
    assert "all eras" in r.text
    assert "very frequent" in r.text
    assert "military" in r.text


def test_word_page_renders_principal_parts_reconstructed(client):
    """Verb entries should show reconstructed citation forms, not raw stems."""
    r = client.get("/word/scribo")
    assert r.status_code == 200
    assert "scribo, scribere, scripsi, scriptum" in r.text
    # Raw stems should NOT appear as the principal-parts line
    assert "scrib, scrib, scrips, script" not in r.text
