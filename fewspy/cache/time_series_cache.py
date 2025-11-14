from fewspy.cache.manifest import Manifest
from typing import Optional
import threading
import xarray as xr
import pandas as pd
from pathlib import Path
import numpy as np
from datetime import datetime


class TimeSeriesCache:
    def __init__(self, manifest: Manifest, last_manifest_mtime: Optional[float] = None):
        self.manifest = manifest
        self.last_manifest_mtime: float | None = last_manifest_mtime
        self._lock = threading.RLock()
        self._datasets: dict[str, xr.Dataset] = {}
        self._common_time_axis: pd.DatetimeIndex | None = None
        self._open_all()  #

    def _key_for(self, path: Path) -> str:
        return f"{path.parent.name}/{path.name}"

    def _get_open_ds(self, filter_id: str, parameter_id: str) -> xr.Dataset:
        entry = self.manifest.get_entry(filter_id=filter_id, parameter_id=parameter_id)
        key = self._key_for(entry.path)
        with self._lock:
            ds = self._datasets.get(key)
        if ds is None:
            # Fallback if not cached
            entry = self.manifest.get_entry(
                filter_id=filter_id, parameter_id=parameter_id
            )
            ds = xr.open_dataset(
                entry.path,
                engine="netcdf4",
                decode_times=True,
                mask_and_scale=True,
                cache=False,
            )
        return ds

    def _open_all(self):
        """Open all datasets and close old datasets"""
        new = {}
        for entry in self.manifest.files:
            key = self._key_for(entry.path)
            dataset = xr.open_dataset(
                entry.path,
                engine="netcdf4",
                decode_times=True,
                mask_and_scale=True,
                cache=False,
            )
            new[key] = dataset
        with self._lock:
            old = self._datasets
            self._datasets = new
        for dataset in old.values():
            try:
                dataset.close()
            except:
                pass

    @property
    def common_time_axis(self) -> pd.DatetimeIndex:
        if not self._datasets:
            raise ValueError(
                "No NetCDF DataSets open in cache. Check manifest-file and run self._open_all()"
            )

        if self._common_time_axis is None:
            # init idx_all
            idx_all: pd.DatetimeIndex | None = None

            # union all time-axis to idx_all
            for dataset in self._datasets.values():
                idx = pd.to_datetime(dataset["time"].values)

                if idx_all is None:
                    idx_all = idx
                else:
                    idx_all = idx_all.union(idx)

            if idx_all is not None:
                self._common_time_axis = idx_all.sort_values()
        return self._common_time_axis

    @classmethod
    def _decode_station_ids(cls, sid: xr.DataArray) -> np.ndarray:
        """
        Retourneert een 1D numpy array met dtype 'U' (unicode) zonder Python-loop.
        Werkt voor:
        - fixed-width bytes: dtype.kind == 'S'
        - unicode strings:   dtype.kind == 'U'
        - object arrays met mix van bytes/str: dtype.kind == 'O'
        """
        vals = sid.values

        # Case 1: fixed-width bytes (b'...') -> vectorized decode
        if vals.dtype.kind == "S":  # e.g. dtype('S20')
            return np.char.decode(vals, "utf-8", "replace")

        # Case 2: al unicode
        if vals.dtype.kind == "U":
            return vals

        # Case 3: object array met mix bytes/str
        if vals.dtype.kind == "O":
            obj = vals
            # mask voor bytes
            is_bytes = np.frompyfunc(lambda x: isinstance(x, (bytes, bytearray)), 1, 1)(
                obj
            ).astype(bool)

            out = np.empty(obj.shape, dtype=object)
            if is_bytes.any():
                # Alleen de bytes-subset in één keer decoden
                out[is_bytes] = np.char.decode(
                    obj[is_bytes].astype("S"), "utf-8", "replace"
                )
            if (~is_bytes).any():
                # Niet-bytes naar str (no-op voor str, netjes voor ints e.d.)
                out[~is_bytes] = obj[~is_bytes].astype(str)
            return out.astype("U")

        # Fallback: veilig naar unicode casten
        return vals.astype("U")

    @classmethod
    def from_manifest_file(cls, path: Path):
        manifest = Manifest.from_file(path)
        manifest.validate_files()
        return cls(manifest=manifest, last_manifest_mtime=path.stat().st_mtime)

    def refresh_if_changed(self, manifest_path: Path) -> bool:
        """Swap DataSets if manifest_json has changed

        Args:
            manifest_path (Path): Path to manifest.json

        Returns:
            bool: True if swapped, else False
        """
        mtime = manifest_path.stat().st_mtime
        if mtime == self.last_manifest_mtime:
            return False
        # read new manifest and validate
        new_manifest = Manifest.from_file(manifest_path)
        try:
            # mount new manifest file
            new_manifest.validate_files()
            self.manifest = new_manifest
            self.last_manifest_mtime = mtime

            # swap to new netcdfs and close old
            self._open_all()

            # reset derived arguments so they will be re-computed
            self._common_time_axis = None
            return True
        except ValueError:  # in case new manifest returns invalid files
            return False

    def get_time_series(
        self,
        filter_id: str,
        parameter_id: str,
        start_time: Optional[datetime | str] = None,
        end_time: Optional[datetime | str] = None,
        location_ids: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """fetch time series data from NetCDF file based on filter_id and parameter_id

        Args:
            filter_id (str): filter_id
            parameter_id (str): parameter_id
            start_time (Optional[datetime  |  str], optional): start_time Defaults to None.
            end_time (Optional[datetime  |  str], optional): end_time. Defaults to None.
            location_ids (Optional[list[str]], optional): location_ids. Defaults to None.

        Returns:
            pd.DataFrame: DataFrame with datetime index and MultiIndex columns (location_id, parameter_id)
        """
        dataset = self._get_open_ds(filter_id=filter_id, parameter_id=parameter_id)
        da = dataset[parameter_id]

        if "stations" in da.dims and "station_id" in dataset.variables:
            # swap station index for station_id values
            # TODO: bij chache een optie inbouwen om station_ids al als location_id (string) op te slaan
            # TODO: bij cache een optie inbouwen om station_ids te gebruiken i.p.v. stations index
            station_ids = self._decode_station_ids(dataset["station_id"])
            da = da.assign_coords(station_id=("stations", station_ids))
            da = da.swap_dims({"stations": "station_id"})

        # Slice time and location_ids
        slicer = {}
        if (start_time is not None) | (end_time is not None):
            slicer["time"] = slice(start_time, end_time)
        if location_ids is not None:
            slicer["station_id"] = location_ids
        if slicer:
            da = da.sel(**slicer)

        s = da.to_series()
        if "station_id" in s.index.names:
            df = s.unstack("station_id")
        else:
            df = s.unstack("stations")
            df.columns = df.columns.astype(str)

        # MultiIndex-kolommen (station_id, parameter_id)
        df.columns = pd.MultiIndex.from_arrays(
            [df.columns, [parameter_id] * len(df.columns)],
            names=["location_id", "parameter_id"],
        )

        # sort indices
        df.sort_index(inplace=True)
        df.index.name = "datetime"
        df.sort_index(inplace=True, axis=1)

        return df
