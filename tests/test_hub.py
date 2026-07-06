"""Hub router response shape tests."""

from fastapi.testclient import TestClient


def test_list_hub_items(client: TestClient):
    """GET /v1/hub/items returns 200 with list envelope."""
    resp = client.get("/v1/hub/items")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    assert "meta" in body


def test_hub_item_summary_shape(client: TestClient):
    """Each hub item summary has the expected fields."""
    resp = client.get("/v1/hub/items")
    items = resp.json()["data"]
    item = items[0]
    assert "name" in item
    assert "title" in item
    assert "version" in item


def test_show_hub_item(client: TestClient):
    """GET /v1/hub/items/{name} returns 200 with detail."""
    resp = client.get("/v1/hub/items/example-app")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert data["name"] == "example-app"
    assert "title" in data
    assert "sources" in data
    assert "ewccli" in data


def test_show_hub_item_not_found(client: TestClient):
    """GET /v1/hub/items/{nonexistent} returns 404."""
    resp = client.get("/v1/hub/items/nonexistent-item")
    assert resp.status_code == 404


def test_deploy_hub_item_async(client: TestClient):
    """POST /v1/hub/items/{name}/deploy returns 202 with JobRef."""
    resp = client.post("/v1/hub/items/example-app/deploy", json={
        "item_name": "example-app",
        "server_name": "deploy-target-1",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "job_id" in data
    assert data["resource_type"] == "hub"
    assert data["operation"] == "deploy"
