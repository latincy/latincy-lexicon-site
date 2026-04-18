def test_api_paradigm_returns_forms(client):
    r = client.get("/api/v1/paradigm/amo")
    assert r.status_code == 200
    body = r.json()
    assert body["lemma"] == "amo"
    assert isinstance(body["forms"], list)
    assert len(body["forms"]) > 0


def test_api_paradigm_filtered_by_pos(client):
    r = client.get("/api/v1/paradigm/malus", params={"pos": "ADJ"})
    assert r.status_code == 200
    body = r.json()
    assert body["pos"] == "ADJ"
    for f in body["forms"]:
        assert f["upos"] == "ADJ"
