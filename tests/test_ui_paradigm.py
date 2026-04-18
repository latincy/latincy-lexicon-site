def test_paradigm_page_renders(client):
    r = client.get("/paradigm/amo")
    assert r.status_code == 200
    assert "amo" in r.text
