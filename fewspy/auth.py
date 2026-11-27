"""Authentication utilities for FEWS API clients."""

import base64
import logging
import os
import time
from collections.abc import Mapping
from typing import Protocol

import requests
from requests.auth import HTTPBasicAuth

LOGGER = logging.getLogger(__name__)

OAUTH2_ENV_PREFIX = "FEWSPY_OAUTH2_"


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
        verify: bool | str = True,
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


def _parse_verify(raw_value: str) -> bool | str:
    raw = raw_value.strip()
    if raw.lower() in {"true", "1", "yes", "on"}:
        return True
    if raw.lower() in {"false", "0", "no", "off"}:
        return False
    return raw


def oauth2_from_env(environ: Mapping[str, str] | None = None) -> OAuth2ClientCredentialsAuth | None:
    """Return client-credentials authentication from the ``FEWSPY_OAUTH2_*`` environment variables.

    ``FEWSPY_OAUTH2_TOKEN_URL`` switches it on. ``FEWSPY_OAUTH2_CLIENT_ID``, ``FEWSPY_OAUTH2_CLIENT_SECRET`` and
    ``FEWSPY_OAUTH2_SCOPE`` are then required; ``FEWSPY_OAUTH2_CERT``, ``FEWSPY_OAUTH2_VERIFY`` and
    ``FEWSPY_OAUTH2_TIMEOUT`` are optional. This lets an application that creates ``Api(url)`` without ``auth``
    run against a protected endpoint by configuration only.

    Args:
        environ: the variables to read. Defaults to ``os.environ``.

    Returns: the authentication, or None when ``FEWSPY_OAUTH2_TOKEN_URL`` is not set.

    """
    env = os.environ if environ is None else environ

    def get(name: str) -> str | None:
        value = env.get(f"{OAUTH2_ENV_PREFIX}{name}", "").strip()
        return value or None

    token_url = get("TOKEN_URL")
    if token_url is None:
        return None

    required = {name: get(name) for name in ("CLIENT_ID", "CLIENT_SECRET", "SCOPE")}
    missing = [f"{OAUTH2_ENV_PREFIX}{name}" for name, value in required.items() if value is None]
    if missing:
        raise ValueError(f"{OAUTH2_ENV_PREFIX}TOKEN_URL is set, but these are not: {', '.join(missing)}")

    verify = get("VERIFY")
    timeout = get("TIMEOUT")
    return OAuth2ClientCredentialsAuth(
        token_url=token_url,
        client_id=required["CLIENT_ID"],
        client_secret=required["CLIENT_SECRET"],
        scope=required["SCOPE"],
        cert=get("CERT"),
        verify=True if verify is None else _parse_verify(verify),
        timeout=30 if timeout is None else int(timeout),
    )
