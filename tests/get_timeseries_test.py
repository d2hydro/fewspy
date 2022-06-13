from datetime import datetime
from config import api

kwargs = dict(
    filter_id="WDB_OW_KGM",
    location_ids=["NL34.HL.KGM156.HWZ1", "NL34.HL.KGM156.LWZ1"],
    start_time=datetime(2022, 5, 1),
    end_time=datetime(2022, 5, 5),
    parameter_ids=["Q [m3/s] [NVT] [OW]", "WATHTE [m] [NAP] [OW]"],
)

timeseriesset = api.get_time_series(**kwargs)


def test_time_zone():
    assert timeseriesset.time_zone == 1.0


def test_version():
    assert timeseriesset.version == "1.28"


def test_empty():
    assert not timeseriesset.empty


def test_length():
    assert len(timeseriesset) == 2


def test_parameter_ids():
    assert timeseriesset.parameter_ids == ["WATHTE [m] [NAP] [OW]"]


def test_location_ids():
    assert all(
        [
            i in ["NL34.HL.KGM156.LWZ1", "NL34.HL.KGM156.HWZ1"]
            for i in timeseriesset.location_ids
        ]
    )


def test_qualifier_ids():
    assert timeseriesset.qualifier_ids == ["validatie"]
