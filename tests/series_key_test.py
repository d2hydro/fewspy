from copy import deepcopy

from pathlib import Path

import json


import pytest
from fewspy.time_series import Header, TimeSeries
from fewspy.io.read_netcdf import read_netcdf, read_netcdf_from_content
from fewspy.io.read_parquet import read_parquet

import pandas as pd

from netCDF4 import Dataset


from fewspy.time_series import TimeSeriesSet


def duplicate_series():

    source = json.loads(
        (Path(__file__).parent / "data/pi_time_series.json").read_text()
    )

    first = source["timeSeries"][0]

    second = deepcopy(first)

    second["header"]["moduleInstanceId"] = "another_module"

    source["timeSeries"] = [first, second]

    return TimeSeriesSet.from_dict(source)


def test_default_duplicate_columns():

    series = duplicate_series()

    df = series.to_df()

    assert df.columns.names == ["location_id", "parameter_id"]

    assert df.shape[1] == 2

    assert df.columns[0] == df.columns[1]

    pd.testing.assert_series_equal(df.iloc[:, 0], df.iloc[:, 1])


def test_default_netcdf_layout(tmp_path):

    series = duplicate_series()

    series.to_netcdf(tmp_path)

    parameter = series.parameter_ids[0]

    assert [p.name for p in tmp_path.iterdir()] == [f"{parameter}.nc"]

    with Dataset(tmp_path / f"{parameter}.nc") as ds:

        assert len(ds.dimensions["stations"]) == 2

        assert ds.variables[parameter].dimensions == ("time", "stations")

        assert "fewspy_headers" not in ds.ncattrs()


import pytest

from fewspy.time_series import Header, TimeSeries

from fewspy.io.read_netcdf import read_netcdf, read_netcdf_from_content

from fewspy.io.read_parquet import read_parquet


@pytest.fixture
def header_series():

    base = dict(
        type="instantaneous",
        location_id="L",
        parameter_id="P",
        time_step={"unit": "hour", "multiplier": 1},
        start_date="2024-01-01T00:00:00",
        end_date="2024-01-01T01:00:00",
        module_instance_id="M",
        value_type="scalar",
        time_series_type="external historical",
    )

    variants = [
        {},
        {"module_instance_id": "M2"},
        {"value_type": "sample"},
        {"time_series_type": "simulated historical"},
        {"time_step": {"unit": "minute", "multiplier": 30}},
        {"qualifier_id": ["a"]},
        {"qualifier_id": ["a", "b"]},
        {"qualifier_id": ["a,b"]},
        {"qualifier_id": ["a", "a"]},
        {"time_step": {"unit": "second", "multiplier": 1, "divider": 2}},
        {"time_step": {"unit": "nonequidistant"}},
        {"location_id": "L2"},
    ]

    return TimeSeriesSet(
        time_series=[
            TimeSeries(
                header=Header(**(base | variant)),
                events=pd.DataFrame(
                    {"value": [float(i), float(i + 1)]},
                    index=pd.date_range(
                        "2024-01-01", periods=2, freq="h", name="datetime"
                    ),
                ),
            )
            for i, variant in enumerate(variants)
        ]
    )


def test_header_identity_and_dataframe(header_series):

    df = header_series.to_df(series_key="header")

    assert df.shape == (2, 12)

    assert df.columns.is_unique

    for i, series in enumerate(header_series.time_series):

        assert df[series.header.series_identity("header")].iloc[0] == i

    h = deepcopy(header_series.time_series[0].header)

    h.qualifier_id = []

    h.time_step = {"multiplier": 1, "unit": "hour"}

    assert h.series_identity("header") == header_series.time_series[
        0
    ].header.series_identity("header")

    h.qualifier_id = ["a", "b"]

    assert h.series_identity("header") == header_series.time_series[
        6
    ].header.series_identity("header")

    assert Header.from_json(h.to_json()).qualifier_id == ["a", "b"]


def test_netcdf_header_roundtrip(header_series, tmp_path):

    header_series.to_netcdf(tmp_path, series_key="header")

    files = list(tmp_path.glob("*.nc"))

    assert len(files) == 11  # same header at another location shares a file

    restored = TimeSeriesSet()

    for path in files:

        restored.time_series.extend(read_netcdf(path, series_key="header").time_series)

    expected = {
        ts.header.series_identity("header"): ts for ts in header_series.time_series
    }

    assert len(restored) == len(expected)

    for ts in restored.time_series:

        original = expected[ts.header.series_identity("header")]

        assert ts.header.to_json() == original.header.to_json()

        pd.testing.assert_frame_equal(
            ts.events, original.events, check_dtype=False, check_freq=False
        )

    again = tmp_path / "again"

    TimeSeriesSet(time_series=list(reversed(header_series.time_series))).to_netcdf(
        again, series_key="header"
    )

    assert {p.name for p in files} == {p.name for p in again.glob("*.nc")}


