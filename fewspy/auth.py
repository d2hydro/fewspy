"""Authentication utilities for FEWS API clients."""

import base64
import logging
import time
from typing import Protocol

import requests
from requests.auth import HTTPBasicAuth

LOGGER = logging.getLogger(__name__)


class Auth(Protocol):
    """Authentication method that supplies headers for a FEWS request."""

    def get_headers(self) -> dict[str, str]:
        """Return authentication headers for a FEWS request."""


class BearerTokenAuth:
    """Authenticate FEWS requests with an existing Bearer token."""

    def __init__(self, token: str):
        self.token = token

    def get_headers(self) -> dict[str, str]:
        """Return the Bearer Authorization header."""
        return {"Authorization": f"Bearer {self.token}"}


class BasicAuth:
    """Authenticate FEWS requests with HTTP Basic Authentication."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def get_headers(self) -> dict[str, str]:
        """Return the Basic Authorization header."""
        credentials = f"{self.username}:{self.password}".encode("latin1")
        encoded_credentials = base64.b64encode(credentials).decode("ascii")
        return {"Authorization": f"Basic {encoded_credentials}"}


class OAuth2ClientCredentialsAuth:
    """Authenticate with cached OAuth2 client-credentials access tokens."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str,
        cert: str | tuple[str, str] | None = None,
        verify: bool = True,
        timeout: int = 30,
        logger=LOGGER,
    ):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.cert = cert
        self.verify = verify
        self.timeout = timeout
        self.logger = logger

        self._access_token = None
        self._expires_at = 0.0

    def get_headers(self) -> dict[str, str]:
        """Return an Authorization header with a valid Bearer token."""
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    def get_access_token(self) -> str:
        """Get a cached token or refresh it when it is expired."""
        now = time.time()
        if (self._access_token is not None) and (now < self._expires_at):
            return self._access_token
        return self._refresh_access_token()

    def _refresh_access_token(self) -> str:
        token_data = {"grant_type": "client_credentials", "scope": self.scope}
        response = requests.post(
            self.token_url,
            data=token_data,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            cert=self.cert,
            verify=self.verify,
            timeout=self.timeout,
        )
        response.raise_for_status()
        token_json = response.json()

        access_token = token_json.get("access_token")
        if access_token is None:
            raise ValueError("No access_token in OAuth2 token response")

        expires_in = int(token_json.get("expires_in", 300))
        refresh_margin = min(60, max(5, expires_in // 10))
        self._access_token = access_token
        self._expires_at = time.time() + max(expires_in - refresh_margin, 0)
        self.logger.debug("Fetched new OAuth2 access token")
        return access_token
