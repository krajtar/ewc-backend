"""DNS router response shape tests."""

from fastapi.testclient import TestClient


def test_list_dns_records_empty(client: TestClient):
    """GET /v1/dns/records returns 200 with list envelope."""
    resp = client.get("/v1/dns/records")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert "meta" in body


def test_create_dns_record_async(client: TestClient):
    """POST /v1/dns/records returns 202 with JobRef envelope."""
    resp = client.post("/v1/dns/records", json={
        "record_name": "test-record",
        "record_type": "A",
        "rdata": "192.0.2.1",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "job_id" in data
    assert data["resource_type"] == "dns"
    assert data["resource_name"] == "test-record"
    assert data["operation"] == "create"


def test_show_dns_record_not_found(client: TestClient):
    """GET /v1/dns/records/{nonexistent} returns 404."""
    resp = client.get("/v1/dns/records/nonexistent-record")
    assert resp.status_code == 404


def test_delete_dns_record_async(client: TestClient):
    """DELETE /v1/dns/records/{name} returns 202 with JobRef."""
    resp = client.delete("/v1/dns/records/test-record-del")
    assert resp.status_code == 202
    body = resp.json()
    data = body["data"]
    assert data["resource_type"] == "dns"
    assert data["operation"] == "delete"
