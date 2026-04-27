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


def test_sentence_entries_top_sense_is_unique(client):
    """Only one entry per token carries top_sense=True — it drives both
    the accent styling and the ✓ badge; every other entry is muted."""
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


def test_word_lookup_marks_top_sense_without_pos_context(client):
    """Standalone /word/{form} has no token POS, but a single-entry form
    like amabam should still render with the accent (top_sense=True),
    not greyed out as 'no annotated sense available'."""
    r = client.get("/api/v1/word/amabam")
    assert r.status_code == 200
    analyses = r.json()["analyses"]
    assert analyses, "amabam should have at least one analysis"
    tops = [e for e in analyses if e.get("top_sense")]
    assert len(tops) == 1, (
        f"expected exactly one top_sense entry, got {len(tops)}"
    )


def test_fragment_word_badge_marks_single_top_sense(client):
    """Expanded-entry fragment with ?pos= applies the accent class and
    the ✓ badge to exactly one entry — the top sense."""
    r = client.get("/fragments/word/bonus", params={"pos": "ADJ"})
    assert r.status_code == 200
    assert r.text.count("entry--top-sense") == 1
    assert r.text.count("pos-match-badge") == 1
