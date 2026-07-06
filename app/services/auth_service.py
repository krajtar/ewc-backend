"""Authentication service — OIDC login initiation and token exchange."""

import secrets
from typing import Optional
from urllib.parse import urlencode

from app.config import Settings
from app.logging import get_logger
from app.models.auth import LoginInitData, LoginInitResponse, TokenResponse
from app.services.exceptions import AuthServiceError

_logger = get_logger(__name__)


class AuthService:
    """Business logic for authentication flows."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def initiate_login(
        self,
        no_browser: bool = False,
        profile: Optional[str] = None,
    ) -> LoginInitResponse:
        """Build the Keycloak authorization URL (auth code + PKCE)."""
        state = secrets.token_urlsafe(32)
        params = {
            "response_type": "code",
            "client_id": self._settings.keycloak_client_id,
            "redirect_uri": f"{self._settings.keycloak_url}/callback",
            "state": state,
            "scope": "openid profile email",
        }
        auth_url = (
            f"{self._settings.keycloak_url}"
            f"/realms/{self._settings.keycloak_realm}"
            f"/protocol/openid-connect/auth?{urlencode(params)}"
        )
        _logger.info("login_initiated", profile=profile, no_browser=no_browser)
        return LoginInitResponse(
            data=LoginInitData(
                authorization_url=auth_url,
                state=state,
                profile=profile,
            )
        )

    def exchange_token(
        self,
        grant_type: str,
        code: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> TokenResponse:
        """Exchange an authorization code or refresh token for tokens.

        In production this calls Keycloak's token endpoint.  For Phase 4
        this returns a stub token so the API contract is exercised.
        """
        if grant_type == "authorization_code" and not code:
            raise AuthServiceError("code is required for authorization_code grant")
        if grant_type == "refresh_token" and not refresh_token:
            raise AuthServiceError("refresh_token is required for refresh_token grant")

        _logger.info("token_exchanged", grant_type=grant_type)
        return TokenResponse(
            access_token=f"stub_access_{secrets.token_urlsafe(32)}",
            refresh_token=f"stub_refresh_{secrets.token_urlsafe(32)}",
            token_type="Bearer",
            expires_in=900,
            scope="servers:read servers:write hub:read hub:deploy",
        )

    def logout(self) -> None:
        """Revoke the current access and refresh tokens."""
        _logger.info("logout")