def test_header_parquet_roundtrip(header_series, tmp_path):

    path = tmp_path / "series.parquet"

    header_series.to_parquet(path, series_key="header")

    restored = read_parquet(path, series_key="header")

    pd.testing.assert_frame_equal(
        header_series.to_df("header"), restored.to_df("header"), check_freq=False
    )


def test_collisions_fail_before_writing(header_series, tmp_path):

    with pytest.raises(ValueError, match="collision"):

        header_series.to_netcdf(tmp_path, series_key="header", file_template="same.nc")

    assert not list(tmp_path.iterdir())

    header_series.time_series.append(deepcopy(header_series.time_series[0]))

    with pytest.raises(ValueError, match="Duplicate"):

        header_series.to_netcdf(tmp_path, series_key="header")

    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("events", ["empty", "single", "unreliable"])
def test_sparse_netcdf(header_series, tmp_path, events):

    ts = header_series.time_series[0]

    if events == "empty":

        ts.events = ts.events.iloc[:0]

    elif events == "single":

        ts.events = ts.events.iloc[:1]

    else:

        ts.events["flag"] = 9

    TimeSeriesSet(time_series=[ts]).to_netcdf(tmp_path, series_key="header")

    restored = read_netcdf(next(tmp_path.glob("*.nc")), series_key="header")

    assert restored.time_series[0].header.series_identity(
        "header"
    ) == ts.header.series_identity("header")


def test_zip_reads_all_header_files(header_series, tmp_path):

    import zipfile

    from io import BytesIO

    header_series.to_netcdf(tmp_path, series_key="header")

    content = BytesIO()

    with zipfile.ZipFile(content, "w") as archive:

        for path in tmp_path.glob("*.nc"):

            archive.write(path, path.name)

    restored = read_netcdf_from_content(content.getvalue(), series_key="header")

    assert len(restored) == len(header_series)


def test_async_response_keeps_all_headers():

    from fewspy.wrappers.get_time_series_async import __result_async_to_time_series_set

    source = json.loads(
        (Path(__file__).parent / "data/pi_time_series.json").read_text()
    )

    assert len(__result_async_to_time_series_set([source])) == 1

    result = __result_async_to_time_series_set([None, source], series_key="header")

    assert len(result) == len(source["timeSeries"])


def test_invalid_mode(header_series, tmp_path):

    with pytest.raises(ValueError, match="series_key"):

        header_series.to_df("invalid")

    with pytest.raises(ValueError, match="series_key"):

        header_series.to_netcdf(tmp_path, series_key="invalid")


def test_pi_header_fields_and_qualifiers():

    header = dict(
        type="instantaneous",
        locationId="L",
        parameterId="P",
        moduleInstanceId="M",
        valueType="scalar",
        timeSeriesType="external historical",
        timeStep={"unit": "second", "multiplier": "1", "divider": "2"},
        qualifierId=["a", "b"],
        startDate={"date": "2024-01-01", "time": "00:00:00"},
        endDate={"date": "2024-01-01", "time": "01:00:00"},
    )

    parsed = Header.from_dict(header)

    assert parsed.value_type == "scalar"

    assert parsed.time_series_type == "external historical"

    assert parsed.time_step["divider"] == 2

    assert parsed.qualifier_id == ["a", "b"]


def test_cache_preserves_full_header_selection(header_series, tmp_path):
    from fewspy.cache.manifest import Manifest, FieldEndtry
    from fewspy.cache.time_series_cache import TimeSeriesCache

    folder = tmp_path / "filter"
    header_series.to_netcdf(folder, series_key="header")
    manifest = Manifest(
        current_cache="20240101T000000",
        files=[FieldEndtry.from_file(p) for p in folder.glob("*.nc")],
    )
    cache = TimeSeriesCache(manifest)
    try:
        df = cache.get_time_series(
            "filter",
            "P",
            location_ids=["L"],
            start_time="2024-01-01T01:00:00",
            series_key="header",
        )
        assert df.shape == (1, 11)
        assert df.columns.is_unique
        assert set(df.columns.get_level_values("location_id")) == {"L"}
    finally:
        for ds in cache._datasets.values():
            ds.close()


