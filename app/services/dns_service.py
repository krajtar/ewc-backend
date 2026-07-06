"""DNS service — record management via Kubernetes CRD."""

from typing import Optional

from app.clients.interfaces import KubernetesBackendInterface
from app.logging import get_logger
from app.models.dns import DnsRecord, DnsRecordCreate
from app.services.exceptions import DnsServiceError

_logger = get_logger(__name__)

_DNS_GROUP = "dns.ewcloud.host"
_DNS_VERSION = "v1alpha1"
_DNS_PLURAL = "dnsrecords"


class DnsService:
    """Business logic for DNS record management."""

    def __init__(
        self,
        k8s_backend: KubernetesBackendInterface,
        namespace: str = "default",
    ) -> None:
        self._backend = k8s_backend
        self._namespace = namespace

    def list_records(self) -> list[DnsRecord]:
        """List DNS records in the tenant namespace."""
        crds = self._backend.list_custom_resources(
            _DNS_GROUP, _DNS_VERSION, self._namespace, _DNS_PLURAL
        )
        records: list[DnsRecord] = []
        for crd in crds:
            spec = crd.get("spec", {})
            records.append(
                DnsRecord(
                    name=crd.get("name", ""),
                    type=spec.get("type", "A"),
                    rdata=spec.get("rdata", ""),
                    namespace=crd.get("namespace", self._namespace),
                    owner=spec.get("owner"),
                    write_access_ids=spec.get("writeAccessIds", []),
                    read_access_ids=spec.get("readAccessIds", []),
                    geo_enabled=spec.get("geoEnabled", False),
                    created_at=crd.get("created_at"),
                    status=crd.get("status"),
                )
            )
        return records

    def show_record(self, record_name: str) -> Optional[DnsRecord]:
        """Show details for a specific DNS record."""
        crd = self._backend.describe_custom_resource(
            _DNS_GROUP, _DNS_VERSION, self._namespace, _DNS_PLURAL, record_name
        )
        if not crd:
            return None
        spec = crd.get("spec", {})
        return DnsRecord(
            name=crd.get("name", ""),
            type=spec.get("type", "A"),
            rdata=spec.get("rdata", ""),
            namespace=crd.get("namespace", self._namespace),
            owner=spec.get("owner"),
            write_access_ids=spec.get("writeAccessIds", []),
            read_access_ids=spec.get("readAccessIds", []),
            geo_enabled=spec.get("geoEnabled", False),
            created_at=crd.get("created_at"),
            status=crd.get("status"),
        )

    def create_record(self, req: DnsRecordCreate, dry_run: bool = False) -> dict:
        """Create a DNS record via Kubernetes CRD."""
        if dry_run:
            return {"dry_run": True, "record_name": req.record_name}
        crd_spec = {
            "type": req.record_type,
            "rdata": req.rdata,
            "owner": req.access_id,
            "writeAccessIds": req.write_access_ids,
            "readAccessIds": req.read_access_ids,
            "geoEnabled": req.geo_enabled,
        }
        result = self._backend.create_custom_resource(
            _DNS_GROUP,
            _DNS_VERSION,
            self._namespace,
            _DNS_PLURAL,
            req.record_name,
            crd_spec,
        )
        _logger.info("dns_record_created", name=req.record_name)
        return result

    def delete_record(self, record_name: str, dry_run: bool = False) -> bool:
        """Delete a DNS record."""
        if dry_run:
            return True
        self._backend.delete_custom_resource(
            _DNS_GROUP, _DNS_VERSION, self._namespace, _DNS_PLURAL, record_name
        )
        _logger.info("dns_record_deleted", name=record_name)
        return True
