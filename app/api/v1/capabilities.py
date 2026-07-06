"""Capabilities endpoint — API discovery for AI agents."""

from fastapi import APIRouter

from app.models.job import CapabilitiesData, CapabilitiesOperation, CapabilitiesResponse

router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


@router.get("", response_model=CapabilitiesResponse)
async def list_capabilities() -> CapabilitiesResponse:
    """List API capabilities for agent discovery."""
    ops = [
        CapabilitiesOperation(method="GET", path="/v1/capabilities", summary="List API capabilities", async_=False, required_scopes=[], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="GET", path="/v1/auth/login", summary="Initiate OIDC login", async_=False, required_scopes=[], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/auth/token", summary="Exchange code or refresh token", async_=False, required_scopes=[], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/auth/logout", summary="Logout / revoke token", async_=False, required_scopes=[], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="GET", path="/v1/profiles", summary="List profiles", async_=False, required_scopes=["profile:read"], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/profiles", summary="Create a profile", async_=False, required_scopes=["profile:write"], estimated_duration_seconds=1, supports_dry_run=True),
        CapabilitiesOperation(method="GET", path="/v1/servers", summary="List servers", async_=False, required_scopes=["servers:read"], estimated_duration_seconds=5, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/servers", summary="Create a server", async_=True, required_scopes=["servers:write"], estimated_duration_seconds=600, supports_dry_run=True),
        CapabilitiesOperation(method="DELETE", path="/v1/servers/{serverName}", summary="Delete a server", async_=True, required_scopes=["servers:write"], estimated_duration_seconds=300, supports_dry_run=True),
        CapabilitiesOperation(method="POST", path="/v1/servers/{serverName}/reconfigure", summary="Reconfigure a server", async_=True, required_scopes=["servers:write"], estimated_duration_seconds=600, supports_dry_run=True),
        CapabilitiesOperation(method="GET", path="/v1/hub/items", summary="List hub items", async_=False, required_scopes=["hub:read"], estimated_duration_seconds=5, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/hub/items/{itemName}/deploy", summary="Deploy a hub item", async_=True, required_scopes=["hub:deploy"], estimated_duration_seconds=900, supports_dry_run=True),
        CapabilitiesOperation(method="GET", path="/v1/keypairs", summary="List keypairs", async_=False, required_scopes=["keypairs:read"], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/keypairs", summary="Create a keypair", async_=True, required_scopes=["keypairs:write"], estimated_duration_seconds=30, supports_dry_run=True),
        CapabilitiesOperation(method="DELETE", path="/v1/keypairs/{keypairName}", summary="Delete a keypair", async_=True, required_scopes=["keypairs:write"], estimated_duration_seconds=30, supports_dry_run=True),
        CapabilitiesOperation(method="GET", path="/v1/dns/records", summary="List DNS records", async_=False, required_scopes=["dns:read"], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/dns/records", summary="Create a DNS record", async_=True, required_scopes=["dns:write"], estimated_duration_seconds=30, supports_dry_run=True),
        CapabilitiesOperation(method="DELETE", path="/v1/dns/records/{recordName}", summary="Delete a DNS record", async_=True, required_scopes=["dns:write"], estimated_duration_seconds=30, supports_dry_run=True),
        CapabilitiesOperation(method="GET", path="/v1/s3/buckets", summary="List S3 buckets", async_=False, required_scopes=["s3:read"], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/s3/buckets", summary="Create an S3 bucket", async_=True, required_scopes=["s3:write"], estimated_duration_seconds=30, supports_dry_run=True),
        CapabilitiesOperation(method="DELETE", path="/v1/s3/buckets/{bucketName}", summary="Delete an S3 bucket", async_=True, required_scopes=["s3:write"], estimated_duration_seconds=30, supports_dry_run=True),
        CapabilitiesOperation(method="GET", path="/v1/jobs", summary="List jobs", async_=False, required_scopes=["jobs:read"], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="GET", path="/v1/jobs/{jobId}", summary="Get job status", async_=False, required_scopes=["jobs:read"], estimated_duration_seconds=1, supports_dry_run=False),
        CapabilitiesOperation(method="POST", path="/v1/jobs/{jobId}/cancel", summary="Cancel a job", async_=False, required_scopes=["jobs:cancel"], estimated_duration_seconds=1, supports_dry_run=False),
    ]
    return CapabilitiesResponse(data=CapabilitiesData(version="1.0.0", operations=ops))
