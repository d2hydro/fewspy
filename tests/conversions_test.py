from datetime import datetime

import numpy as np
import pytest

from fewspy.utils.conversions import attributes_to_array, dict_to_datetime, geo_datum_to_crs, xy_array_to_point
from fewspy.utils.transformations import parameters_to_fews


@pytest.mark.parametrize(
    ("datum", "expected"),
    [
        ("UTM31N", "epsg:32631"),
        ("UTM05S", "epsg:32705"),
        ("EPSG:28992", "epsg:28992"),
        ("Rijks Driehoekstelsel", "epsg:28992"),
        ("Gauss Krueger Meridian2", None),
        ("unknown", None),
    ],
)
def test_geo_datum_to_crs(datum, expected):
    assert geo_datum_to_crs(datum) == expected


def test_attributes_preserve_requested_order_and_missing_values():
    values = np.array(
        [
            [{"id": "b", "value": "second"}, {"id": "a", "value": "first"}],
            [{"id": "a", "value": "other"}, {"id": "ignored", "value": "unused"}],
        ],
        dtype=object,
    )
    result = attributes_to_array(values, ["a", "b", "missing"])
    assert result.tolist() == [["first", "second", None], ["other", None, None]]


def test_xy_conversion_preserves_coordinate_order():
    points = xy_array_to_point(np.array([["4.5", "52.0"], ["5.0", "53.0"]]))
    assert [(point.x, point.y) for point in points] == [(4.5, 52.0), (5.0, 53.0)]
    assert xy_array_to_point(np.empty((0, 2))) == []


def test_pi_date_without_time_defaults_to_midnight():
    assert dict_to_datetime({"date": "2026-01-02"}) == datetime(2026, 1, 2)
    assert dict_to_datetime({"date": "2026-01-02", "time": "12:34:56"}) == datetime(2026, 1, 2, 12, 34, 56)


@pytest.mark.parametrize("bool_to_string", [False, True])
def test_request_parameters_preserve_false_zero_and_lists(bool_to_string):
    parameters = {
        "start_time": datetime(2026, 1, 2),
        "only_headers": False,
        "thinning": 0,
        "location_ids": ["a", "b"],
        "attributes": ["region"],
        "filter_id": None,
        "unknown": "ignored",
    }
    result = parameters_to_fews(parameters, bool_to_string=bool_to_string)
    assert result == {
        "startTime": "2026-01-02T00:00:00Z",
        "onlyHeaders": "False" if bool_to_string else False,
        "thinning": 0,
        "locationIds": ["a", "b"],
        "showAttributes": "True" if bool_to_string else True,
    }
    assert parameters["attributes"] == ["region"]
    assert parameters["start_time"] == datetime(2026, 1, 2)
