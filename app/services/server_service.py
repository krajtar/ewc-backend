"""Server service — provisioning, listing, deletion, reconfiguration."""

from datetime import datetime, timezone
from typing import Any, Optional

from app.clients.interfaces import OpenstackBackendInterface
from app.logging import get_logger
from app.models.server import (
    ServerConflict,
    ServerConflictDiff,
    ServerDetail,
    ServerNetwork,
    ServerSummary,
)
from app.services.exceptions import ServerServiceError

_logger = get_logger(__name__)


class ServerService:
    """Business logic for OpenStack VM lifecycle."""

    def __init__(self, openstack_backend: OpenstackBackendInterface) -> None:
        self._backend = openstack_backend

    def list_servers(self, show_all: bool = False) -> list[ServerSummary]:
        """List servers, optionally filtered to ewccli-created ones."""
        conn = self._backend.get_connection()
        servers = self._backend.list_servers(conn, show_all=show_all)
        summaries: list[ServerSummary] = []
        for srv in servers:
            if isinstance(srv, dict):
                addresses = srv.get("addresses", {})
                net_str = ", ".join(
                    f"{net}({', '.join(a.get('addr', '') for a in addrs if isinstance(a, dict))})"
                    for net, addrs in addresses.items()
                ) if addresses else None
                summaries.append(
                    ServerSummary(
                        name=srv.get("name", ""),
                        status=srv.get("status"),
                        networks=net_str,
                        flavor=srv.get("flavor", {}).get("original_name") if isinstance(srv.get("flavor"), dict) else None,
                        id=srv.get("id"),
                    )
                )
            else:
                summaries.append(ServerSummary(name=str(srv)))
        return summaries

    def show_server(self, server_name: str) -> Optional[ServerDetail]:
        """Show detailed info for a single server."""
        conn = self._backend.get_connection()
        servers = self._backend.list_servers(conn, show_all=True)
        for srv in servers:
            name = srv.get("name") if isinstance(srv, dict) else str(srv)
            if name == server_name:
                return self._to_detail(srv)
        return None

    def _to_detail(self, srv: Any) -> ServerDetail:
        if not isinstance(srv, dict):
            return ServerDetail(name=str(srv))
        addresses = srv.get("addresses", {})
        networks = []
        for net_name, addrs in addresses.items():
            ips = [a.get("addr", "") for a in addrs if isinstance(a, dict)]
            networks.append(ServerNetwork(network=net_name, addresses=ips))
        sgs = [sg.get("name", "") for sg in srv.get("security_groups", []) if isinstance(sg, dict)]
        return ServerDetail(
            name=srv.get("name", ""),
            id=srv.get("id"),
            status=srv.get("status"),
            flavor=srv.get("flavor", {}).get("original_name") if isinstance(srv.get("flavor"), dict) else None,
            image=srv.get("image"),
            networks=networks,
            security_groups=sgs,
            keypair=srv.get("key_name"),
            internal_ip=srv.get("internal_ip"),
            external_ip=srv.get("external_ip"),
            created_at=srv.get("created_at"),
        )

    def check_conflict(
        self, server_name: str, server_inputs: dict, existing: Any
    ) -> Optional[ServerConflict]:
        """Check if creation inputs conflict with an existing server."""
        if not existing:
            return None
        diffs: list[ServerConflictDiff] = []
        if isinstance(existing, dict):
            if server_inputs.get("image_name") and existing.get("image"):
                if str(existing.get("image")) != str(server_inputs["image_name"]):
                    diffs.append(ServerConflictDiff(field="Image", current=str(existing.get("image")), requested=server_inputs["image_name"]))
            if server_inputs.get("keypair_name") and existing.get("key_name"):
                if str(existing.get("key_name")) != str(server_inputs["keypair_name"]):
                    diffs.append(ServerConflictDiff(field="Keypair", current=str(existing.get("key_name")), requested=server_inputs["keypair_name"]))
        if diffs:
            return ServerConflict(server_name=server_name, diffs=diffs)
        return None

    def create_server(self, server_inputs: dict, dry_run: bool = False, force: bool = False) -> dict:
        """Execute server creation. Returns outputs dict."""
        conn = self._backend.get_connection()
        server_name = server_inputs.get("server_name", "")
        if dry_run:
            return {"dry_run": True, "server_name": server_name}
        _, _, outputs = self._backend.create_server(
            conn,
            server_name=server_name,
            image_name=server_inputs.get("image_name"),
            flavour_name=server_inputs.get("flavour_name"),
            networks=server_inputs.get("networks", []),
            security_groups=server_inputs.get("security_groups", ["ssh"]),
            keypair_name=server_inputs.get("keypair_name"),
        )
        return outputs

    def delete_server(self, server_name: str, force: bool = False, dry_run: bool = False) -> bool:
        """Delete a server by name."""
        if dry_run:
            return True
        conn = self._backend.get_connection()
        self._backend.delete_server(conn, server_name, force=force)
        return True
