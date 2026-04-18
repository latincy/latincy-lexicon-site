def test_healthz_returns_versions(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "versions" in body
    assert "latincy_lexicon_site" in body["versions"]
    assert "latincy_lexicon" in body["versions"]
    assert "spacy_model" in body["versions"]


def test_pipeline_attached_to_app_state(client):
    # Invoking a route that needs nlp proves state is wired (done by later tasks).
    # For now: healthz must not error even with full lifespan.
    assert client.get("/healthz").status_code == 200
