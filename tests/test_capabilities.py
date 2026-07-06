"""Capabilities router response shape tests."""

from fastapi.testclient import TestClient


def test_list_capabilities(client: TestClient):
    """GET /v1/capabilities returns 200 with version and operations."""
    resp = client.get("/v1/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "version" in data
    assert "operations" in data
    assert isinstance(data["operations"], list)
    assert len(data["operations"]) > 0


def test_capabilities_operation_shape(client: TestClient):
    """Each capability operation has the required fields."""
    resp = client.get("/v1/capabilities")
    ops = resp.json()["data"]["operations"]
    for op in ops:
        assert "method" in op
        assert "path" in op
        assert "summary" in op
        assert "async_" in op
        assert "required_scopes" in op
        assert "supports_dry_run" in op


def test_capabilities_includes_all_routers(client: TestClient):
    """Capabilities catalog references all 9 API routers."""
    resp = client.get("/v1/capabilities")
    paths = {op["path"] for op in resp.json()["data"]["operations"]}
    # Check at least one path from each router
    expected_prefixes = [
        "/v1/auth/",
        "/v1/profiles",
        "/v1/servers",
        "/v1/hub/",
        "/v1/keypairs",
        "/v1/dns/",
        "/v1/s3/",
        "/v1/jobs",
        "/v1/capabilities",
    ]
    for prefix in expected_prefixes:
        assert any(p.startswith(prefix) for p in paths), f"No capability path starts with {prefix}"
