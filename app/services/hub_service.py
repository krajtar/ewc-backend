"""Hub service — item listing, detail, and deployment."""

from typing import Any, Optional

from app.config import Settings
from app.logging import get_logger
from app.models.hub import (
    HubItemAnnotations,
    HubItemDetail,
    HubItemEwccli,
    HubItemInput,
    HubItemSource,
    HubItemSummary,
)
from app.services.exceptions import HubDeployServiceError

_logger = get_logger(__name__)


class HubService:
    """Business logic for EWC Community Hub items."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Stub catalog for Phase 4
        self._catalog: list[dict[str, Any]] = [
            {
                "name": "example-app",
                "title": "Example Application",
                "version": "1.0.0",
                "summary": "A sample EWC Community Hub application.",
                "annotations": {
                    "technology": ["Ansible Playbook"],
                    "category": [],
                    "other": ["EWCCLI-compatible"],
                },
                "ewccli": {
                    "inputs": [
                        {"name": "flavour_name", "mandatory": False, "default": "4cpu-4gbmem"},
                    ],
                    "default_image_name": "Rocky-9",
                    "default_security_groups": ["ssh"],
                    "path_to_main_file": "playbook.yml",
                    "path_to_requirements_file": "requirements.yml",
                    "external_ip": False,
                    "check_dns": True,
                },
                "sources": [{"type": "git", "url": "https://github.com/ewcloud/example-app", "ref": "main"}],
                "description": "Detailed description of the example application.",
            }
        ]

    def list_items(self, force_refresh: bool = False) -> list[HubItemSummary]:
        """List all EWCCLI-compatible hub items."""
        summaries: list[HubItemSummary] = []
        for item in self._catalog:
            ann = item.get("annotations", {})
            summaries.append(
                HubItemSummary(
                    name=item.get("name", ""),
                    title=item.get("title"),
                    version=item.get("version"),
                    summary=item.get("summary"),
                    annotations=HubItemAnnotations(
                        technology=ann.get("technology", []),
                        category=ann.get("category", []),
                        other=ann.get("other", []),
                    ),
                )
            )
        return summaries

    def show_item(self, item_name: str) -> Optional[HubItemDetail]:
        """Show detailed metadata for a specific hub item."""
        for item in self._catalog:
            if item.get("name") == item_name:
                ewc = item.get("ewccli", {})
                inputs = [HubItemInput(**inp) for inp in ewc.get("inputs", [])]
                sources = [HubItemSource(**s) for s in item.get("sources", [])]
                return HubItemDetail(
                    name=item.get("name", ""),
                    title=item.get("title"),
                    version=item.get("version"),
                    summary=item.get("summary"),
                    description=item.get("description"),
                    sources=sources,
                    ewccli=HubItemEwccli(
                        inputs=inputs,
                        default_image_name=ewc.get("default_image_name"),
                        default_security_groups=ewc.get("default_security_groups", []),
                        path_to_main_file=ewc.get("path_to_main_file"),
                        path_to_requirements_file=ewc.get("path_to_requirements_file"),
                        external_ip=ewc.get("external_ip", False),
                        check_dns=ewc.get("check_dns", False),
                    ),
                )
        return None

    def deploy_item(self, item_name: str, server_name: str, inputs: dict, profile: Optional[str] = None) -> dict:
        """Deploy a hub item. Returns deployment outputs."""
        item = self.show_item(item_name)
        if not item:
            raise HubDeployServiceError(f"Hub item '{item_name}' not found")
        _logger.info("hub_deploy", item=item_name, server=server_name, profile=profile)
        return {
            "item_name": item_name,
            "server_name": server_name,
            "ssh_command": f"ssh cloud-user@{server_name}",
            "outputs": [
                {"name": "ssh_command", "type": "text", "value": f"ssh cloud-user@{server_name}"},
            ],
        }
