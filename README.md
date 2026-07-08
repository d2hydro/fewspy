# Fewspy

A Python API for the [Deltares FEWS PI REST Web Service](https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service).

Fewspy is build for speed; time-series requests are handled asynchronous, giving the results you need much faster.

[![test](https://github.com/d2hydro/fewspy/actions/workflows/test-cov.yml/badge.svg)](https://github.com/d2hydro/fewspy/actions/workflows/test-cov.yml)
[![Coverage](https://img.shields.io/codecov/c/github/d2hydro/fewspy)](https://app.codecov.io/github/d2hydro/fewspy)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Release: latest](https://img.shields.io/github/v/release/d2hydro/fewspy)](https://pypi.org/project/fewspy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
---

**Documentation**: [https://d2hydro.github.io/fewspy](https://d2hydro.github.io/fewspy)

**Source Code**: [https://github.com/d2hydro/fewspy](https://github.com/d2hydro/fewspy)

---

## Installation

Fewspy can be installed with pip in any environment with the following Python-packages properly installed:

* requests
* aiohttp
* nest-asyncio
* pandas
* geopandas

In that activated environment you can add fewspy via pip by:
```
pip install fewspy
```
We recommend to build your environment using [Anaconda](https://www.anaconda.com/). You can build an environment ánd install fewspy by conda in one go using this <a href="https://github.com/d2hydro/fewspy/blob/main/envs/environment.yml" target="_blank">environment.yml</a> from the command-line:
```
conda env create -f environment.yml
```

## Authentication

Fewspy continues to support the existing unauthenticated usage pattern. If your FEWS endpoint is protected by OAuth2 (Azure AD client credentials), you can pass an `oauth2` configuration to `Api`.

```python
from fewspy import Api

api = Api(
	url="https://fewsapi.hhnk.nl/FewsWebServices/rest/fewspiservice/v1/",
	ssl_verify=True,
	oauth2={
		"token_url": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
		"client_id": "YOUR_CLIENT_ID_HERE",
		"client_secret": "YOUR_CLIENT_SECRET_HERE",
		"scope": "api://9905a90b-de6b-4251-a721-0acc7dadcd76/.default",
		"cert": "/path/to/client_cert.pem",
	},
)

ts = api.get_time_series(
	filter_id="WDB_OW_KGM",
	parameter_ids=["Q.meting"],
	location_ids=["MPN-E-1071"],
)
```

For already-issued tokens, you can also pass `bearer_token="..."` to `Api`.

## OAuth2 integration tests (optional)

The OAuth2 unit tests run without real credentials because they mock the token endpoint.

If you want to run a real OAuth2 integration test against a FEWS endpoint:

1. Copy `.env.development.example` to `.env.development` (or place the same variables in `.env`).
2. Fill in your real values for:
	- `FEWSPY_TEST_FEWS_URL`
	- `FEWSPY_TEST_OAUTH2_TOKEN_URL`
	- `FEWSPY_TEST_OAUTH2_CLIENT_ID`
	- `FEWSPY_TEST_OAUTH2_CLIENT_SECRET`
	- `FEWSPY_TEST_OAUTH2_SCOPE`
3. Optionally set:
	- `FEWSPY_TEST_OAUTH2_CERT`
	- `FEWSPY_TEST_OAUTH2_VERIFY` (`true` or `false`)
	- `FEWSPY_TEST_USE_TEMP_TOKEN` (`true` or `false`)
	- `FEWSPY_TEST_ACCESS_TOKEN` (required when `FEWSPY_TEST_USE_TEMP_TOKEN=true`)
4. Run:

```
pixi run pytest tests/oauth2_integration_test.py -q
```

If variables are missing, this integration test is skipped automatically.

The integration tests are split into two steps:

1. token ophalen (OAuth flow)\
	prints `access_token` and `expires_in` for quick reuse during debugging;
2. data ophalen (FEWS endpoint call with bearer token).

When `FEWSPY_TEST_USE_TEMP_TOKEN=true`, OAuth token retrieval tests are skipped and the temporary bearer token is validated directly against FEWS endpoints. A clear failure is reported when the token is expired.

To run only the temporary-token timeseries test (using the example parameters):

```
pixi run pytest tests/oauth2_integration_test.py -q -k temp_token
```

## About

Fewspy is developed and maintained by [D2Hydro](https://d2hydro.nl/) and freely available under an Open Source <a href="https://github.com/d2hydro/fewspy/blob/main/LICENSE" target="_blank">MIT license</a>.
