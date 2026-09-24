import base64
import json
import os
import time
from pathlib import Path

import pytest
import requests
from requests.auth import HTTPBasicAuth

REQUIRED_ENV_KEYS_OAUTH = [
    "FEWSPY_TEST_FEWS_URL",
    "FEWSPY_TEST_OAUTH2_TOKEN_URL",
    "FEWSPY_TEST_OAUTH2_CLIENT_ID",
    "FEWSPY_TEST_OAUTH2_CLIENT_SECRET",
    "FEWSPY_TEST_OAUTH2_SCOPE",
]
REQUIRED_ENV_KEYS_TEMP_TOKEN = [
    "FEWSPY_TEST_FEWS_URL",
    "FEWSPY_TEST_ACCESS_TOKEN",
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

use_temp_token = os.getenv("FEWSPY_TEST_USE_TEMP_TOKEN", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
missing_temp = [k for k in REQUIRED_ENV_KEYS_TEMP_TOKEN if not os.getenv(k)]
missing_oauth = [k for k in REQUIRED_ENV_KEYS_OAUTH if not os.getenv(k)]
pytestmark = [pytest.mark.integration]


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
        pytest.fail(f"Could not decode FEWSPY_TEST_ACCESS_TOKEN as JWT: {err}")

    exp = payload.get("exp")
    if exp is None:
        pytest.fail("FEWSPY_TEST_ACCESS_TOKEN has no 'exp' claim.")

    now = int(time.time())
    if int(exp) <= now:
        pytest.fail("FEWSPY_TEST_ACCESS_TOKEN is expired based on JWT exp claim.")


def _assert_filters_request_with_token(fews_url: str, access_token: str, verify):
    filters_url = f"{fews_url.rstrip('/')}/filters"
    response = requests.get(
        filters_url,
        headers={"Authorization": f"Bearer {access_token}"},
        verify=verify,
        timeout=30,
    )

    _assert_not_expired_jwt(response)

    response.raise_for_status()
    payload = response.json()
    assert isinstance(payload, dict)
    assert "filters" in payload


def _assert_not_expired_jwt(response):
    if (response.status_code == 401) and ("Expired JWT" in response.text):
        pytest.fail("Provided FEWSPY_TEST_ACCESS_TOKEN is expired (Expired JWT).")


def _request_oauth_access_token(verify):
    token_url = os.environ["FEWSPY_TEST_OAUTH2_TOKEN_URL"]
    token_data = {
        "grant_type": "client_credentials",
        "scope": os.environ["FEWSPY_TEST_OAUTH2_SCOPE"],
    }
    response = requests.post(
        token_url,
        data=token_data,
        auth=HTTPBasicAuth(
            os.environ["FEWSPY_TEST_OAUTH2_CLIENT_ID"],
            os.environ["FEWSPY_TEST_OAUTH2_CLIENT_SECRET"],
        ),
        cert=os.getenv("FEWSPY_TEST_OAUTH2_CERT"),
        verify=verify,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload["access_token"]
    expires_in = int(payload.get("expires_in", 0))

    print("Access token received successfully")
    print("Access token expires_in (seconds):", expires_in)

    return access_token, expires_in


@pytest.mark.integration
@pytest.mark.skipif(
    use_temp_token,
    reason="Token-request test is skipped when FEWSPY_TEST_USE_TEMP_TOKEN=true.",
)
@pytest.mark.skipif(
    bool(missing_oauth),
    reason="Missing OAuth env vars: " + ", ".join(missing_oauth),
)
def test_oauth2_can_request_access_token():
    verify = _parse_verify_setting(os.getenv("FEWSPY_TEST_OAUTH2_VERIFY", "true"))
    access_token, expires_in = _request_oauth_access_token(verify=verify)

    assert isinstance(access_token, str)
    assert len(access_token) > 20
    assert expires_in > 0


@pytest.mark.integration
@pytest.mark.skipif(
    use_temp_token,
    reason="OAuth data-call test is skipped when FEWSPY_TEST_USE_TEMP_TOKEN=true.",
)
@pytest.mark.skipif(
    bool(missing_oauth),
    reason="Missing OAuth env vars: " + ", ".join(missing_oauth),
)
def test_oauth2_token_can_call_fews_filters():
    verify = _parse_verify_setting(os.getenv("FEWSPY_TEST_OAUTH2_VERIFY", "true"))
    fews_url = os.environ["FEWSPY_TEST_FEWS_URL"]
    access_token, _ = _request_oauth_access_token(verify=verify)

    _assert_filters_request_with_token(
        fews_url=fews_url,
        access_token=access_token,
        verify=verify,
    )


@pytest.mark.integration
@pytest.mark.skipif(
    not use_temp_token,
    reason="Set FEWSPY_TEST_USE_TEMP_TOKEN=true to run temp-token timeseries test.",
)
@pytest.mark.skipif(
    bool(missing_temp),
    reason="Missing temp-token env vars: " + ", ".join(missing_temp),
)
def test_temp_token_can_call_fews_timeseries_with_example_params():
    verify = _parse_verify_setting(os.getenv("FEWSPY_TEST_OAUTH2_VERIFY", "true"))
    fews_url = os.environ["FEWSPY_TEST_FEWS_URL"]
    access_token = os.environ["FEWSPY_TEST_ACCESS_TOKEN"]
    _assert_temp_token_claims_not_expired(access_token)
    cert = os.getenv("FEWSPY_TEST_OAUTH2_CERT")

    params = {
        "documentFormat": "PI_XML",
        "documentVersion": "1.34",
        "parameterIds": "Q.meting",
        "locationIds": "MPN-E-1071",
        "startTime": "2025-07-02T12:44:53Z",
        "endTime": "2025-07-02T13:44:53Z",
        "convertDatum": "true",
    }

    timeseries_url = f"{fews_url.rstrip('/')}/timeseries/"
    response = requests.get(
        timeseries_url,
        params=params,
        headers={"Authorization": f"Bearer {access_token}"},
        cert=cert or None,
        verify=verify,
        timeout=60,
    )

    _assert_not_expired_jwt(response)
    response.raise_for_status()
    assert response.content
