import pandas as pd
import xarray as xr
import shutil
from datetime import datetime, timezone
from pathlib import Path

def _datetimeindex_to_nc_time(idx: pd.DatetimeIndex, units="seconds since 1970-01-01 00:00:00 UTC"):
    # xarray gebruikt standaard np.datetime64, maar units kunnen worden toegevoegd als attribuut
    return idx.to_numpy(), units

def write_netcdf(
    df: pd.DataFrame,
    out_dir: Path,
    global_attributes: dict = {"source": "fewspy"},
    file_template: str = "{parameter_id}.nc",
    remove_dir: bool = False,
) -> None:
    """Write NetCDF files using xarray

    Args:
        df (pd.DataFrame): MultiIndex columns: (location_id, parameter_id)
        out_dir (Path): Output directory
        global_attributes (dict, optional): Global attributes for NetCDF file
        file_template (str, optional): Filename template
        remove_dir (bool, optional): Remove output dir before writing
    """
    if remove_dir:
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(exist_ok=True, parents=True)

    for parameter_id in set(df.columns.get_level_values(1)):
        dfp = df.loc[:, df.columns.get_level_values(1) == parameter_id].dropna(how="all")
        values = dfp.to_numpy(dtype=float)
        location_ids = dfp.columns.get_level_values(0).to_list()
        time_vals, time_units = _datetimeindex_to_nc_time(dfp.index)

        # Maak een xarray Dataset
        ds = xr.Dataset(
            {
                parameter_id: (['time', 'stations'], values)
            },
            coords={
                'time': ('time', time_vals, {'units': time_units}),
                'station_id': ('stations', location_ids)
            },
            attrs={
                'Conventions': 'CF-1.6',
                'featureType': 'timeSeries',
                'history': f"Created {datetime.now(timezone.utc).isoformat()}Z",
                'parameter_id': parameter_id,
                **global_attributes
            }
        )

        # Schrijf naar NetCDF
        nc_file = out_dir / file_template.format(parameter_id=parameter_id)
        ds.to_netcdf(nc_file, format="NETCDF4", engine="netcdf4", encoding={parameter_id: {"zlib": True, "complevel": 4}})

# Functie om NetCDF-bestand weer in een DataFrame te lezen
def read_netcdf_to_dataframe(nc_path: Path, parameter_id: str) -> pd.DataFrame:
    """
    Lees een NetCDF-bestand (gemaakt door write_netcdf) terug naar een pandas DataFrame.

    Args:
        nc_path (Path): Pad naar NetCDF-bestand
        parameter_id (str): Parameter die gelezen moet worden

    Returns:
        pd.DataFrame: DataFrame met MultiIndex columns (location_id, parameter_id)
    """
    ds = xr.open_dataset(nc_path)
    values = ds[parameter_id].values
    times = pd.to_datetime(ds['time'].values)
    stations = ds['station_id'].to_numpy().tolist()  # converteer naar lijst van strings
    stations = [str(s) for s in stations]
    columns = pd.MultiIndex.from_product([stations, [parameter_id]], names=["location_id", "parameter_id"])
    df = pd.DataFrame(values, index=times, columns=columns)
    return df