def test_default_explicit_mode(header_series):
    pd.testing.assert_frame_equal(
        header_series.to_df(), header_series.to_df("location_parameter")
    )


def test_api_passes_header_mode(monkeypatch):
    import importlib
    from fewspy import Api

    module = importlib.import_module("fewspy.api")
    captured = []
    monkeypatch.setattr(module, "validate_url", lambda url: (url, False))
    monkeypatch.setattr(
        module, "get_time_series_async", lambda **kwargs: captured.append(kwargs)
    )
    api = Api("https://example.com/", ssl_verify=False)
    api.get_time_series("filter", parallel=True, series_key="header")
    assert captured[0]["series_key"] == "header"
    assert "validate_series_key" not in captured[0]


def test_existing_file_collision(header_series, tmp_path):
    series = TimeSeriesSet(time_series=[header_series.time_series[0]])
    series.to_netcdf(tmp_path, file_template="fixed.nc", series_key="header")
    before = (tmp_path / "fixed.nc").read_bytes()
    series.time_series[0].header.module_instance_id = "changed"
    with pytest.raises(ValueError, match="overwrite"):
        series.to_netcdf(tmp_path, file_template="fixed.nc", series_key="header")
    assert (tmp_path / "fixed.nc").read_bytes() == before


def test_filename_escaping_and_unicode(header_series, tmp_path):
    series = TimeSeriesSet(time_series=[header_series.time_series[0]])
    series.time_series[0].header.parameter_id = "a/b:%"
    series.time_series[0].header.qualifier_id = ["x_y", "x/y"]
    series.time_series[0].header.location_id = "MÃƒÂ¼nchen"
    series.to_netcdf(tmp_path, series_key="header")
    path = next(tmp_path.glob("*.nc"))
    assert "%2F" in path.name
    restored = read_netcdf(path, series_key="header")
    assert restored.time_series[0].header.series_identity(
        "header"
    ) == series.time_series[0].header.series_identity("header")


def test_selected_dataframe_writer(header_series, tmp_path):
    from fewspy.io.write_netcdf import write_netcdf

    selected = header_series.to_df("header").iloc[:, [6, 1]]
    write_netcdf(selected, tmp_path, series_key="header")
    restored = TimeSeriesSet()
    for path in tmp_path.glob("*.nc"):
        restored.time_series.extend(read_netcdf(path, series_key="header").time_series)
    assert {ts.header.series_identity("header") for ts in restored.time_series} == set(
        selected.columns
    )


def test_missing_optional_identity_roundtrip(tmp_path):
    series = duplicate_series()
    series.to_netcdf(tmp_path, series_key="header")
    restored = [
        read_netcdf(p, series_key="header").time_series[0]
        for p in tmp_path.glob("*.nc")
    ]
    assert {ts.header.series_identity("header") for ts in restored} == {
        ts.header.series_identity("header") for ts in series.time_series
    }


def test_empty_header_set(tmp_path):
    series = TimeSeriesSet()
    assert series.to_df("header").columns.nlevels == 7
    path = tmp_path / "empty.parquet"
    series.to_parquet(path, series_key="header")
    assert len(read_parquet(path, series_key="header")) == 0


def test_default_parquet_layout(tmp_path):
    source = json.loads(
        (Path(__file__).parent / "data/pi_time_series.json").read_text()
    )
    series = TimeSeriesSet.from_dict(source)
    path = tmp_path / "default.parquet"
    series.to_parquet(path, include_header=True)
    pd.testing.assert_frame_equal(pd.read_parquet(path), series.to_df())
    pd.testing.assert_frame_equal(read_parquet(path).to_df(), series.to_df())


def test_reject_missing_netcdf_header_metadata(tmp_path):
    duplicate_series().to_netcdf(tmp_path)
    with pytest.raises(ValueError, match="metadata"):
        read_netcdf(next(tmp_path.glob("*.nc")), series_key="header")


def test_xml_preserves_identity_fields():
    from fewspy.io.read_xml import read_xml_from_string

    xml = """<TimeSeries xmlns="http://www.wldelft.nl/fews/PI" version="1.31">
    <timeZone>0</timeZone><series><header>
    <type>instantaneous</type><moduleInstanceId>M</moduleInstanceId>
    <valueType>scalar</valueType><locationId>L</locationId><parameterId>P</parameterId>
    <timeSeriesType>external historical</timeSeriesType>
    <timeStep unit="hour" multiplier="1"/><qualifierId>a</qualifierId><qualifierId>b</qualifierId>
    <startDate date="2024-01-01" time="00:00:00"/>
    <endDate date="2024-01-01" time="01:00:00"/>
    </header></series></TimeSeries>"""
    header = read_xml_from_string(xml).time_series[0].header
    assert header.qualifier_id == ["a", "b"]
    assert header.time_series_type == "external historical"
    assert header.value_type == "scalar"


