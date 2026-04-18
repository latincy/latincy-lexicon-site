def test_landing_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "LatinCy Lexicon" in r.text
    assert 'name="text"' in r.text  # form field present
