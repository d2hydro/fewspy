from datetime import datetime
from config import api


LOCATION_IDS = ["NL34.HL.KGM156.HWZ1", "NL34.HL.KGM156.LWZ1"]
PARAMETER_IDS = ["Q [m3/s] [NVT] [OW]", "WATHTE [m] [NAP] [OW]"]
QUALIFIER_IDS = ["productie"]

time_series_set = api.get_time_series(
    filter_id="WDB_OW_KGM",
    location_ids=LOCATION_IDS,
    start_time=datetime(2022, 5, 1),
    end_time=datetime(2022, 5, 5),
    parameter_ids=PARAMETER_IDS,
    qualifier_ids=QUALIFIER_IDS,
    parallel=True,
)


def test_time_zone():
    assert time_series_set.time_zone == 1.0


def test_version():
    assert time_series_set.version == "1.31"


def test_empty():
    assert not time_series_set.empty


def test_length():
    assert len(time_series_set) == 2


def test_parameter_ids():
    assert all([i in PARAMETER_IDS for i in time_series_set.parameter_ids])


def test_location_ids():
    assert all([i in LOCATION_IDS for i in time_series_set.location_ids])


def test_qualifier_ids():
    assert time_series_set.qualifier_ids == ["productie"]
