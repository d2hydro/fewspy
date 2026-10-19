# %% [markdown]
# # FEWS OAuth2 vanuit .env
# 
# Dit notebook laadt variabelen uit `.env` (en daarna `.env.development` als fallback).
# 
# Benodigde variabelen in je `.env`:
# - `FEWSPY_FEWS_URL`
# - `FEWSPY_OAUTH2_TOKEN_URL`
# - `FEWSPY_OAUTH2_CLIENT_ID`
# - `FEWSPY_OAUTH2_CLIENT_SECRET`
# - `FEWSPY_OAUTH2_SCOPE`
# 
# Optioneel:
# - `FEWSPY_FEWS_CERT` (alleen als de FEWS-deployment expliciet mTLS vereist)
# - `FEWSPY_FEWS_VERIFY` (`true`/`false` of pad naar CA bundle)
# - `FEWSPY_OAUTH2_CERT` (alleen als het token-endpoint expliciet mTLS vereist)
# - `FEWSPY_OAUTH2_VERIFY` (`true`/`false` of pad naar CA bundle)
# - `FEWSPY_USE_TEMP_TOKEN` (`true`/`false`)
# - `FEWSPY_ACCESS_TOKEN` (alleen nodig als `FEWSPY_USE_TEMP_TOKEN=true`)

# %%
import os
from datetime import datetime
from pathlib import Path

from fewspy import Api, BearerTokenAuth, OAuth2ClientCredentialsAuth


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if (not line) or line.startswith("#") or ("=" not in line):
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_verify_setting(raw_value: str) -> bool | str:
    raw = raw_value.strip()
    if raw.lower() in {"true", "1", "yes", "on"}:
        return True
    if raw.lower() in {"false", "0", "no", "off"}:
        return False
    return raw


# Omgevingsvariabelen laden vanuit .env
load_dotenv_file(Path.cwd() / ".env")

USE_TEMP_TOKEN = os.getenv("FEWSPY_USE_TEMP_TOKEN", "false").strip().lower() in {"1", "true", "yes", "on"}
TEMP_ACCESS_TOKEN = os.getenv("FEWSPY_ACCESS_TOKEN")

if USE_TEMP_TOKEN:
    required = ["FEWSPY_FEWS_URL", "FEWSPY_ACCESS_TOKEN"]
else:
    required = [
        "FEWSPY_FEWS_URL",
        "FEWSPY_OAUTH2_TOKEN_URL",
        "FEWSPY_OAUTH2_CLIENT_ID",
        "FEWSPY_OAUTH2_CLIENT_SECRET",
        "FEWSPY_OAUTH2_SCOPE",
    ]
missing = [key for key in required if not os.getenv(key)]
if missing:
    raise ValueError(f"Missende env variabelen: {', '.join(missing)}")

FEWS_URL = os.environ["FEWSPY_FEWS_URL"]
OAUTH2_CERT = os.getenv("FEWSPY_OAUTH2_CERT")
OAUTH2_VERIFY = parse_verify_setting(os.getenv("FEWSPY_OAUTH2_VERIFY", "true"))
FEWS_CERT = os.getenv("FEWSPY_FEWS_CERT")
FEWS_VERIFY = parse_verify_setting(os.getenv("FEWSPY_FEWS_VERIFY", "true"))

# %%
# 1) Authenticatie en FEWS-client instellen
if USE_TEMP_TOKEN:
    auth = BearerTokenAuth(TEMP_ACCESS_TOKEN)
else:
    auth = OAuth2ClientCredentialsAuth(
        token_url=os.environ["FEWSPY_OAUTH2_TOKEN_URL"],
        client_id=os.environ["FEWSPY_OAUTH2_CLIENT_ID"],
        client_secret=os.environ["FEWSPY_OAUTH2_CLIENT_SECRET"],
        scope=os.environ["FEWSPY_OAUTH2_SCOPE"],
        cert=OAUTH2_CERT,
        verify=OAUTH2_VERIFY,
    )

api = Api(
    url=FEWS_URL,
    auth=auth,
    cert=FEWS_CERT,
    ssl_verify=FEWS_VERIFY,
    validate_endpoint=False,
)

# %%
# 2) FEWS timeseries request
time_series = api.get_time_series(
    filter_id=None,
    parameter_ids=["H.meting"],
    location_ids=["MPN-AS-1594"],
    start_time=datetime(2025, 7, 2, 12, 44, 53),
    end_time=datetime(2025, 7, 2, 13, 44, 53),
    document_format="PI_JSON",
)

if time_series.empty:
    raise RuntimeError("De FEWS-request gaf geen tijdreeksen terug.")



# %%
