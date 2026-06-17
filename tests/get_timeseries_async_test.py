from datetime import datetime
import pytest


LOCATION_IDS = ["NL34.HL.KGM156.HWZ1", "NL34.HL.KGM156.LWZ1"]
PARAMETER_IDS = ["Q [m3/s] [NVT] [OW]", "WATHTE [m] [NAP] [OW]"]
QUALIFIER_IDS = ["productie"]


@pytest.fixture(scope="module")
def time_series_set(api):
    return api.get_time_series(
        filter_id="WDB_OW_KGM",
        location_ids=LOCATION_IDS,
        start_time=datetime(2022, 5, 1),
        end_time=datetime(2022, 5, 5),
        parameter_ids=PARAMETER_IDS,
        qualifier_ids=QUALIFIER_IDS,
        parallel=True,
    )


def test_time_zone(time_series_set):
    assert time_series_set.time_zone == 1.0


def test_version(time_series_set):
    assert time_series_set.version == "1.31"


def test_empty(time_series_set):
    assert not time_series_set.empty


def test_length(time_series_set):
    assert len(time_series_set) == 2


def test_parameter_ids(time_series_set):
    assert all([i in PARAMETER_IDS for i in time_series_set.parameter_ids])


def test_location_ids(time_series_set):
    assert all([i in LOCATION_IDS for i in time_series_set.location_ids])


def test_qualifier_ids(time_series_set):
    assert time_series_set.qualifier_ids == ["productie"]
