def test_landing_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "LatinCy" in r.text
    assert 'name="text"' in r.text  # form field present


def test_brand_splits_lexicon_for_black_styling(client):
    """'Lexicon' should be wrapped so it can be styled black while
    'LatinCy' takes the brand accent color."""
    r = client.get("/")
    assert '<span class="brand-lexicon">Lexicon</span>' in r.text
