"""Tests for health and readiness endpoints."""

from fastapi.testclient import TestClient

from app.main import create_app


class TestHealth:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_healthz_returns_200(self) -> None:
        resp = self.client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readyz_returns_200(self) -> None:
        resp = self.client.get("/readyz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_request_id_header(self) -> None:
        resp = self.client.get("/healthz")
        assert "X-Request-ID" in resp.headers

    def test_request_id_echoed(self) -> None:
        resp = self.client.get("/healthz", headers={"X-Request-ID": "test-123"})
        assert resp.headers["X-Request-ID"] == "test-123"
