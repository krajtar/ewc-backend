"""S3 router response shape tests."""

from fastapi.testclient import TestClient


def test_list_s3_buckets_empty(client: TestClient):
    """GET /v1/s3/buckets returns 200 with data array."""
    resp = client.get("/v1/s3/buckets")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)


def test_create_s3_bucket_async(client: TestClient):
    """POST /v1/s3/buckets returns 202 with JobRef envelope."""
    resp = client.post("/v1/s3/buckets", json={
        "bucket_name": "test-bucket",
        "access_id": "owner-1",
    })
    assert resp.status_code == 202
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "job_id" in data
    assert data["resource_type"] == "s3"
    assert data["resource_name"] == "test-bucket"
    assert data["operation"] == "create"


def test_create_s3_bucket_dry_run(client: TestClient):
    """POST /v1/s3/buckets?dry_run=true returns 202."""
    resp = client.post("/v1/s3/buckets", json={
        "bucket_name": "dry-bucket",
        "access_id": "owner-2",
    }, params={"dry_run": "true"})
    assert resp.status_code == 202
    assert "data" in resp.json()


def test_delete_s3_bucket_async(client: TestClient):
    """DELETE /v1/s3/buckets/{name} returns 202 with JobRef."""
    resp = client.delete("/v1/s3/buckets/test-bucket-del")
    assert resp.status_code == 202
    body = resp.json()
    data = body["data"]
    assert data["resource_type"] == "s3"
    assert data["operation"] == "delete"
