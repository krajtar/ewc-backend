"""Auth router response shape tests."""

from fastapi.testclient import TestClient


def test_login_init(client: TestClient):
    """GET /v1/auth/login returns 200 with authorization_url and state."""
    resp = client.get("/v1/auth/login")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "authorization_url" in data
    assert "state" in data
    assert isinstance(data["authorization_url"], str)
    assert len(data["authorization_url"]) > 0
    assert len(data["state"]) > 0


def test_login_no_browser(client: TestClient):
    """GET /v1/auth/login?no_browser=true still returns 200."""
    resp = client.get("/v1/auth/login", params={"no_browser": "true"})
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "authorization_url" in body["data"]


def test_login_with_profile(client: TestClient):
    """GET /v1/auth/login?profile=foo returns profile in response."""
    resp = client.get("/v1/auth/login", params={"profile": "my-profile"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["profile"] == "my-profile"


def test_auth_callback(client: TestClient):
    """GET /v1/auth/callback returns 302 redirect."""
    resp = client.get("/v1/auth/callback", params={"code": "test-code", "state": "test-state"}, follow_redirects=False)
    assert resp.status_code == 302
    assert "location" in resp.headers


def test_token_exchange(client: TestClient):
    """POST /v1/auth/token returns 200 with token fields."""
    resp = client.post("/v1/auth/token", json={
        "grant_type": "authorization_code",
        "code": "test-code",
        "redirect_uri": "http://localhost:8000/callback",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "Bearer"
    assert isinstance(body["expires_in"], int)


def test_token_refresh(client: TestClient):
    """POST /v1/auth/token with refresh_token grant returns 200."""
    resp = client.post("/v1/auth/token", json={
        "grant_type": "refresh_token",
        "refresh_token": "old-refresh",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body


def test_logout(client: TestClient):
    """POST /v1/auth/logout returns 204."""
    resp = client.post("/v1/auth/logout")
    assert resp.status_code == 204
