"""Keypair service — OpenStack SSH keypair management."""

from typing import Optional

from app.clients.interfaces import OpenstackBackendInterface
from app.logging import get_logger
from app.models.keypair import Keypair, KeypairCreate
from app.services.exceptions import KeyPairServiceError

_logger = get_logger(__name__)


class KeypairService:
    """Business logic for OpenStack keypair management."""

    def __init__(self, openstack_backend: OpenstackBackendInterface) -> None:
        self._backend = openstack_backend

    def list_keypairs(self) -> list[Keypair]:
        """List all keypairs."""
        conn = self._backend.get_connection()
        # The stub stores keypairs internally
        if hasattr(self._backend, "_keypairs"):
            return [
                Keypair(
                    name=kp.get("name", ""),
                    fingerprint=kp.get("fingerprint"),
                    public_key=kp.get("public_key"),
                )
                for kp in self._backend._keypairs.values()
            ]
        return []

    def create_keypair(self, req: KeypairCreate, dry_run: bool = False) -> dict:
        """Create a keypair from an SSH public key."""
        if dry_run:
            return {"dry_run": True, "keypair_name": req.keypair_name}
        conn = self._backend.get_connection()
        kp, msg = self._backend.create_keypair(
            conn,
            keypair_name=req.keypair_name,
            public_key_path=req.ssh_public_key_path or "",
            public_key=req.public_key,
        )
        _logger.info("keypair_created", name=req.keypair_name)
        return {"keypair": kp, "message": msg}

    def delete_keypair(self, keypair_name: str, dry_run: bool = False) -> bool:
        """Delete a keypair by name."""
        if dry_run:
            return True
        conn = self._backend.get_connection()
        _, msg = self._backend.delete_keypair(conn, keypair_name)
        _logger.info("keypair_deleted", name=keypair_name)
        return True
