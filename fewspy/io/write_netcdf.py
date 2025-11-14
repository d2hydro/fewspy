import shutil
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


def write_netcdf(
    df: pd.DataFrame,
    out_dir: Path,
    global_attributes: dict = {"source": "fewspy"},
    file_template: str = "{parameter_id}.nc",
    remove_dir: bool = False,
) -> None:
    """Write a pandas DataFrame to netCDF files, one per parameter_id.

    Args:
        df (pd.DataFrame): _description_
        out_dir (Path): _description_
        global_attributes (dict(str), optional): _description_. Defaults to {"source": "fewspy"}.
        file_template (str, optional): _description_. Defaults to "{parameter_id}.nc".
        remove_dir (bool, optional): If True, removes the output directory before writing. Defaults to False.
    """

    # prepare output directory
    if remove_dir:
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(exist_ok=True, parents=True)

    # write one netCDF file per parameter_id
    for parameter_id in set(df.columns.get_level_values(1)):
        # Filter dataframe for parameter_id and drop all-NaN rows
        dfp = df.loc[:, df.columns.get_level_values(1) == parameter_id].dropna(
            how="all"
        )

        # to numpy
        values = dfp.to_numpy(dtype=float)

        # prepare dimensions
        location_ids = dfp.columns.get_level_values(0).to_list()
        strlen = max(len(s) for s in location_ids)
        time_vals, time_units = _datetimeindex_to_nc_time(dfp.index)

        # create netCDF file
        nc_file = out_dir / file_template.format(parameter_id=parameter_id)
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
            arr = np.array(location_ids, dtype=f"S{strlen}")  # fixed-length bytestrings
            data = arr.view("S1").reshape(n_stations, strlen)
            vstation[:, :] = data

            # compression and chunks
            compression_args = dict(zlib=True, complevel=4, shuffle=True)
            chunks = (min(max(n_time // 10, 1), n_time), min(n_stations, 128))

            vval = nc.createVariable(
                parameter_id,
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
