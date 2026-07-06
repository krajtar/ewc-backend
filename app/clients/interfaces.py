"""Backend client interface protocols.

Defines ``typing.Protocol`` interfaces for each backend client so that
services depend on the *contract* rather than the concrete implementation.
This enables dependency injection and mock-based unit testing without
importing heavy SDK dependencies.

Ported from ewccli Phase 3 (KAM-8) backend interfaces.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class BackendInterface(Protocol):
    """Common contract for all backend clients."""

    def connect(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def close(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...


@runtime_checkable
class OpenstackBackendInterface(BackendInterface, Protocol):
    """Contract for the OpenStack backend client."""

    def get_connection(self, **kwargs: Any) -> Any:
        ...

    def create_server(
        self, conn: Any, server_name: str, **kwargs: Any
    ) -> Tuple[Any, Optional[str], Dict[Any, Any]]:
        ...

    def delete_server(self, conn: Any, server_name: str, **kwargs: Any) -> Any:
        ...

    def list_servers(self, conn: Any, **kwargs: Any) -> List[Any]:
        ...

    def find_latest_image(self, conn: Any, prefix: str) -> Any:
        ...

    def check_server_inputs(self, conn: Any, **kwargs: Any) -> Any:
        ...

    def add_external_ip(self, conn: Any, **kwargs: Any) -> Any:
        ...

    def remove_external_ip(self, conn: Any, **kwargs: Any) -> Any:
        ...

    def list_networks(self, conn: Any, **kwargs: Any) -> List[Any]:
        ...

    def create_keypair(
        self, conn: Any, keypair_name: str, public_key_path: Any, **kwargs: Any
    ) -> Tuple[Any, str]:
        ...

    def delete_keypair(self, conn: Any, keypair_name: str, **kwargs: Any) -> Tuple[Any, str]:
        ...

    def ssh_key_matches_openstack(self, public_key_path: str, keypair: dict) -> bool:
        ...


@runtime_checkable
class KubernetesBackendInterface(BackendInterface, Protocol):
    """Contract for the Kubernetes backend client."""

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
        ...

    def delete_custom_resource(
        self, group: str, version: str, namespace: str, plural: str, name: str
    ) -> dict:
        ...

    def describe_custom_resource(
        self, group: str, version: str, namespace: str, plural: str, name: str
    ) -> dict:
        ...

    def list_custom_resources(
        self, group: str, version: str, namespace: str, plural: str, **kwargs: Any
    ) -> List[dict]:
        ...

    def list_pods(self, namespace: str) -> List[dict]:
        ...

    def list_custom_resource_definitions(self) -> List[dict]:
        ...


@runtime_checkable
class AnsibleBackendInterface(BackendInterface, Protocol):
    """Contract for the Ansible backend client."""

    def run_ansible_live(
        self, working_directory_path: str, cmdline: List[str], **kwargs: Any
    ) -> Any:
        ...

    def run_ansible(self, **kwargs: Any) -> Any:
        ...

    def install_ansible_roles(self, requirements_path: str, dry_run: bool = False) -> None:
        ...
