"""Tests for API endpoint response shapes."""

from fastapi.testclient import TestClient

from app.main import create_app


class TestCapabilities:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_capabilities(self) -> None:
        resp = self.client.get("/v1/capabilities")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "version" in data
        assert "operations" in data
        assert isinstance(data["operations"], list)
        assert len(data["operations"]) > 0

    def test_capabilities_has_get_and_post(self) -> None:
        resp = self.client.get("/v1/capabilities")
        ops = resp.json()["data"]["operations"]
        methods = {op["method"] for op in ops}
        assert "GET" in methods
        assert "POST" in methods


class TestAuth:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_login_init(self) -> None:
        resp = self.client.get("/v1/auth/login", params={"profile": "test"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "authorization_url" in data
        assert "state" in data

    def test_login_no_browser(self) -> None:
        resp = self.client.get("/v1/auth/login", params={"no_browser": "true"})
        assert resp.status_code == 200

    def test_token_exchange(self) -> None:
        resp = self.client.post("/v1/auth/token", json={
            "grant_type": "authorization_code",
            "code": "test-code",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"

    def test_token_exchange_missing_code(self) -> None:
        resp = self.client.post("/v1/auth/token", json={
            "grant_type": "authorization_code",
        })
        assert resp.status_code == 400

    def test_logout(self) -> None:
        resp = self.client.post("/v1/auth/logout")
        assert resp.status_code == 204

    def test_callback_redirect(self) -> None:
        resp = self.client.get("/v1/auth/callback", params={"code": "test", "state": "st"}, follow_redirects=False)
        assert resp.status_code == 302


class TestProfiles:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_create_and_list_profile(self) -> None:
        resp = self.client.post("/v1/profiles", json={
            "federee": "ECMWF",
            "region": "CC1",
            "tenant_name": "test-tenant",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["federee"] == "ECMWF"
        assert data["region"] == "CC1"

        resp = self.client.get("/v1/profiles")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    def test_show_profile(self) -> None:
        self.client.post("/v1/profiles", json={
            "federee": "ECMWF", "region": "CC1", "tenant_name": "show-test",
        })
        resp = self.client.get("/v1/profiles/ecmwf-cc1-show-test")
        assert resp.status_code == 200

    def test_show_profile_not_found(self) -> None:
        resp = self.client.get("/v1/profiles/nonexistent")
        assert resp.status_code == 404

    def test_delete_profile(self) -> None:
        self.client.post("/v1/profiles", json={
            "federee": "ECMWF", "region": "CC1", "tenant_name": "delete-test",
        })
        resp = self.client.delete("/v1/profiles/ecmwf-cc1-delete-test")
        assert resp.status_code == 204

    def test_create_duplicate_profile(self) -> None:
        self.client.post("/v1/profiles", json={
            "federee": "ECMWF", "region": "CC1", "tenant_name": "dup-test",
        })
        resp = self.client.post("/v1/profiles", json={
            "federee": "ECMWF", "region": "CC1", "tenant_name": "dup-test",
        })
        assert resp.status_code == 409


class TestServers:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_servers(self) -> None:
        resp = self.client.get("/v1/servers")
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_create_server_async(self) -> None:
        resp = self.client.post("/v1/servers", json={
            "server_name": "test-vm",
            "image_name": "Rocky-9",
        })
        assert resp.status_code == 202
        data = resp.json()["data"]
        assert "job_id" in data
        assert data["resource_type"] == "server"
        assert data["operation"] == "create"

    def test_create_server_dry_run(self) -> None:
        resp = self.client.post("/v1/servers", params={"dry_run": "true"}, json={
            "server_name": "dry-run-vm",
        })
        assert resp.status_code == 202
        data = resp.json()["data"]
        assert data["status"] == "completed"

    def test_delete_server_async(self) -> None:
        resp = self.client.delete("/v1/servers/test-vm")
        assert resp.status_code == 202
        assert "job_id" in resp.json()["data"]

    def test_reconfigure_server(self) -> None:
        resp = self.client.post("/v1/servers/test-vm/reconfigure", json={
            "server_name": "test-vm",
        })
        assert resp.status_code == 202
        assert resp.json()["data"]["operation"] == "reconfigure"


class TestHub:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_hub_items(self) -> None:
        resp = self.client.get("/v1/hub/items")
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_show_hub_item(self) -> None:
        resp = self.client.get("/v1/hub/items/example-app")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "example-app"

    def test_show_hub_item_not_found(self) -> None:
        resp = self.client.get("/v1/hub/items/nonexistent")
        assert resp.status_code == 404

    def test_deploy_hub_item(self) -> None:
        resp = self.client.post("/v1/hub/items/example-app/deploy", json={
            "item_name": "example-app",
            "server_name": "deploy-vm",
        })
        assert resp.status_code == 202
        assert resp.json()["data"]["resource_type"] == "hub"


class TestKeypairs:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_keypairs(self) -> None:
        resp = self.client.get("/v1/keypairs")
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_create_keypair(self) -> None:
        resp = self.client.post("/v1/keypairs", json={
            "keypair_name": "test-key",
            "public_key": "ssh-rsa AAAA...",
        })
        assert resp.status_code == 202

    def test_delete_keypair(self) -> None:
        resp = self.client.delete("/v1/keypairs/test-key")
        assert resp.status_code == 202


class TestDns:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_dns_records(self) -> None:
        resp = self.client.get("/v1/dns/records")
        assert resp.status_code == 200

    def test_create_dns_record(self) -> None:
        resp = self.client.post("/v1/dns/records", json={
            "record_name": "test.example.com",
            "record_type": "A",
            "rdata": "10.0.0.1",
        })
        assert resp.status_code == 202

    def test_delete_dns_record(self) -> None:
        resp = self.client.delete("/v1/dns/records/test.example.com")
        assert resp.status_code == 202


class TestS3:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_s3_buckets(self) -> None:
        resp = self.client.get("/v1/s3/buckets")
        assert resp.status_code == 200

    def test_create_s3_bucket(self) -> None:
        resp = self.client.post("/v1/s3/buckets", json={
            "bucket_name": "test-bucket",
            "access_id": "owner-123",
        })
        assert resp.status_code == 202

    def test_delete_s3_bucket(self) -> None:
        resp = self.client.delete("/v1/s3/buckets/test-bucket")
        assert resp.status_code == 202


class TestJobs:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_jobs(self) -> None:
        resp = self.client.get("/v1/jobs")
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_get_job_not_found(self) -> None:
        resp = self.client.get("/v1/jobs/nonexistent")
        assert resp.status_code == 404

    def test_job_lifecycle(self) -> None:
        """Create a dry-run server job, then query it."""
        resp = self.client.post("/v1/servers", params={"dry_run": "true"}, json={
            "server_name": "lifecycle-vm",
        })
        assert resp.status_code == 202
        job_id = resp.json()["data"]["job_id"]

        resp = self.client.get(f"/v1/jobs/{job_id}")
        assert resp.status_code == 200
        job = resp.json()["data"]
        assert job["job_id"] == job_id

        resp = self.client.get(f"/v1/jobs/{job_id}/logs")
        assert resp.status_code == 200

        resp = self.client.get(f"/v1/jobs/{job_id}/outputs")
        assert resp.status_code == 200
