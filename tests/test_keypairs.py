"""Keypairs router response shape tests."""

from fastapi.testclient import TestClient


def test_list_keypairs_empty(client: TestClient):
    """GET /v1/keypairs returns 200 with data array."""
    resp = client.get("/v1/keypairs")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)


def test_create_keypair_async(client: TestClient):
    """POST /v1/keypairs returns 202 with JobRef envelope."""
    resp = client.post("/v1/keypairs", json={
        "keypair_name": "test-key-1",
        "public_key": "ssh-rsa AAAA...",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "job_id" in data
    assert data["resource_type"] == "keypair"
    assert data["resource_name"] == "test-key-1"
    assert data["operation"] == "create"


def test_create_keypair_dry_run(client: TestClient):
    """POST /v1/keypairs?dry_run=true returns 202."""
    resp = client.post("/v1/keypairs", json={
        "keypair_name": "dry-key",
    }, params={"dry_run": "true"})
    assert resp.status_code == 202
    assert "data" in resp.json()


def test_delete_keypair_async(client: TestClient):
    """DELETE /v1/keypairs/{name} returns 202 with JobRef."""
    resp = client.delete("/v1/keypairs/test-key-delete")
    assert resp.status_code == 202
    body = resp.json()
    data = body["data"]
    assert data["resource_type"] == "keypair"
    assert data["operation"] == "delete"
    assert data["resource_name"] == "test-key-delete"
