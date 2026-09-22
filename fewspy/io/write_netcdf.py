import shutil
import json
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from netCDF4 import Dataset, date2num


def _datetimeindex_to_nc_time(
    idx: pd.DatetimeIndex, units="seconds since 1970-01-01 00:00:00 UTC"
):
    # netCDF4.date2num expects naive datetimes + units/tz in string;
    py_dt = [
        d.to_pydatetime().replace(tzinfo=timezone.utc).replace(tzinfo=None) for d in idx
    ]
    return date2num(py_dt, units=units), units


def _validate_file_naming(series_key, file_naming, include_time_series_type):
    if file_naming not in ("default", "archive"):
        raise ValueError("file_naming must be 'default' or 'archive'")
    if file_naming == "archive" and series_key != "header":
        raise ValueError("file_naming='archive' requires series_key='header'")
    if include_time_series_type and file_naming != "archive":
        raise ValueError("include_time_series_type requires file_naming='archive'")


def _archive_identity(header, include_time_series_type):
    """Build a readable name; the NetCDF metadata remains authoritative."""
    step = header.time_step
    timestep = step.get("id")
    if not timestep:
        unit = step.get("unit")
        if not unit:
            raise ValueError("Archive naming requires a timestep id or unit")
        timestep = unit
        if unit != "nonequidistant":
            multiplier = step.get("multiplier")
            timestep += f"-{1 if multiplier is None else multiplier}"
            if step.get("divider") is not None:
                timestep += f"-div{step['divider']}"
    qualifiers = header.qualifier_id or []
    parts = [
        header.parameter_id,
        "[" + "_".join(qualifiers) + "]",
        timestep,
    ]
    if header.value_type is not None:
        parts.append(header.value_type)
    parts.append(header.module_instance_id)
    if include_time_series_type and header.time_series_type is not None:
        parts.append(header.time_series_type)
    if not header.parameter_id or any(part == "" for part in [*parts, *qualifiers]):
        raise ValueError(
            "Archive naming requires nonempty parameter, qualifiers, value_type, "
            "module_instance_id and any requested time_series_type"
        )
    return "_".join("null" if part is None else part for part in parts)


def _header_groups(
    df, file_template, file_naming="default", include_time_series_type=False
):
    from fewspy.time_series import Header, HEADER_KEY_FIELDS, canonical_json

    if list(df.columns.names) != HEADER_KEY_FIELDS:
        raise ValueError(
            "Header mode requires the full header MultiIndex from to_df(series_key='header')"
        )
    metadata = [Header.from_json(value) for value in df.attrs.get("fewspy_headers", [])]
    by_key = {header.series_identity("header"): header for header in metadata}
    headers = []
    for column in df.columns:
        key = tuple(None if pd.isna(value) else value for value in column)
        if key not in by_key:
            raise ValueError(
                "DataFrame identity has no matching fewspy_headers metadata"
            )
        headers.append(by_key[key])
    if df.columns.has_duplicates:
        raise ValueError("Duplicate full header identities cannot be written to NetCDF")
    groups = {}
    for index, header in enumerate(headers):
        key = header.series_identity("header")
        group = key[:2] + key[3:]  # Locations are the station dimension.
        groups.setdefault(group, []).append(index)
    filenames = set()
    result = []
    for indices in groups.values():
        header = headers[indices[0]]
        # JSON distinguishes null, empty strings, and qualifier boundaries.
        parts = [
            header.parameter_id,
            header.qualifier_id or [],
            header.time_step,
            header.value_type,
            header.module_instance_id,
            header.time_series_type,
        ]
        identity = "_".join(quote(canonical_json(value), safe="") for value in parts)
        if file_naming == "archive":
            identity = _archive_identity(header, include_time_series_type)
        template = (
            "{identity}.nc" if file_template == "{parameter_id}.nc" else file_template
        )
        filename = template.format(
            identity=identity,
            parameter_id=(
                header.parameter_id
                if file_naming == "archive"
                else quote(header.parameter_id, safe="")
            ),
        )
        if (
            Path(filename).name != filename
            or any(c in filename for c in '<>:"/\\|?*')
            or any(ord(c) < 32 for c in filename)
            or filename.split(".")[0].upper()
            in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *[f"COM{i}" for i in range(1, 10)],
                *[f"LPT{i}" for i in range(1, 10)],
            }
            or filename.endswith((".", " "))
            or len(filename.encode("utf-8")) > 240
        ):
            raise ValueError(
                "Invalid or overlong NetCDF filename; shorten the header identifiers or file_template"
            )
        if filename.casefold() in filenames:
            raise ValueError(
                "NetCDF filename collision: use a unique template or include_time_series_type=True; check qualifier separators"
            )
        filenames.add(filename.casefold())
        result.append(
            (
                header.parameter_id,
                df.iloc[:, indices],
                filename,
                [headers[i].to_json() for i in indices],
            )
        )
    return result


