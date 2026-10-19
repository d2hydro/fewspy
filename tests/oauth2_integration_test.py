import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path

import pytest

from fewspy import Api, BearerTokenAuth, OAuth2ClientCredentialsAuth

REQUIRED_ENV_KEYS_OAUTH = [
    "FEWSPY_OAUTH2_TOKEN_URL",
    "FEWSPY_OAUTH2_CLIENT_ID",
    "FEWSPY_OAUTH2_CLIENT_SECRET",
    "FEWSPY_OAUTH2_SCOPE",
]
REQUIRED_ENV_KEYS_FEWS = [
    "FEWSPY_FEWS_URL",
]
REQUIRED_ENV_KEYS_TEMP_TOKEN = [
    *REQUIRED_ENV_KEYS_FEWS,
    "FEWSPY_ACCESS_TOKEN",
]


def _load_dotenv(dotenv_path: Path) -> None:
    """Minimal .env loader for local test convenience without extra dependency."""
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(Path.cwd() / ".env.development")
_load_dotenv(Path.cwd() / ".env")

use_temp_token = os.getenv("FEWSPY_USE_TEMP_TOKEN", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
missing_temp = [k for k in REQUIRED_ENV_KEYS_TEMP_TOKEN if not os.getenv(k)]
missing_oauth = [k for k in REQUIRED_ENV_KEYS_OAUTH if not os.getenv(k)]
missing_oauth_fews = [k for k in [*REQUIRED_ENV_KEYS_OAUTH, *REQUIRED_ENV_KEYS_FEWS] if not os.getenv(k)]
pytestmark = [pytest.mark.integration]


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _parse_verify_setting(raw_value: str):
    raw = raw_value.strip()
    if raw.lower() in {"1", "true", "yes", "on"}:
        return True
    if raw.lower() in {"0", "false", "no", "off"}:
        return False
    return raw


def _assert_temp_token_claims_not_expired(access_token: str):
    """Fail fast when the temporary JWT is already expired."""
    try:
        token_parts = access_token.split(".")
        payload_b64 = token_parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")))
    except Exception as err:
        pytest.fail(f"Could not decode FEWSPY_ACCESS_TOKEN as JWT: {err}")

    exp = payload.get("exp")
    if exp is None:
        pytest.fail("FEWSPY_ACCESS_TOKEN has no 'exp' claim.")

    now = int(time.time())
    if int(exp) <= now:
        pytest.fail("FEWSPY_ACCESS_TOKEN is expired based on JWT exp claim.")


def _oauth_auth(verify):
    return OAuth2ClientCredentialsAuth(
        token_url=os.environ["FEWSPY_OAUTH2_TOKEN_URL"],
        client_id=os.environ["FEWSPY_OAUTH2_CLIENT_ID"],
        client_secret=os.environ["FEWSPY_OAUTH2_CLIENT_SECRET"],
        scope=os.environ["FEWSPY_OAUTH2_SCOPE"],
        cert=os.getenv("FEWSPY_OAUTH2_CERT"),
        verify=verify,
    )


def test_request_oauth_access_token_does_not_print_credentials(monkeypatch, capsys):
    access_token = "dummy-access-token-for-output-regression"  # noqa: S105 - Mock credential.
    for key in REQUIRED_ENV_KEYS_OAUTH:
        monkeypatch.setenv(key, "dummy-value")

    response = _Response({"access_token": access_token, "expires_in": 3600})
    monkeypatch.setattr("fewspy.auth.requests.post", lambda *args, **kwargs: response)

    assert _oauth_auth(verify=True).get_access_token() == access_token
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.integration
@pytest.mark.skipif(
    use_temp_token,
    reason="Token-request test is skipped when FEWSPY_USE_TEMP_TOKEN=true.",
)
@pytest.mark.skipif(
    bool(missing_oauth),
    reason="Missing OAuth env vars: " + ", ".join(missing_oauth),
)
def test_oauth2_can_request_access_token():
    verify = _parse_verify_setting(os.getenv("FEWSPY_OAUTH2_VERIFY", "true"))
    access_token = _oauth_auth(verify=verify).get_access_token()

    assert isinstance(access_token, str)
    assert len(access_token) > 20


@pytest.mark.integration
@pytest.mark.skipif(
    use_temp_token,
    reason="OAuth data-call test is skipped when FEWSPY_USE_TEMP_TOKEN=true.",
)
@pytest.mark.skipif(
    bool(missing_oauth_fews),
    reason="Missing OAuth or FEWS env vars: " + ", ".join(missing_oauth_fews),
)
def test_oauth2_token_can_call_fews_filters():
    oauth_verify = _parse_verify_setting(os.getenv("FEWSPY_OAUTH2_VERIFY", "true"))
    fews_verify = _parse_verify_setting(os.getenv("FEWSPY_FEWS_VERIFY", "true"))
    api = Api(
        url=os.environ["FEWSPY_FEWS_URL"],
        auth=_oauth_auth(verify=oauth_verify),
        cert=os.getenv("FEWSPY_FEWS_CERT"),
        ssl_verify=fews_verify,
        validate_endpoint=False,
    )

    assert api.get_filters()


@pytest.mark.integration
@pytest.mark.skipif(
    not use_temp_token,
    reason="Set FEWSPY_USE_TEMP_TOKEN=true to run temp-token timeseries test.",
)
@pytest.mark.skipif(
    bool(missing_temp),
    reason="Missing temp-token env vars: " + ", ".join(missing_temp),
)
def test_temp_token_can_call_fews_timeseries_with_example_params():
    verify = _parse_verify_setting(os.getenv("FEWSPY_FEWS_VERIFY", "true"))
    fews_url = os.environ["FEWSPY_FEWS_URL"]
    access_token = os.environ["FEWSPY_ACCESS_TOKEN"]
    _assert_temp_token_claims_not_expired(access_token)
    api = Api(
        url=fews_url,
        auth=BearerTokenAuth(access_token),
        cert=os.getenv("FEWSPY_FEWS_CERT"),
        ssl_verify=verify,
        validate_endpoint=False,
    )

    result = api.get_time_series(
        filter_id=None,
        parameter_ids=["Q.meting"],
        location_ids=["MPN-E-1071"],
        start_time=datetime(2025, 7, 2, 12, 44, 53),
        end_time=datetime(2025, 7, 2, 13, 44, 53),
        document_format="PI_XML",
    )

    assert not result.empty
