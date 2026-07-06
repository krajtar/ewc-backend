"""Service-layer exception hierarchy.

Ported from ewccli Phase 2 (KAM-7). No click/rich_click dependencies.
"""


class ServiceError(Exception):
    """Base exception for all service-layer errors."""


class ConfigServiceError(ServiceError):
    """Raised by ConfigService for configuration errors."""


class KeyPairServiceError(ServiceError):
    """Raised by KeyPairService for SSH key-pair errors."""


class DnsServiceError(ServiceError):
    """Raised by DnsService for DNS-related errors."""


class ServerServiceError(ServiceError):
    """Raised by ServerService for server-provisioning errors."""


class HubDeployServiceError(ServiceError):
    """Raised by HubDeployService for hub-deployment errors."""


class S3ServiceError(ServiceError):
    """Raised by S3Service for S3 bucket errors."""


class AuthServiceError(ServiceError):
    """Raised by AuthService for authentication errors."""
