"""Profiles router response shape tests."""

from fastapi.testclient import TestClient


def test_list_profiles_empty(client: TestClient):
    """GET /v1/profiles returns 200 with empty data array initially."""
    resp = client.get("/v1/profiles")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 0


def test_create_profile(client: TestClient):
    """POST /v1/profiles returns 201 with profile data."""
    resp = client.post("/v1/profiles", json={
        "federee": "example-org",
        "region": "eu-central",
        "tenant_name": "tenant-1",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert data["federee"] == "example-org"
    assert data["region"] == "eu-central"
    assert data["tenant_name"] == "tenant-1"
    assert "profile_id" in data
    assert "created_at" in data


def test_create_profile_conflict(client: TestClient):
    """POST /v1/profiles with duplicate returns 409."""
    payload = {"federee": "dup-org", "region": "eu-west", "tenant_name": "t1"}
    resp1 = client.post("/v1/profiles", json=payload)
    assert resp1.status_code == 201
    resp2 = client.post("/v1/profiles", json=payload)
    assert resp2.status_code == 409
    detail = resp2.json()["detail"]
    assert detail["code"] == "PROFILE_EXISTS"


def test_show_profile(client: TestClient):
    """GET /v1/profiles/{id} returns 200 with profile data."""
    create = client.post("/v1/profiles", json={
        "federee": "show-org", "region": "eu-north", "tenant_name": "t2",
    })
    pid = create.json()["data"]["profile_id"]
    resp = client.get(f"/v1/profiles/{pid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["profile_id"] == pid


def test_show_profile_not_found(client: TestClient):
    """GET /v1/profiles/{nonexistent} returns 404."""
    resp = client.get("/v1/profiles/nonexistent-profile")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "NOT_FOUND"


def test_update_profile(client: TestClient):
    """PUT /v1/profiles/{id} returns 200 with updated data."""
    create = client.post("/v1/profiles", json={
        "federee": "upd-org", "region": "eu-south", "tenant_name": "t3",
    })
    pid = create.json()["data"]["profile_id"]
    resp = client.put(f"/v1/profiles/{pid}", json={"ssh_public_key_path": "/new/key.pub"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["ssh_public_key_path"] == "/new/key.pub"


def test_delete_profile(client: TestClient):
    """DELETE /v1/profiles/{id} returns 204."""
    create = client.post("/v1/profiles", json={
        "federee": "del-org", "region": "eu-east", "tenant_name": "t4",
    })
    pid = create.json()["data"]["profile_id"]
    resp = client.delete(f"/v1/profiles/{pid}")
    assert resp.status_code == 204
    # Verify it's gone
    resp2 = client.get(f"/v1/profiles/{pid}")
    assert resp2.status_code == 404
