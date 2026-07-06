"""S3 bucket service — management via Kubernetes CRD."""

from typing import Optional

from app.clients.interfaces import KubernetesBackendInterface
from app.logging import get_logger
from app.models.s3 import S3Bucket, S3BucketCreate
from app.services.exceptions import S3ServiceError

_logger = get_logger(__name__)

_S3_GROUP = "s3.ewcloud.host"
_S3_VERSION = "v1alpha1"
_S3_PLURAL = "objectbuckets"


class S3Service:
    """Business logic for S3 bucket management."""

    def __init__(
        self,
        k8s_backend: KubernetesBackendInterface,
        namespace: str = "default",
    ) -> None:
        self._backend = k8s_backend
        self._namespace = namespace

    def list_buckets(self) -> list[S3Bucket]:
        """List S3 buckets in the tenant namespace."""
        crds = self._backend.list_custom_resources(
            _S3_GROUP, _S3_VERSION, self._namespace, _S3_PLURAL
        )
        buckets: list[S3Bucket] = []
        for crd in crds:
            spec = crd.get("spec", {})
            buckets.append(
                S3Bucket(
                    name=crd.get("name", ""),
                    namespace=crd.get("namespace", self._namespace),
                    owner=spec.get("owner"),
                    write_access_ids=spec.get("writeAccessIds", []),
                    read_access_ids=spec.get("readAccessIds", []),
                    geo_enabled=spec.get("geoEnabled", False),
                    created_at=crd.get("created_at"),
                    status=crd.get("status"),
                )
            )
        return buckets

    def create_bucket(self, req: S3BucketCreate, dry_run: bool = False) -> dict:
        """Create an S3 bucket via Kubernetes CRD."""
        if dry_run:
            return {"dry_run": True, "bucket_name": req.bucket_name}
        crd_spec = {
            "owner": req.access_id,
            "writeAccessIds": req.write_access_ids,
            "readAccessIds": req.read_access_ids,
            "geoEnabled": req.geo_enabled,
        }
        result = self._backend.create_custom_resource(
            _S3_GROUP,
            _S3_VERSION,
            self._namespace,
            _S3_PLURAL,
            req.bucket_name,
            crd_spec,
        )
        _logger.info("s3_bucket_created", name=req.bucket_name)
        return result

    def delete_bucket(self, bucket_name: str, dry_run: bool = False) -> bool:
        """Delete an S3 bucket."""
        if dry_run:
            return True
        self._backend.delete_custom_resource(
            _S3_GROUP, _S3_VERSION, self._namespace, _S3_PLURAL, bucket_name
        )
        _logger.info("s3_bucket_deleted", name=bucket_name)
        return True
