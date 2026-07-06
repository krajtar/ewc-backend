"""Health and readiness endpoint tests."""

from fastapi.testclient import TestClient


def test_healthz(client: TestClient):
    """GET /healthz returns 200 with status ok."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_readyz(client: TestClient):
    """GET /readyz returns 200 with status ready."""
    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"


def test_healthz_response_shape(client: TestClient):
    """healthz response has exactly the expected shape."""
    resp = client.get("/healthz")
    body = resp.json()
    assert isinstance(body, dict)
    assert set(body.keys()) == {"status"}


def test_readyz_response_shape(client: TestClient):
    """readyz response has exactly the expected shape."""
    resp = client.get("/readyz")
    body = resp.json()
    assert isinstance(body, dict)
    assert set(body.keys()) == {"status"}


def test_docs_available(client: TestClient):
    """Swagger UI docs endpoint is accessible."""
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_openapi_json_available(client: TestClient):
    """OpenAPI JSON spec is accessible."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"] == "EWC Backend API"
    assert "paths" in spec
