import pytest

from fewspy.api import Api
from fewspy.auth import OAuth2ClientCredentialsTokenProvider


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_oauth2_provider_caches_access_token(monkeypatch):
    calls = []

    def _fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return _Response({"access_token": "token-1", "expires_in": 3600})

    monkeypatch.setattr("fewspy.auth.requests.post", _fake_post)

    provider = OAuth2ClientCredentialsTokenProvider(
        token_url="https://login.microsoftonline.com/example/oauth2/v2.0/token",
        client_id="client-id",
        client_secret="secret",
        scope="api://example/.default",
        cert="/tmp/client.pem",
        verify=True,
        timeout=10,
    )

    token_1 = provider.get_access_token()
    token_2 = provider.get_access_token()

    assert token_1 == "token-1"
    assert token_2 == "token-1"
    assert len(calls) == 1
    assert calls[0][1]["cert"] == "/tmp/client.pem"


def test_api_oauth2_adds_bearer_header(monkeypatch):
    token_calls = []
    filters_calls = []

    def _fake_validate_url(url, cert=None):
        if not url.endswith("/"):
            url = f"{url}/"
        return url, False

    def _fake_post(*args, **kwargs):
        token_calls.append((args, kwargs))
        return _Response({"access_token": "oauth-token", "expires_in": 3600})

    def _fake_get_filters(**kwargs):
        filters_calls.append(kwargs)
        return []

    monkeypatch.setattr("fewspy.api.validate_url", _fake_validate_url)
    monkeypatch.setattr("fewspy.auth.requests.post", _fake_post)
    monkeypatch.setattr("fewspy.api.get_filters", _fake_get_filters)

    api = Api(
        url="https://example.test/fews",
        ssl_verify=False,
        oauth2={
            "token_url": "https://login.microsoftonline.com/example/oauth2/v2.0/token",
            "client_id": "client-id",
            "client_secret": "secret",
            "scope": "api://example/.default",
            "cert": "/tmp/client.pem",
        },
    )

    api.get_filters()
    api.get_filters()

    assert len(token_calls) == 1
    assert len(filters_calls) == 2
    assert filters_calls[0]["cert"] == "/tmp/client.pem"
    assert filters_calls[0]["http_headers"]["Authorization"] == "Bearer oauth-token"
    assert filters_calls[1]["http_headers"]["Authorization"] == "Bearer oauth-token"


def test_api_rejects_multiple_auth_methods(monkeypatch):
    def _fake_validate_url(url, cert=None):
        if not url.endswith("/"):
            url = f"{url}/"
        return url, False

    monkeypatch.setattr("fewspy.api.validate_url", _fake_validate_url)

    with pytest.raises(ValueError):
        Api(
            url="https://example.test/fews",
            bearer_token="token",
            oauth2={
                "token_url": "https://login.microsoftonline.com/example/oauth2/v2.0/token",
                "client_id": "client-id",
                "client_secret": "secret",
                "scope": "api://example/.default",
            },
        )


def test_api_can_skip_preflight_validation(monkeypatch):
    def _failing_validate_url(url, cert=None):
        raise RuntimeError("preflight should not be called")

    monkeypatch.setattr("fewspy.api.validate_url", _failing_validate_url)

    api = Api(
        url="https://example.test/fews",
        validate_endpoint=False,
    )

    assert api.url == "https://example.test/fews/"
    assert api.ssl_verify is True
