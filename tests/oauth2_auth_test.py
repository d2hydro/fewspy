# These mocked credentials are test data, never used with a live service.
# ruff: noqa: S105, S106

import base64

import pytest

from fewspy.api import Api
from fewspy.auth import BasicAuth, BearerTokenAuth, OAuth2ClientCredentialsAuth


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_oauth2_auth_caches_access_token(monkeypatch):
    calls = []

    def _fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return _Response({"access_token": "token-1", "expires_in": 3600})

    monkeypatch.setattr("fewspy.auth.requests.post", _fake_post)

    auth = OAuth2ClientCredentialsAuth(
        token_url="https://login.microsoftonline.com/example/oauth2/v2.0/token",
        client_id="client-id",
        client_secret="secret",
        scope="api://example/.default",
        cert="client.pem",
        verify=True,
        timeout=10,
    )

    token_1 = auth.get_access_token()
    token_2 = auth.get_access_token()

    assert token_1 == "token-1"
    assert token_2 == "token-1"
    assert len(calls) == 1
    assert calls[0][1]["cert"] == "client.pem"


def test_oauth2_auth_does_not_require_mtls_certificate(monkeypatch):
    calls = []

    def _fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return _Response({"access_token": "token-1", "expires_in": 3600})

    monkeypatch.setattr("fewspy.auth.requests.post", _fake_post)

    auth = OAuth2ClientCredentialsAuth(
        token_url="https://identity.example.test/token",
        client_id="client-id",
        client_secret="secret",
        scope="api://example/.default",
    )

    auth.get_access_token()

    assert calls[0][1]["cert"] is None


def test_api_keeps_token_and_fews_certificates_separate(monkeypatch):
    token_calls = []
    filters_calls = []

    def _fake_post(*args, **kwargs):
        token_calls.append((args, kwargs))
        return _Response({"access_token": "oauth-token", "expires_in": 3600})

    monkeypatch.setattr("fewspy.auth.requests.post", _fake_post)
    monkeypatch.setattr("fewspy.api.get_filters", lambda **kwargs: filters_calls.append(kwargs))

    auth = OAuth2ClientCredentialsAuth(
        token_url="https://identity.example.test/token",
        client_id="client-id",
        client_secret="secret",
        scope="api://example/.default",
        cert="token-endpoint.pem",
    )
    api = Api(
        url="https://example.test/fews",
        auth=auth,
        cert="fews-api.pem",
        validate_endpoint=False,
    )

    api.get_filters()

    assert token_calls[0][1]["cert"] == "token-endpoint.pem"
    assert filters_calls[0]["cert"] == "fews-api.pem"
    assert filters_calls[0]["http_headers"] == {"Authorization": "Bearer oauth-token"}


@pytest.mark.parametrize(
    ("auth", "expected_header"),
    [
        (BearerTokenAuth("existing-token"), "Bearer existing-token"),
        (
            BasicAuth("username", "password"),
            f"Basic {base64.b64encode(b'username:password').decode('ascii')}",
        ),
    ],
)
def test_api_supports_header_authentication_methods(monkeypatch, auth, expected_header):
    filters_calls = []
    monkeypatch.setattr("fewspy.api.get_filters", lambda **kwargs: filters_calls.append(kwargs))

    api = Api(url="https://example.test/fews", auth=auth, validate_endpoint=False)
    api.get_filters()

    assert filters_calls[0]["http_headers"] == {"Authorization": expected_header}


def test_api_can_skip_preflight_validation(monkeypatch):
    def _failing_validate_url(url, cert=None, ssl_verify=None):
        raise RuntimeError("preflight should not be called")

    monkeypatch.setattr("fewspy.api.validate_url", _failing_validate_url)

    api = Api(
        url="https://example.test/fews",
        validate_endpoint=False,
    )

    assert api.url == "https://example.test/fews/"
    assert api.ssl_verify is True