@pytest.mark.parametrize(
    "qualifiers,expected",
    [
        (None, "P_[]_hour-1_scalar_M.nc"),
        ([], "P_[]_hour-1_scalar_M.nc"),
        (["q"], "P_[q]_hour-1_scalar_M.nc"),
        (["q1", "q2"], "P_[q1_q2]_hour-1_scalar_M.nc"),
    ],
)
def test_archive_names_and_metadata(header_series, tmp_path, qualifiers, expected):
    ts = header_series.time_series[0]
    ts.header.qualifier_id = qualifiers
    series = TimeSeriesSet(time_series=[ts])
    series.to_netcdf(tmp_path, series_key="header", file_naming="archive")
    assert [p.name for p in tmp_path.iterdir()] == [expected]
    restored = read_netcdf(tmp_path / expected, series_key="header")
    assert restored.time_series[0].header.to_json() == ts.header.to_json()
    pd.testing.assert_frame_equal(
        restored.to_df("header"),
        series.to_df("header"),
        check_dtype=False,
        check_freq=False,
    )


@pytest.mark.parametrize(
    "step,token",
    [
        ({"id": "SETS60", "unit": "second", "multiplier": 60}, "SETS60"),
        ({"unit": "minute", "multiplier": 15}, "minute-15"),
        ({"unit": "month"}, "month-1"),
        ({"unit": "second", "multiplier": 1, "divider": 2}, "second-1-div2"),
        ({"unit": "nonequidistant"}, "nonequidistant"),
    ],
)
def test_archive_timestep(header_series, tmp_path, step, token):
    ts = header_series.time_series[0]
    ts.header.time_step = step
    TimeSeriesSet(time_series=[ts]).to_netcdf(
        tmp_path, series_key="header", file_naming="archive"
    )
    assert (tmp_path / f"P_[]_{token}_scalar_M.nc").is_file()


def test_archive_type_suffix_and_collision(header_series, tmp_path):
    series = TimeSeriesSet(
        time_series=[header_series.time_series[0], header_series.time_series[3]]
    )
    with pytest.raises(ValueError, match="collision"):
        series.to_netcdf(tmp_path, series_key="header", file_naming="archive")
    assert not list(tmp_path.iterdir())
    series.to_netcdf(
        tmp_path,
        series_key="header",
        file_naming="archive",
        include_time_series_type=True,
    )
    assert {p.name for p in tmp_path.iterdir()} == {
        "P_[]_hour-1_scalar_M_external historical.nc",
        "P_[]_hour-1_scalar_M_simulated historical.nc",
    }


def test_archive_qualifier_collision(header_series, tmp_path):
    first = deepcopy(header_series.time_series[0])
    second = deepcopy(first)
    first.header.qualifier_id = ["a_b", "c"]
    second.header.qualifier_id = ["a", "b_c"]
    series = TimeSeriesSet(time_series=[first, second])
    with pytest.raises(ValueError, match="collision"):
        series.to_netcdf(tmp_path, series_key="header", file_naming="archive")
    assert not list(tmp_path.iterdir())
    TimeSeriesSet(time_series=[first]).to_netcdf(
        tmp_path, series_key="header", file_naming="archive"
    )
    path = next(tmp_path.glob("*.nc"))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        TimeSeriesSet(time_series=[second]).to_netcdf(
            tmp_path, series_key="header", file_naming="archive"
        )
    assert path.read_bytes() == before


@pytest.mark.parametrize("bad", ["a/b", "a\\b", "a:b", "a?b", "a\x00b", "a\nb"])
def test_archive_invalid_characters(header_series, tmp_path, bad):
    ts = header_series.time_series[0]
    ts.header.qualifier_id = [bad]
    with pytest.raises(ValueError, match="Invalid"):
        TimeSeriesSet(time_series=[ts]).to_netcdf(
            tmp_path, series_key="header", file_naming="archive"
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field", ["module_instance_id", "value_type", "time_series_type"]
)
def test_archive_missing_optional_fields(header_series, tmp_path, field):
    ts = header_series.time_series[0]
    setattr(ts.header, field, None)
    series = TimeSeriesSet(time_series=[ts])
    series.to_netcdf(
        tmp_path,
        series_key="header",
        file_naming="archive",
        include_time_series_type=True,
    )
    path = next(tmp_path.glob("*.nc"))
    expected = {
        "module_instance_id": "P_[]_hour-1_scalar_null_external historical.nc",
        "value_type": "P_[]_hour-1_M_external historical.nc",
        "time_series_type": "P_[]_hour-1_scalar_M.nc",
    }
    assert path.name == expected[field]
    restored = read_netcdf(path, series_key="header")
    assert restored.time_series[0].header.to_json() == ts.header.to_json()


