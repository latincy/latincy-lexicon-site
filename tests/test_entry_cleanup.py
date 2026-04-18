"""Regression tests for site-side cleanup of raw whitakers_words entries."""


def test_prefix_entries_filtered_on_word(client):
    r = client.get("/api/v1/word/sed")
    assert r.status_code == 200
    body = r.json()
    for entry in body["analyses"]:
        assert entry.get("pos") != "PREFIX"


def test_gloss_leading_pipe_stripped_on_word(client):
    r = client.get("/api/v1/word/cura")
    assert r.status_code == 200
    body = r.json()
    for entry in body["analyses"]:
        for gloss in entry.get("glosses") or []:
            if isinstance(gloss, str):
                assert not gloss.startswith("|"), f"leading pipe in: {gloss!r}"


def test_prefix_entries_filtered_in_sentence(client):
    r = client.get("/api/v1/sentence", params={"text": "sed amo."})
    assert r.status_code == 200
    for tok in r.json()["tokens"]:
        for entry in tok.get("entries") or []:
            assert entry.get("pos") != "PREFIX"
