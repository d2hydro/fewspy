# %%
import fewspy
from config import data_dir

EXPECTED_LOCATION_IDS = sorted(["CMB_03751-21", "CMB_6100-04"])
EXPECTED_PARAMETER_IDS = ["vullingsgraad"]
EXPECTED_QUALIFIER_IDS = []

XML_FILE = data_dir.joinpath("io", "sample.xml")
JSON_FILE = data_dir.joinpath("io", "sample.json")
NC_FILE = data_dir.joinpath("io", "sample.nc")

xml_ts = fewspy.read_xml(XML_FILE)
json_ts = fewspy.read_json(JSON_FILE)
nc_ts = fewspy.read_netcdf(NC_FILE)


def test_xml_ts():
    """Check xml time-series to expected values"""
    # check basic info
    assert xml_ts.version == "1.34"
    assert xml_ts.time_zone == 0.0

    # amount of time_series
    assert len(xml_ts) == 2

    # some checks in header
    assert sorted(xml_ts.location_ids) == EXPECTED_LOCATION_IDS
    assert xml_ts.parameter_ids == EXPECTED_PARAMETER_IDS
    assert xml_ts.qualifier_ids == EXPECTED_QUALIFIER_IDS

    # xcheck start_time and end_time
    expected_start_date = xml_ts.time_series[0].events.index[0]
    assert xml_ts.time_series[0].header.start_date == expected_start_date
    expected_end_date = xml_ts.time_series[0].events.index[-1]
    assert xml_ts.time_series[0].header.end_date == expected_end_date

    # xcheck interval
    expected_time_step = (
        (expected_end_date - expected_start_date) / (len(xml_ts.time_series[0]) - 1)
    ).total_seconds()

    assert xml_ts.time_series[0].header.time_step["multiplier"] == expected_time_step

    # check values by sum
    assert xml_ts.time_series[0].events["value"].sum() == 0
    assert xml_ts.time_series[1].events["value"].sum() == 6053.0


def test_json_ts():
    """Check json time-series to xml-timeseries


    With FEWS API a sightly different header with documentFormat=PI_XML and documentFormat=PI_JSON are returned
        - start_date in JSON is request start_data in XML first available data
        - z is not returned in XML, but is returned in JSON

    Therefore we pop start_date and z when comparing headers
    """
    # basic info
    assert json_ts.version == xml_ts.version
    assert json_ts.time_zone == xml_ts.time_zone

    # headers
    ignore_keys = ["start_date", "z"]

    json_header = {
        k: v
        for k, v in json_ts.time_series[0].header.__dict__.items()
        if k not in ignore_keys
    }
    xml_header = {
        k: v
        for k, v in xml_ts.time_series[0].header.__dict__.items()
        if k not in ignore_keys
    }

    assert json_header == xml_header

    json_header = {
        k: v
        for k, v in json_ts.time_series[1].header.__dict__.items()
        if k not in ignore_keys
    }
    xml_header = {
        k: v
        for k, v in xml_ts.time_series[1].header.__dict__.items()
        if k not in ignore_keys
    }

    assert json_header == xml_header

    # events
    assert json_ts.time_series[0].events.equals(xml_ts.time_series[0].events)
    assert json_ts.time_series[1].events.equals(xml_ts.time_series[1].events)


def test_netcdf_ts():
    """Check json time-series to xml-timeseries


    With NetCDF does not contain version-info. TimeZone will always be 0 (GMT) Per header is also doen't contain:
        - type
        - module_instance_id
    It does contain z (XML doesn't)

    Events do not contain flags.

    Therefore we don't compare these info
    """

    assert nc_ts.time_zone == 0.0
    # headers
    ignore_keys = ["type", "module_instance_id", "z"]

    nc_header = {
        k: v
        for k, v in nc_ts.time_series[0].header.__dict__.items()
        if k not in ignore_keys
    }

    xml_header = {
        k: v
        for k, v in xml_ts.time_series[0].header.__dict__.items()
        if k not in ignore_keys
    }

    assert nc_header == xml_header

    nc_header = {
        k: v
        for k, v in nc_ts.time_series[1].header.__dict__.items()
        if k not in ignore_keys
    }

    xml_header = {
        k: v
        for k, v in xml_ts.time_series[1].header.__dict__.items()
        if k not in ignore_keys
    }

    assert nc_header == xml_header

    # events
    assert (
        nc_ts.time_series[0]
        .events[["value"]]
        .equals(xml_ts.time_series[0].events[["value"]])
    )
    assert (
        nc_ts.time_series[1]
        .events[["value"]]
        .equals(xml_ts.time_series[1].events[["value"]])
    )


def test_parquet_ts(tmp_path):
    """Check json time-series to xml-timeseries


    With NetCDF does not contain version-info. TimeZone will always be 0 (GMT) Per header is also doen't contain:
        - type
        - module_instance_id
    It does contain z (XML doesn't)

    Events do not contain flags.

    Therefore we don't compare these info
    """

    # make sure parquet-file does not exist
    parquet_file = tmp_path.joinpath("io", "sample.parquet")
    parquet_file.unlink(missing_ok=True)
    assert not parquet_file.exists()

    # store xml_ts as parquet-file and check if exists
    xml_ts.to_parquet(parquet_file, include_header=True)
    assert parquet_file.exists()
    header_file = fewspy.io.header_file.get_header_file(parquet_file)
    assert header_file.exists()

    # read parquet time-series
    parquet_ts = fewspy.read_parquet(parquet_file=parquet_file)

    # headers
    ignore_keys = []

    parquet_header = {
        k: v
        for k, v in parquet_ts.time_series[0].header.__dict__.items()
        if k not in ignore_keys
    }

    xml_header = {
        k: v
        for k, v in xml_ts.time_series[0].header.__dict__.items()
        if k not in ignore_keys
    }

    assert parquet_header == xml_header

    parquet_header = {
        k: v
        for k, v in parquet_ts.time_series[1].header.__dict__.items()
        if k not in ignore_keys
    }

    xml_header = {
        k: v
        for k, v in xml_ts.time_series[1].header.__dict__.items()
        if k not in ignore_keys
    }

    assert parquet_header == xml_header

    # events
    assert (
        parquet_ts.time_series[0]
        .events[["value"]]
        .equals(xml_ts.time_series[0].events[["value"]])
    )
    assert (
        parquet_ts.time_series[1]
        .events[["value"]]
        .equals(xml_ts.time_series[1].events[["value"]])
    )
