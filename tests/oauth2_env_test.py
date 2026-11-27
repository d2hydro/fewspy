# These mocked credentials are test data, never used with a live service.
# ruff: noqa: S105, S106

import pytest

from fewspy.api import Api
from fewspy.auth import BearerTokenAuth, OAuth2ClientCredentialsAuth, oauth2_from_env

ENV = {
    "FEWSPY_OAUTH2_TOKEN_URL": "https://auth.example.test/application/o/token/",
    "FEWSPY_OAUTH2_CLIENT_ID": "client-id",
    "FEWSPY_OAUTH2_CLIENT_SECRET": "secret",
    "FEWSPY_OAUTH2_SCOPE": "openid read",
}


@pytest.fixture
def no_oauth2_env(monkeypatch):
    for name in [*ENV, "FEWSPY_OAUTH2_CERT", "FEWSPY_OAUTH2_VERIFY", "FEWSPY_OAUTH2_TIMEOUT"]:
        monkeypatch.delenv(name, raising=False)


def test_oauth2_from_env_is_off_without_a_token_url():
    assert oauth2_from_env({}) is None
    assert oauth2_from_env({"FEWSPY_OAUTH2_TOKEN_URL": "  "}) is None


def test_oauth2_from_env_builds_client_credentials_auth():
    auth = oauth2_from_env({**ENV, "FEWSPY_OAUTH2_VERIFY": "false", "FEWSPY_OAUTH2_TIMEOUT": "5"})

    assert isinstance(auth, OAuth2ClientCredentialsAuth)
    assert auth.token_url == ENV["FEWSPY_OAUTH2_TOKEN_URL"]
    assert auth.client_id == "client-id"
    assert auth.client_secret == "secret"
    assert auth.scope == "openid read"
    assert auth.cert is None
    assert auth.verify is False
    assert auth.timeout == 5


def test_oauth2_from_env_keeps_a_ca_bundle_path_as_verify():
    auth = oauth2_from_env({**ENV, "FEWSPY_OAUTH2_VERIFY": "/etc/ssl/ca.pem"})

    assert auth.verify == "/etc/ssl/ca.pem"


def test_oauth2_from_env_names_what_is_missing():
    with pytest.raises(ValueError, match="FEWSPY_OAUTH2_CLIENT_SECRET, FEWSPY_OAUTH2_SCOPE"):
        oauth2_from_env({k: v for k, v in ENV.items() if k not in {"FEWSPY_OAUTH2_CLIENT_SECRET", "FEWSPY_OAUTH2_SCOPE"}})


def test_api_without_auth_takes_oauth2_from_the_environment(monkeypatch, no_oauth2_env):
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(OAuth2ClientCredentialsAuth, "get_access_token", lambda self: "token-1")

    api = Api(url="https://example.test/fews", validate_endpoint=False)

    assert isinstance(api.auth, OAuth2ClientCredentialsAuth)
    assert api._request_headers() == {"Authorization": "Bearer token-1"}


def test_api_auth_argument_wins_over_the_environment(monkeypatch, no_oauth2_env):
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)

    api = Api(url="https://example.test/fews", auth=BearerTokenAuth("given"), validate_endpoint=False)

    assert api._request_headers() == {"Authorization": "Bearer given"}


def test_api_without_auth_or_environment_sends_no_header(no_oauth2_env):
    api = Api(url="https://example.test/fews", validate_endpoint=False)

    assert api.auth is None
    assert api._request_headers() is None
