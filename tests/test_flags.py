"""Tests for the crowdsourced flag system.

The feature is gated by LATINCY_SITE_FLAGS_ENABLED. Session `client`
fixture boots with the var unset, so baseline coverage checks that the
endpoint is invisible and the UI hides the widget. Toggling via
monkeypatch.setenv proves the same endpoint/UI activate once flipped on.
"""


def test_flag_submit_404_when_disabled(client):
    r = client.post(
        "/flags/submit",
        json={"target_type": "word", "subject": "amo", "issue": "wrong-gloss"},
    )
    assert r.status_code == 404


def test_flag_button_hidden_on_word_page_by_default(client):
    r = client.get("/word/amo")
    assert r.status_code == 200
    assert "flag-btn" not in r.text


def test_flag_button_hidden_on_sentence_page_by_default(client):
    r = client.get("/sentence", params={"text": "amo te."})
    assert r.status_code == 200
    assert "flag-btn" not in r.text


def test_flag_submit_accepted_when_enabled(client, monkeypatch):
    monkeypatch.setenv("LATINCY_SITE_FLAGS_ENABLED", "1")
    before = client.app.state.flags.count()
    r = client.post(
        "/flags/submit",
        json={
            "target_type": "word",
            "subject": "amo",
            "issue": "wrong-gloss",
            "note": "glosses feel wrong",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "recorded"
    assert isinstance(body["id"], int)
    assert client.app.state.flags.count() == before + 1


def test_flag_button_visible_on_word_page_when_enabled(client, monkeypatch):
    monkeypatch.setenv("LATINCY_SITE_FLAGS_ENABLED", "1")
    r = client.get("/word/amo")
    assert r.status_code == 200
    assert "flag-btn" in r.text


def test_flag_button_visible_on_sentence_page_when_enabled(client, monkeypatch):
    monkeypatch.setenv("LATINCY_SITE_FLAGS_ENABLED", "1")
    r = client.get("/sentence", params={"text": "amo te."})
    assert r.status_code == 200
    assert "flag-btn" in r.text


def test_flag_rejects_bad_target_type(client, monkeypatch):
    monkeypatch.setenv("LATINCY_SITE_FLAGS_ENABLED", "1")
    r = client.post(
        "/flags/submit",
        json={"target_type": "bogus", "subject": "amo", "issue": "x"},
    )
    assert r.status_code == 422