def write_netcdf(
    df: pd.DataFrame,
    out_dir: Path,
    global_attributes: dict = {"source": "fewspy"},
    file_template: str = "{parameter_id}.nc",
    remove_dir: bool = False,
    series_key: str = "location_parameter",
    file_naming: str = "default",
    include_time_series_type: bool = False,
) -> None:
    """Write a pandas DataFrame to netCDF files, one per parameter_id.

    Args:
        df (pd.DataFrame): Reliable values from TimeSeriesSet.to_df.
        series_key: "location_parameter" (default) or "header". Header mode
            requires the full column identity and fewspy_headers metadata.
        file_naming: "default" preserves existing names; "archive" uses readable
            parameter, qualifiers, timestep, value type and module instance.
        include_time_series_type: Append the full type in archive mode when known.
        Missing value_type and time_series_type are omitted from archive names.
        out_dir (Path): Output directory.
        global_attributes (dict(str), optional): _description_. Defaults to {"source": "fewspy"}.
        file_template (str, optional): _description_. Defaults to "{parameter_id}.nc".
        remove_dir (bool, optional): If True, removes the output directory before writing. Defaults to False.
    """

    from fewspy.time_series import validate_series_key

    validate_series_key(series_key)
    _validate_file_naming(series_key, file_naming, include_time_series_type)
    if series_key == "header":
        groups = _header_groups(
            df, file_template, file_naming, include_time_series_type
        )
        # Validate against existing files before changing anything.
        if not remove_dir:
            for _, _, filename, headers in groups:
                path = out_dir / filename
                if path.exists():
                    with Dataset(path) as existing:
                        if getattr(existing, "fewspy_headers", None) != json.dumps(
                            headers
                        ):
                            raise ValueError(
                                f"Refusing to overwrite different headers in {path}"
                            )
    else:
        groups = [
            (
                parameter,
                df.loc[:, df.columns.get_level_values(1) == parameter].dropna(
                    how="all"
                ),
                file_template.format(parameter_id=parameter),
                None,
            )
            for parameter in set(df.columns.get_level_values(1))
        ]

    # prepare output directory
    if remove_dir:
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(exist_ok=True, parents=True)

    # write one netCDF file per parameter_id
    for parameter_id, dfp, filename, headers in groups:
        # to numpy
        values = dfp.to_numpy(dtype=float)

        # prepare dimensions
        location_ids = dfp.columns.get_level_values(
            "location_id" if headers else 0
        ).to_list()
        strlen = (
            max(len(s.encode("utf-8")) for s in location_ids)
            if headers
            else max(len(s) for s in location_ids)
        )
        time_vals, time_units = _datetimeindex_to_nc_time(dfp.index)

        # create netCDF file
        nc_file = out_dir / filename
        with Dataset(nc_file, "w", format="NETCDF4_CLASSIC") as nc:
            n_time, n_stations = values.shape

            # dimensions
            nc.createDimension("time", n_time)
            nc.createDimension("stations", n_stations)
            nc.createDimension("char_leng_id", strlen)  # for station_id

            # variables: time
            vtime = nc.createVariable("time", "f8", ("time",))
            vtime.units = time_units
            vtime.standard_name = "time"
            vtime.long_name = "time"
            vtime.calendar = "gregorian"
            vtime[:] = time_vals

            # variables: station

            vstation = nc.createVariable(
                "station_id", "S1", ("stations", "char_leng_id")
            )
            vstation.long_name = "station identification code"
            vstation.cf_role = "timeseries_id"

            # convert list of strings to array of characters (FEWS style)
            arr = np.array(
                [s.encode("utf-8") for s in location_ids] if headers else location_ids,
                dtype=f"S{strlen}",
            )  # fixed-length bytestrings
            data = arr.view("S1").reshape(n_stations, strlen)
            vstation[:, :] = data

            # compression and chunks
            compression_args = dict(zlib=True, complevel=4, shuffle=True)
            chunks = (max(1, min(max(n_time // 10, 1), n_time)), min(n_stations, 128))

            vval = nc.createVariable(
                "value" if headers else parameter_id,
                "f4",
                ("time", "stations"),
                fill_value=np.nan,
                chunksizes=chunks,
                **compression_args,
            )
            vval.coordinates = "time station_id"
            vval[:] = values

            # Globale attributen (CF-vriendelijk)
            nc.Conventions = "CF-1.6"
            nc.featureType = "timeSeries"
            nc.history = f"Created {datetime.now(timezone.utc).isoformat()}Z"
            nc.parameter_id = parameter_id
            for key, value in global_attributes.items():
                setattr(nc, key, value)

            if headers:
                nc.fewspy_headers = json.dumps(headers)
                nc.fewspy_series_key = "header"
                nc.parameter_id = parameter_id
