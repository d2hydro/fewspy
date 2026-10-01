from importlib.metadata import PackageNotFoundError, version

from fewspy.api import Api
from fewspy.auth import Auth, BasicAuth, BearerTokenAuth, OAuth2ClientCredentialsAuth
from fewspy.io.read_json import read_json
from fewspy.io.read_netcdf import read_netcdf
from fewspy.io.read_parquet import read_parquet
from fewspy.io.read_xml import read_xml
from fewspy.io.write_netcdf import write_netcdf
from fewspy.time_series import SeriesKey, TimeSeries, TimeSeriesSet

__all__ = [
    "Api",
    "Auth",
    "BasicAuth",
    "BearerTokenAuth",
    "OAuth2ClientCredentialsAuth",
    "SeriesKey",
    "TimeSeries",
    "TimeSeriesSet",
    "read_json",
    "read_netcdf",
    "read_parquet",
    "read_xml",
    "write_netcdf",
]

try:
    __version__ = version("fewspy")
except PackageNotFoundError:
    __version__ = "0+unknown"
