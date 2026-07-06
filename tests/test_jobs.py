"""Jobs router response shape tests."""

from fastapi.testclient import TestClient


def test_list_jobs_empty(client: TestClient):
    """GET /v1/jobs returns 200 with list envelope."""
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert "meta" in body


def test_get_job_not_found(client: TestClient):
    """GET /v1/jobs/{nonexistent} returns 404."""
    resp = client.get("/v1/jobs/nonexistent-job")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "NOT_FOUND"


def test_get_job_logs_not_found(client: TestClient):
    """GET /v1/jobs/{nonexistent}/logs returns 404."""
    resp = client.get("/v1/jobs/nonexistent-job/logs")
    assert resp.status_code == 404


def test_get_job_outputs_not_found(client: TestClient):
    """GET /v1/jobs/{nonexistent}/outputs returns 404."""
    resp = client.get("/v1/jobs/nonexistent-job/outputs")
    assert resp.status_code == 404


def test_cancel_job_not_found(client: TestClient):
    """POST /v1/jobs/{nonexistent}/cancel returns 404."""
    resp = client.post("/v1/jobs/nonexistent-job/cancel")
    assert resp.status_code == 404


def test_job_lifecycle(client: TestClient):
    """Create a server (async job), then fetch the job status."""
    # Create a server — this submits a job
    create = client.post("/v1/servers", json={"server_name": "lifecycle-vm"})
    assert create.status_code == 202
    job_id = create.json()["data"]["job_id"]

    # Fetch the job
    resp = client.get(f"/v1/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert data["job_id"] == job_id
    assert "status" in data
    assert "resource_type" in data
    assert "operation" in data
    assert "created_at" in data


def test_job_logs_shape(client: TestClient):
    """GET /v1/jobs/{id}/logs returns logs with expected shape."""
    create = client.post("/v1/servers", json={"server_name": "logs-vm"})
    job_id = create.json()["data"]["job_id"]

    resp = client.get(f"/v1/jobs/{job_id}/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "logs" in data
    assert "has_more" in data
    assert isinstance(data["logs"], list)


def test_job_outputs_shape(client: TestClient):
    """GET /v1/jobs/{id}/outputs returns outputs with expected shape."""
    create = client.post("/v1/servers", json={"server_name": "outputs-vm"})
    job_id = create.json()["data"]["job_id"]

    resp = client.get(f"/v1/jobs/{job_id}/outputs")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "outputs" in body["data"]
