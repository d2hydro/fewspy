import pytest

from fewspy.utils.url import URLNotFoundError, validate_url


class _Response:
    def __init__(self, status_code: int, ok: bool):
        self.status_code = status_code
        self.ok = ok


def test_validate_url_accepts_unauthorized_endpoint(monkeypatch):
    def _fake_get(*args, **kwargs):
        return _Response(status_code=401, ok=False)

    monkeypatch.setattr("fewspy.utils.url.requests.get", _fake_get)

    url, ssl_verify = validate_url("https://example.test/fews")

    assert url == "https://example.test/fews/"
    assert ssl_verify is True


def test_validate_url_accepts_forbidden_endpoint(monkeypatch):
    def _fake_get(*args, **kwargs):
        return _Response(status_code=403, ok=False)

    monkeypatch.setattr("fewspy.utils.url.requests.get", _fake_get)

    url, ssl_verify = validate_url("https://example.test/fews")

    assert url == "https://example.test/fews/"
    assert ssl_verify is True


def test_validate_url_raises_for_missing_endpoint(monkeypatch):
    def _fake_get(*args, **kwargs):
        return _Response(status_code=404, ok=False)

    monkeypatch.setattr("fewspy.utils.url.requests.get", _fake_get)

    with pytest.raises(URLNotFoundError):
        validate_url("https://example.test/fews")
