import json

import pytest

from fewspy import Api, SeriesKey, TimeSeriesSet, read_netcdf, read_parquet
from fewspy.cache.time_series_cache import TimeSeriesCache
from fewspy.io.read_netcdf import read_netcdf_from_content
from fewspy.io.write_netcdf import write_netcdf
from fewspy.time_series import SeriesKey as TimeSeriesKey
from fewspy.wrappers.get_time_series import get_time_series
from fewspy.wrappers.get_time_series_async import get_time_series_async


@pytest.mark.parametrize("mode", list(SeriesKey))
def test_enum_string_compatibility(mode):
    assert TimeSeriesKey is SeriesKey
    assert SeriesKey(mode.value) is mode
    assert str(mode) == mode.value
    assert json.dumps(mode) == json.dumps(mode.value)
    assert mode == mode.value


@pytest.mark.parametrize("invalid", ["invalid", "HEADER", "", None, 1])
@pytest.mark.parametrize(
    "entry_point",
    [
        lambda key, path: TimeSeriesSet().to_df(key),
        lambda key, path: TimeSeriesSet().to_netcdf(path, series_key=key),
        lambda key, path: TimeSeriesSet().to_parquet(path, series_key=key),
        lambda key, path: read_netcdf(path, series_key=key),
        lambda key, path: read_parquet(path, series_key=key),
        lambda key, path: read_netcdf_from_content(b"", series_key=key),
        lambda key, path: write_netcdf(None, path, series_key=key),
        lambda key, path: Api.get_time_series(None, "filter", series_key=key),
        lambda key, path: get_time_series("", "filter", series_key=key),
        lambda key, path: get_time_series_async("", "filter", series_key=key),
        lambda key, path: TimeSeriesCache.get_time_series(
            None, "filter", "parameter", series_key=key
        ),
    ],
)
def test_invalid_mode_rejected_before_io(entry_point, invalid, tmp_path):
    target = tmp_path / "missing"
    with pytest.raises(ValueError, match="SeriesKey"):
        entry_point(invalid, target)
    assert not target.exists()
