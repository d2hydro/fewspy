"""Validated metadata and selective reads of fewspy header-mode NetCDF files."""

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from fewspy.io.read_netcdf import _parse_time
from fewspy.time_series import Header, SeriesKey, TimeSeries, TimeSeriesSet


@dataclass
class HeaderMetadata:
    headers: tuple[Header, ...]
    time: pd.DatetimeIndex
    locations: dict[str, list[int]]
    selective: bool
    decoded: bool = False


def read_metadata(dataset) -> HeaderMetadata:
    """Validate every header, including locations outside a later selection."""
    if getattr(dataset, "fewspy_series_key", None) != SeriesKey.HEADER.value:
        raise ValueError("NetCDF has no full FEWS header metadata")
    raw_headers = json.loads(dataset.fewspy_headers)
    time = _parse_time(dataset.variables["time"])
    variable = dataset.variables["value"]
    if len(raw_headers) != variable.shape[1]:
        raise ValueError("NetCDF header count does not match stations")
    headers = tuple(Header.from_json(header) for header in raw_headers)
    locations = {}
    for position, header in enumerate(headers):
        locations.setdefault(header.location_id, []).append(position)
    return HeaderMetadata(
        headers,
        time,
        locations,
        variable.dimensions == ("time", "stations")
        # Integer/string variants can raise on full-array NaN filling even when
        # the selected values themselves have no missing data. Preserve that.
        and np.dtype(variable.dtype).kind == "f"
        and time.is_monotonic_increasing
        and time.is_unique,
    )


def read_selection(dataset, metadata, positions, time_slice) -> TimeSeriesSet:
    """Materialize only selected values; keep the original validated headers."""
    # NetCDF4 indexes the two axes independently, retaining the station axis.
    values = dataset.variables["value"][time_slice, positions].filled(float("nan"))
    time = metadata.time[time_slice]
    return TimeSeriesSet(
        time_zone=0.0,
        time_series=[
            TimeSeries(header=metadata.headers[position], events=pd.DataFrame({"value": values[:, i]}, index=time))
            for i, position in enumerate(positions)
        ],
    )


def select_positions(metadata, location_ids):
    if location_ids is None:
        return np.arange(len(metadata.headers))
    # Match membership semantics: requested order and repeated IDs do not
    # reorder or duplicate columns. Distinct identities at one location remain.
    return np.array(
        sorted(position for location in set(location_ids) for position in metadata.locations.get(location, ())),
        dtype=np.intp,
    )
