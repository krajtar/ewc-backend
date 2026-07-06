"""Servers router response shape tests."""

from fastapi.testclient import TestClient


def test_list_servers_empty(client: TestClient):
    """GET /v1/servers returns 200 with data array."""
    resp = client.get("/v1/servers")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)


def test_create_server_async(client: TestClient):
    """POST /v1/servers returns 202 with JobRef envelope."""
    resp = client.post("/v1/servers", json={
        "server_name": "test-vm-1",
        "image_name": "Rocky-9",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "job_id" in data
    assert "status" in data
    assert data["resource_type"] == "server"
    assert data["resource_name"] == "test-vm-1"
    assert data["operation"] == "create"
    assert "created_at" in data
    assert "estimated_duration_seconds" in data


def test_create_server_dry_run(client: TestClient):
    """POST /v1/servers?dry_run=true returns 202 with JobRef."""
    resp = client.post("/v1/servers", json={
        "server_name": "dry-run-vm",
    }, params={"dry_run": "true"})
    assert resp.status_code == 202
    body = resp.json()
    assert "data" in body
    assert "job_id" in body["data"]


def test_show_server_not_found(client: TestClient):
    """GET /v1/servers/{nonexistent} returns 404."""
    resp = client.get("/v1/servers/nonexistent-vm")
    assert resp.status_code == 404


def test_delete_server_async(client: TestClient):
    """DELETE /v1/servers/{name} returns 202 with JobRef."""
    resp = client.delete("/v1/servers/test-vm-delete")
    assert resp.status_code == 202
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert data["resource_type"] == "server"
    assert data["operation"] == "delete"


def test_reconfigure_server_async(client: TestClient):
    """POST /v1/servers/{name}/reconfigure returns 202 with JobRef."""
    resp = client.post("/v1/servers/test-vm-reconf/reconfigure", json={
        "server_name": "test-vm-reconf",
        "image_name": "Rocky-9",
    })
    assert resp.status_code == 202
    body = resp.json()
    data = body["data"]
    assert data["resource_type"] == "server"
    assert data["operation"] == "reconfigure"
