def test_rate_limit_returns_429_after_quota(client, monkeypatch):
    """Tighten the quota via env var and confirm the 3rd call 429s."""
    monkeypatch.setenv("LATINCY_SITE_API_QUOTA", "2/minute")
    client.app.state.limiter.reset()
    try:
        r1 = client.get("/api/v1/word/amo")
        r2 = client.get("/api/v1/word/amo")
        r3 = client.get("/api/v1/word/amo")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
    finally:
        client.app.state.limiter.reset()
