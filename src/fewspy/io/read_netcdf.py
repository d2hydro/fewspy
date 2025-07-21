from netCDF4 import Dataset, num2date
from pathlib import Path
import pandas as pd
from fewspy.time_series import TimeSeriesSet, TimeSeries, Header
import zipfile
from io import  BytesIO
import tempfile
import os


type = "instantaneous"
module_instance_id = "Vullingsgraad"


def _parse_time(time_var):
    times = num2date(time_var[:], units=time_var.units, only_use_cftime_datetimes=False)
    time_index = pd.to_datetime(times)
    time_index.name = "datetime"
    return time_index


def _get_time_step(time_index):
    # time delta
    deltas = time_index.to_series().diff().dropna()
    first_delta = deltas.iloc[0]
    equidistant = (deltas == first_delta).all()
    if equidistant:
        return {"unit": "second", "multiplier": first_delta.total_seconds()}
    else:
        return {"unit": "nonequidistant"}


def _parse_locations(stations_var):
    station_id_var = stations_var[:]

    return [
        "".join([c.decode("utf-8") if isinstance(c, bytes) else "" for c in row])
        .strip()
        .replace("\x00", "")
        for row in station_id_var
    ]


def _get_parameter_id(ds):
    parameter_ids = [
        var_name
        for var_name, var in ds.variables.items()
        if var.dimensions == ("time", "stations")
    ]
    return parameter_ids



def read_netcdf_from_content(content) -> TimeSeriesSet:
    """Read zipped NetCDF content as TimeSeriesSet 

    Parameters
    ----------
    content : Bytes
        Zipped NetCDF content

    Returns
    -------
    TimeSeriesSet
        timeseries

    Raises
    ------
    ValueError
        In case no netcdf-file is present in content
    """
    with zipfile.ZipFile(BytesIO(content)) as zf:
        nc_file_name  = next((name for name in zf.namelist() if name.endswith(".nc")), None)
        if nc_file_name is None:
            raise ValueError(f"No NetCDF-file in content, with filelist {zf.namelist()}")
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            tmp.write(zf.read(nc_file_name))
            tmp_path = tmp.name
            try:
                result = read_netcdf(Path(tmp_path))
            finally:
                os.remove(tmp_path)

            return result


def read_netcdf(
    nc_file: Path,
    time_series_type: str | None = None,
    module_instance_id: str | None = None,
) -> TimeSeriesSet:
    """Read the content of a NetCDF file into a fewspy TimeSeriesSet

    Args:
        nc_file (Path): path to the NetCDF file
        time_series_type (str | None, optional): type for timeseries header. Defaults to None.
        module_instance_id (str | None, optional): ModuleInstanceId for timeseries header. Defaults to None.

    Returns:
        TimeSeriesSet: timeseries
    """
    # Read file
    with Dataset(nc_file, mode="r") as ds:

        # init TimeSeriesSet
        time_series_set = TimeSeriesSet(time_zone=0.0)

        # Get time-index for events
        time_index = _parse_time(ds.variables["time"])
        time_step = _get_time_step(time_index)
        start_date = time_index[0].to_pydatetime()
        end_date = time_index[-1].to_pydatetime()

        # Get Locations
        location_ids = _parse_locations(ds.variables["station_id"])
        location_names = _parse_locations(ds.variables["station_names"])

        # Get coordinates
        x = list(ds.variables["x"][:].data)
        y = list(ds.variables["y"][:].data)
        lat = list(ds.variables["lat"][:].data)
        lon = list(ds.variables["lon"][:].data)
        z_fill = ds.variables["z"]._FillValue
        z = [None if i == z_fill else float(i) for i in ds.variables["z"][:].data]

        # Get Parameters
        parameter_ids = _get_parameter_id(ds)

        # Populate TimeSeries
        for parameter_id in parameter_ids:
            var = ds.variables[parameter_id]
            miss_val = float(var._FillValue)
            for i in range(len(location_ids)):
                # define header
                header = Header(
                    type=time_series_type,
                    module_instance_id=module_instance_id,
                    location_id=location_ids[i],
                    parameter_id=parameter_id,
                    time_step=time_step,
                    start_date=start_date,
                    end_date=end_date,
                    x=float(x[i]),
                    y=float(y[i]),
                    lat=float(lat[i]),
                    lon=float(lon[i]),
                    units=var.units,
                    station_name=location_names[i],
                    z=z[i],
                    qualifier_id=None,
                    miss_val=miss_val,
                )

                # define events
                data = {"value": pd.to_numeric(var[:, i].data, downcast="float")}
                events = pd.DataFrame(data=data, index=time_index)

                # append to TimeSeriesSet
                time_series_set.time_series.append(TimeSeries(header=header, events=events))

    return time_series_set
