def test_robots(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Disallow: /api/" in r.text
    assert "Disallow: /fragments/" in r.text
    assert "Allow: /word/" in r.text


def test_sitemap(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<urlset" in r.text
