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
    """bonus has both ADJ and NOUN senses in WW; all POS-matching senses
    are flagged with pos_match for the border-highlight styling."""
    r = client.get("/api/v1/sentence", params={"text": "bonus vir"})
    assert r.status_code == 200
    tokens = {t["text"]: t for t in r.json()["tokens"]}
    bonus = tokens.get("bonus")
    assert bonus is not None
    assert bonus["pos"] == "ADJ"
    for entry in bonus["entries"]:
        expected = "ADJ" in (entry.get("ud_pos") or [])
        assert entry.get("pos_match") is expected


def test_sentence_entries_top_sense_is_unique(client):
    """Only one entry per token carries top_sense=True — the badge target."""
    r = client.get("/api/v1/sentence", params={"text": "bonus vir"})
    assert r.status_code == 200
    for tok in r.json()["tokens"]:
        entries = tok.get("entries") or []
        tops = [e for e in entries if e.get("top_sense")]
        assert len(tops) <= 1
        if tops:
            assert tok["pos"] in (tops[0].get("ud_pos") or [])


def test_top_sense_is_frequency_weighted(client):
    """carmen has freq=A (song) and freq=F (wool-card) noun senses; the
    top_sense pick must land on the freq=A entry, never the rare one."""
    r = client.get("/api/v1/sentence", params={"text": "Horatius carmen cantat."})
    assert r.status_code == 200
    tokens = {t["text"]: t for t in r.json()["tokens"]}
    carmen = tokens.get("carmen")
    assert carmen is not None
    carmen_entries = [
        e for e in carmen["entries"]
        if (e.get("headword") or "").lower().startswith("carmen")
    ]
    tops = [e for e in carmen_entries if e.get("top_sense")]
    assert len(tops) == 1
    assert tops[0].get("freq") == "A"


def test_sentence_tokens_expose_xpos_tag(client):
    r = client.get("/api/v1/sentence", params={"text": "bonus vir"})
    assert r.status_code == 200
    for tok in r.json()["tokens"]:
        assert "tag" in tok
        assert isinstance(tok["tag"], str)


def test_fragment_word_badge_marks_single_top_sense(client):
    """Expanded-entry fragment with ?pos= marks pos-match on all NOUN/ADJ
    entries (border) but only the top sense gets the ✓ badge."""
    r = client.get("/fragments/word/bonus", params={"pos": "ADJ"})
    assert r.status_code == 200
    assert "entry--pos-match" in r.text
    assert r.text.count("pos-match-badge") == 1
