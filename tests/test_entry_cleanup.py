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


def test_sentence_entries_annotate_pos_match(client):
    """bonus has both ADJ and NOUN senses in WW; we keep both but mark
    the one matching the LatinCy POS so the UI can highlight it."""
    r = client.get("/api/v1/sentence", params={"text": "bonus vir"})
    assert r.status_code == 200
    tokens = {t["text"]: t for t in r.json()["tokens"]}
    bonus = tokens.get("bonus")
    assert bonus is not None
    assert bonus["pos"] == "ADJ"
    for entry in bonus["entries"]:
        expected = "ADJ" in (entry.get("ud_pos") or [])
        assert entry.get("pos_match") is expected


def test_sentence_tokens_expose_xpos_tag(client):
    r = client.get("/api/v1/sentence", params={"text": "bonus vir"})
    assert r.status_code == 200
    for tok in r.json()["tokens"]:
        assert "tag" in tok
        assert isinstance(tok["tag"], str)


def test_fragment_word_annotates_pos_match(client):
    """Expanded-entry fragment with ?pos= marks matching entries."""
    r = client.get("/fragments/word/bonus", params={"pos": "ADJ"})
    assert r.status_code == 200
    assert "entry--pos-match" in r.text
    assert "annotated sense" in r.text
