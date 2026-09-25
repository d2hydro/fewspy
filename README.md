# Fewspy

A Python API for the [Deltares FEWS PI REST Web Service](https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service).

Fewspy is build for speed; time-series requests are handled asynchronous, giving the results you need much faster.

[![test](https://github.com/d2hydro/fewspy/actions/workflows/test-cov.yml/badge.svg)](https://github.com/d2hydro/fewspy/actions/workflows/test-cov.yml)
[![Coverage](https://img.shields.io/codecov/c/github/d2hydro/fewspy)](https://app.codecov.io/github/d2hydro/fewspy)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-Ruff-D7FF64)](https://docs.astral.sh/ruff/)
[![Release: latest](https://img.shields.io/github/v/release/d2hydro/fewspy)](https://pypi.org/project/fewspy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
---

**Documentation**: [https://d2hydro.github.io/fewspy](https://d2hydro.github.io/fewspy)

**Source Code**: [https://github.com/d2hydro/fewspy](https://github.com/d2hydro/fewspy)

---

## Installation

Fewspy supports Python 3.10–3.14.

Install Fewspy in your Python environment:

```console
python -m pip install fewspy
```

## Authentication

Fewspy continues to support unauthenticated FEWS endpoints. For an endpoint protected by OpenID Connect/OAuth2, create an authentication object and pass it to `Api`:

```python
from fewspy import Api, OAuth2ClientCredentialsAuth

auth = OAuth2ClientCredentialsAuth(
	token_url="https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
	client_id="YOUR_CLIENT_ID_HERE",
	client_secret="YOUR_CLIENT_SECRET_HERE",
	scope="api://<application-id>/.default",
)

api = Api(
	url="https://<mijn.domein.nl>/FewsWebServices/rest/fewspiservice/v1/",
	auth=auth,
	ssl_verify=True,
)

ts = api.get_time_series(
	filter_id="WDB_OW_KGM",
	parameter_ids=["Q.meting"],
	location_ids=["MPN-E-1071"],
)
```

The optional certificate on `OAuth2ClientCredentialsAuth` is used only if the token endpoint requires mTLS. Microsoft Entra client credentials with a client secret normally do not require it. The certificate on `Api` is used only for FEWS requests. OAuth2 access tokens are cached and refreshed before they expire.

For other authentication methods, use `BearerTokenAuth(token)` or `BasicAuth(username, password)`. Custom authentication methods can implement `get_headers() -> dict[str, str]`; wrappers receive only those headers and the FEWS client certificate.

## OAuth2 integration tests (optional)

The OAuth2 unit tests run without real credentials because they mock the token endpoint.

If you want to run a real OAuth2 integration test against a FEWS endpoint:

1. Copy `.env.development.example` to `.env.development` (or place the same variables in `.env`).
2. Fill in your real values for:
	- `FEWSPY_FEWS_URL`
	- `FEWSPY_OAUTH2_TOKEN_URL`
	- `FEWSPY_OAUTH2_CLIENT_ID`
	- `FEWSPY_OAUTH2_CLIENT_SECRET`
	- `FEWSPY_OAUTH2_SCOPE`
3. Optionally set:
	- `FEWSPY_FEWS_CERT` (only for a FEWS deployment that explicitly requires mTLS)
	- `FEWSPY_FEWS_VERIFY` (`true`, `false`, or a CA bundle path)
	- `FEWSPY_OAUTH2_CERT` (only for a token endpoint that explicitly requires mTLS)
	- `FEWSPY_OAUTH2_VERIFY` (`true`, `false`, or a CA bundle path)
	- `FEWSPY_USE_TEMP_TOKEN` (`true` or `false`)
	- `FEWSPY_ACCESS_TOKEN` (required when `FEWSPY_USE_TEMP_TOKEN=true`)
4. Run:

```
pixi run pytest tests/oauth2_integration_test.py -q
```

If variables are missing, this integration test is skipped automatically.

The integration tests are split into two steps:

1. token ophalen (OAuth flow) without logging the access token;
2. data ophalen (FEWS endpoint call with bearer token).

When `FEWSPY_USE_TEMP_TOKEN=true`, OAuth token retrieval tests are skipped and the temporary bearer token is validated directly against FEWS endpoints. A clear failure is reported when the token is expired.

To run only the temporary-token timeseries test (using the example parameters):

```
pixi run pytest tests/oauth2_integration_test.py -q -k temp_token
```
Pip installs all required dependencies automatically.

## About

Fewspy is developed and maintained by [D2Hydro](https://d2hydro.nl/) and freely available under an Open Source <a href="https://github.com/d2hydro/fewspy/blob/main/LICENSE" target="_blank">MIT license</a>.
