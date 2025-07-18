from pathlib import Path
import json
from fewspy.time_series import TimeSeriesSet

DATA_PATH = Path(__file__).parent / "data"

with open(DATA_PATH / "pi_time_series.json") as src:
    pi_time_series = json.load(src)

timeseriesset = TimeSeriesSet.from_dict(pi_time_series)


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
