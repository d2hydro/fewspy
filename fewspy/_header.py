"""FEWS header models and identity helpers, independent of time-series I/O.

This module is for internal use only. Import Header from fewspy.time_series.
"""

import json
import warnings
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import List, Literal, TypedDict

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from fewspy.utils.conversions import camel_to_snake_case, dict_to_datetime

DATETIME_KEYS = ["start_date", "end_date"]
FLOAT_KEYS = ["miss_val", "lat", "lon", "x", "y", "z"]
STRING_KEYS = ["module_instance_id"]
HEADER_KEY_FIELDS = [
    "module_instance_id",
    "value_type",
    "location_id",
    "parameter_id",
    "time_series_type",
    "time_step",
    "qualifier_id",
]


class SeriesKey(str, Enum):
    """Fields used to identify a FEWS time series."""

    LOCATION_PARAMETER = "location_parameter"
    HEADER = "header"

    def __str__(self) -> str:
        return self.value


def canonical_json(value):
    """Convert a value to JSON with a consistent representation.

    Keys are sorted and whitespace is removed so that equivalent values always
    produce the same string. For example, ``{"a": 1, "b": 2}`` and
    ``{"b": 2, "a": 1}`` both become ``'{"a":1,"b":2}'``.

    Parameters
    ----------
    value
        Value to convert to JSON.

    Returns
    -------
    str
        JSON string with consistent key order and formatting.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(config=ConfigDict(arbitrary_types_allowed=False))
class TimeStepDict(TypedDict, total=False):
    unit: Literal["second", "minute", "hour", "day", "month", "year", "nonequidistant"]
    multiplier: int | None
    divider: int | None
    id: str | None


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Header:
    """FEWS-PI header-style dataclass"""

    # required arguments
    type: Literal["accumulative", "instantaneous"]
    location_id: str
    parameter_id: str
    time_step: TimeStepDict
    start_date: datetime
    end_date: datetime

    # Optional arguments
    module_instance_id: str | None = None
    miss_val: float = float("nan")
    lat: float | None = None
    lon: float | None = None
    x: float | None = None
    y: float | None = None
    units: str | None = None
    station_name: str | None = None
    z: float | None = None
    qualifier_id: List[str] | None = None
    value_type: str | None = None
    time_series_type: str | None = None

    def series_identity(
        self, series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER
    ) -> tuple:
        """Hashable FEWS identity; nested fields use unambiguous canonical JSON.

        Qualifier order is retained, as in the PI header. None and [] both mean
        no qualifiers. Missing optional scalar fields remain None.
        """
        series_key = SeriesKey(series_key)
        if series_key == SeriesKey.LOCATION_PARAMETER:
            return self.location_id, self.parameter_id
        return (
            self.module_instance_id,
            self.value_type,
            self.location_id,
            self.parameter_id,
            self.time_series_type,
            canonical_json(self.time_step),
            canonical_json(self.qualifier_id or []),
        )

    def to_json(self):
        return json.dumps(asdict(self), default=lambda value: value.isoformat())

    @classmethod
    def from_json(cls, value):
        return cls(**json.loads(value))

    @classmethod
    def from_pi_header(cls, pi_header: dict) -> "Header":
        warnings.warn(
            "from_pi_header is depricated, use from_dict instead.", DeprecationWarning
        )
        return cls.from_dict(pi_header=pi_header)

    @classmethod
    def from_dict(cls, pi_header: dict) -> "Header":
        """
        Parse Header from FEWS PI header dict.

        Args:
            pi_header (dict): FEWS PI header as dictionary

        Returns:
            Header: FEWS-PI header-style dataclass

        """

        def _convert_kv(k: str, v) -> dict:
            k = camel_to_snake_case(k)
            if k in DATETIME_KEYS:
                v = dict_to_datetime(v)
            elif k in FLOAT_KEYS:
                v = float(v)
            elif k in STRING_KEYS:
                if v == "None":
                    v = None
                else:
                    v = str(v)
            elif k == "time_step":
                if "multiplier" in v.keys():
                    v["multiplier"] = float(v["multiplier"])
            return k, v

        args = (_convert_kv(k, v) for k, v in pi_header.items())
        return cls(**{i[0]: i[1] for i in args})

    def to_row(self):
        flat = self.__dict__.copy()
        for key in ("value_type", "time_series_type"):
            if flat.get(key) is None:
                flat.pop(key, None)
        ts = flat.pop("time_step", {})
        flat["time_step.unit"] = ts.get("unit")
        flat["time_step.multiplier"] = ts.get("multiplier")
        return flat