@pytest.mark.parametrize("field", ["module_instance_id"])
def test_archive_null_token_collision(header_series, tmp_path, field):
    first = deepcopy(header_series.time_series[0])
    second = deepcopy(first)
    setattr(first.header, field, None)
    setattr(second.header, field, "null")
    with pytest.raises(ValueError, match="collision"):
        TimeSeriesSet(time_series=[first, second]).to_netcdf(
            tmp_path,
            series_key="header",
            file_naming="archive",
            include_time_series_type=True,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field", ["module_instance_id", "value_type", "time_series_type"]
)
def test_archive_empty_optional_fields_rejected(header_series, tmp_path, field):
    ts = header_series.time_series[0]
    setattr(ts.header, field, "")
    with pytest.raises(ValueError, match="requires nonempty"):
        TimeSeriesSet(time_series=[ts]).to_netcdf(
            tmp_path,
            series_key="header",
            file_naming="archive",
            include_time_series_type=True,
        )


@pytest.mark.parametrize(
    "options",
    [
        {"file_naming": "unknown"},
        {"file_naming": "archive"},
        {"include_time_series_type": True},
    ],
)
def test_archive_option_validation(tmp_path, options):
    with pytest.raises(ValueError):
        TimeSeriesSet().to_netcdf(tmp_path, **options)


def test_archive_modules_and_template(header_series, tmp_path):
    from fewspy.io.write_netcdf import write_netcdf

    series = TimeSeriesSet(time_series=header_series.time_series[:2])
    write_netcdf(
        series.to_df("header"),
        tmp_path,
        series_key="header",
        file_naming="archive",
        file_template="prefix_{identity}.nc",
    )
    assert {p.name for p in tmp_path.iterdir()} == {
        "prefix_P_[]_hour-1_scalar_M.nc",
        "prefix_P_[]_hour-1_scalar_M2.nc",
    }


def test_archive_empty_qualifier_rejected(header_series, tmp_path):
    ts = header_series.time_series[0]
    ts.header.qualifier_id = [""]
    with pytest.raises(ValueError, match="requires nonempty"):
        TimeSeriesSet(time_series=[ts]).to_netcdf(
            tmp_path, series_key="header", file_naming="archive"
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("include_type", [False, True])
def test_archive_missing_both_types(header_series, tmp_path, include_type):
    ts = header_series.time_series[0]
    ts.header.value_type = None
    ts.header.time_series_type = None
    TimeSeriesSet(time_series=[ts]).to_netcdf(
        tmp_path,
        series_key="header",
        file_naming="archive",
        include_time_series_type=include_type,
    )
    path = tmp_path / "P_[]_hour-1_M.nc"
    restored = read_netcdf(path, series_key="header")
    assert restored.time_series[0].header.to_json() == ts.header.to_json()


@pytest.mark.parametrize("field", ["value_type", "time_series_type"])
def test_archive_literal_null_type_is_distinct(header_series, tmp_path, field):
    first = deepcopy(header_series.time_series[0])
    second = deepcopy(first)
    setattr(first.header, field, None)
    setattr(second.header, field, "null")
    TimeSeriesSet(time_series=[first, second]).to_netcdf(
        tmp_path,
        series_key="header",
        file_naming="archive",
        include_time_series_type=True,
    )
    paths = list(tmp_path.glob("*.nc"))
    assert len(paths) == 2
    assert {
        getattr(read_netcdf(path, series_key="header").time_series[0].header, field)
        for path in paths
    } == {None, "null"}


def test_archive_omitted_value_type_collision(header_series, tmp_path):
    first = deepcopy(header_series.time_series[0])
    second = deepcopy(first)
    first.header.value_type = None
    first.header.module_instance_id = "scalar_M"
    series = TimeSeriesSet(time_series=[first, second])
    with pytest.raises(ValueError, match="collision"):
        series.to_netcdf(tmp_path, series_key="header", file_naming="archive")
    assert not list(tmp_path.iterdir())
