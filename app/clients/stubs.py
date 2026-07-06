"""Stub backend client implementations.

These stubs return realistic data shapes so the API layer can be
developed and tested without real OpenStack/K8s/Ansible infrastructure.
They implement the Protocol interfaces from ``app.clients.interfaces``.

Phase 5+ will replace these with real SDK-backed implementations.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.clients.interfaces import (
    AnsibleBackendInterface,
    KubernetesBackendInterface,
    OpenstackBackendInterface,
)
from app.logging import get_logger

_logger = get_logger(__name__)


class StubOpenstackBackend:
    """In-memory stub for the OpenStack backend client."""

    def __init__(self) -> None:
        self._connected = False
        self._servers: Dict[str, dict] = {}
        self._keypairs: Dict[str, dict] = {}

    def connect(self, *args: Any, **kwargs: Any) -> Any:
        self._connected = True
        _logger.info("stub_openstack.connect")
        return self

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_connection(self, **kwargs: Any) -> Any:
        if not self._connected:
            self.connect()
        return self

    def create_server(
        self, conn: Any, server_name: str, **kwargs: Any
    ) -> Tuple[Any, Optional[str], Dict[Any, Any]]:
        server = {
            "name": server_name,
            "id": str(uuid.uuid4()),
            "status": "ACTIVE",
            "flavor": {"original_name": kwargs.get("flavour_name", "4cpu-4gbmem")},
            "image": kwargs.get("image_name", "Rocky-9"),
            "addresses": {"private": [{"addr": "10.0.0.10"}]},
            "security_groups": [{"name": sg} for sg in kwargs.get("security_groups", ["ssh"])],
            "key_name": kwargs.get("keypair_name"),
            "created_at": datetime.now(timezone.utc),
        }
        self._servers[server_name] = server
        outputs: Dict[Any, Any] = {
            "internal_ip_machine": "10.0.0.10",
            "external_ip_machine": None,
            "server_info": server,
        }
        return server, None, outputs

    def delete_server(self, conn: Any, server_name: str, **kwargs: Any) -> Any:
        self._servers.pop(server_name, None)
        return True

    def list_servers(self, conn: Any, **kwargs: Any) -> List[Any]:
        show_all = kwargs.get("show_all", False)
        if show_all:
            return list(self._servers.values())
        return [s for s in self._servers.values()]

    def find_latest_image(self, conn: Any, prefix: str) -> Any:
        return {"name": f"{prefix}-latest", "id": str(uuid.uuid4())}

    def check_server_inputs(self, conn: Any, **kwargs: Any) -> Any:
        return True

    def add_external_ip(self, conn: Any, **kwargs: Any) -> Any:
        server = kwargs.get("server")
        if server and "name" in server:
            if server["name"] in self._servers:
                self._servers[server["name"]]["external_ip"] = "192.0.2.10"
        return (True, "Floating IP assigned", {})

    def remove_external_ip(self, conn: Any, **kwargs: Any) -> Any:
        return True

    def list_networks(self, conn: Any, **kwargs: Any) -> List[Any]:
        return [{"name": "private", "id": str(uuid.uuid4())}]

    def create_keypair(
        self, conn: Any, keypair_name: str, public_key_path: Any, **kwargs: Any
    ) -> Tuple[Any, str]:
        self._keypairs[keypair_name] = {
            "name": keypair_name,
            "fingerprint": "aa:bb:cc:dd:ee:ff",
            "public_key": kwargs.get("public_key", "ssh-rsa AAAA..."),
        }
        return self._keypairs[keypair_name], "Keypair created"

    def delete_keypair(self, conn: Any, keypair_name: str, **kwargs: Any) -> Tuple[Any, str]:
        self._keypairs.pop(keypair_name, None)
        return True, "Keypair deleted"

    def ssh_key_matches_openstack(self, public_key_path: str, keypair: dict) -> bool:
        return True


class StubKubernetesBackend:
    """In-memory stub for the Kubernetes backend client."""

    def __init__(self) -> None:
        self._connected = False
        self._crds: Dict[str, dict] = {}

    def connect(self, *args: Any, **kwargs: Any) -> Any:
        self._connected = True
        return self

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def create_custom_resource(
        self,
        group: str,
        version: str,
        namespace: str,
        plural: str,
        name: str,
        crd: Any,
        **kwargs: Any,
    ) -> dict:
        key = f"{namespace}/{plural}/{name}"
        self._crds[key] = {
            "name": name,
            "namespace": namespace,
            "spec": crd if isinstance(crd, dict) else {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return self._crds[key]

    def delete_custom_resource(
        self, group: str, version: str, namespace: str, plural: str, name: str
    ) -> dict:
        key = f"{namespace}/{plural}/{name}"
        self._crds.pop(key, None)
        return {"deleted": True}

    def describe_custom_resource(
        self, group: str, version: str, namespace: str, plural: str, name: str
    ) -> dict:
        key = f"{namespace}/{plural}/{name}"
        return self._crds.get(key, {})

    def list_custom_resources(
        self, group: str, version: str, namespace: str, plural: str, **kwargs: Any
    ) -> List[dict]:
        prefix = f"{namespace}/{plural}/"
        return [v for k, v in self._crds.items() if k.startswith(prefix)]

    def list_pods(self, namespace: str) -> List[dict]:
        return [{"name": "stub-pod", "namespace": namespace, "status": "Running"}]

    def list_custom_resource_definitions(self) -> List[dict]:
        return [{"name": "dnsrecords.dns.ewcloud.host"}, {"name": "objectbuckets.s3.ewcloud.host"}]


class StubAnsibleBackend:
    """In-memory stub for the Ansible backend client."""

    def __init__(self) -> None:
        self._connected = False

    def connect(self, *args: Any, **kwargs: Any) -> Any:
        self._connected = True
        return self

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def run_ansible_live(
        self, working_directory_path: str, cmdline: List[str], **kwargs: Any
    ) -> Any:
        _logger.info("stub_ansible.run_live", cwd=working_directory_path, cmdline=cmdline)
        return {"rc": 0, "stdout": "PLAY RECAP: ok=1 changed=0 unreachable=0 failed=0"}

    def run_ansible(self, **kwargs: Any) -> Any:
        _logger.info("stub_ansible.run")
        return {"rc": 0, "stdout": "ok"}

    def install_ansible_roles(self, requirements_path: str, dry_run: bool = False) -> None:
        _logger.info("stub_ansible.install_roles", path=requirements_path, dry_run=dry_run)
