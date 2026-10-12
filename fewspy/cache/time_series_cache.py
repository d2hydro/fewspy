import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from netCDF4 import Dataset

from fewspy.cache._header_reader import HeaderMetadata, read_metadata, read_selection, select_positions
from fewspy.cache.manifest import Manifest
from fewspy.io.read_netcdf import read_netcdf
from fewspy.time_series import SeriesKey, TimeSeriesSet

# netCDF4/HDF5 access is serialized across cache instances, including xarray.
# Do not hold the state lock while acquiring this lock.
_NETCDF_LOCK = threading.RLock()


@dataclass(eq=False)
class _Snapshot:
    manifest: Manifest
    parameters: dict[Path, str | None]
    common_time_axis: pd.DatetimeIndex | None = None


class TimeSeriesCache:
    def __init__(
        self,
        manifest: Manifest,
        last_manifest_mtime: float | None = None,
        *,
        metadata_cache_size: int = 16,
    ):
        """Read immutable cache generations with bounded full-header metadata reuse.

        metadata_cache_size bounds retained file entries, not bytes. Zero disables
        reuse. Active reads may retain evicted metadata until they finish.
        Construction reads routing attributes only. Content decoding checks run
        on first use of each file, before any selected data are returned.
        """
        if isinstance(metadata_cache_size, bool) or not isinstance(metadata_cache_size, int) or metadata_cache_size < 0:
            raise ValueError("metadata_cache_size must be a non-negative integer")
        self._lock = threading.RLock()
        self._refresh_lock = threading.Lock()
        self._closed = False
        self._metadata_cache_size = metadata_cache_size
        self._metadata: OrderedDict[tuple[_Snapshot, Path], HeaderMetadata] = OrderedDict()
        self._snapshot = self._prepare_snapshot(manifest)
        self.manifest = manifest
        self.last_manifest_mtime = last_manifest_mtime

    @staticmethod
    def _open_dataset(path):
        return xr.open_dataset(path, engine="netcdf4", decode_times=True, mask_and_scale=True, cache=False)

    def _prepare_snapshot(self, manifest: Manifest) -> _Snapshot:
        """Capture routing attributes; defer content decoding until a file is used."""
        manifest = manifest.model_copy(deep=True)
        parameters = {}
        for entry in manifest.files:
            with _NETCDF_LOCK, Dataset(entry.path, mode="r") as dataset:
                parameters[entry.path] = getattr(dataset, "parameter_id", None)
        return _Snapshot(manifest, parameters)

    def _acquire_snapshot(self):
        with self._lock:
            if self._closed:
                raise RuntimeError("TimeSeriesCache is closed")
            return self._snapshot

    def close(self):
        """Release retained metadata; active reads finish on their own snapshot.

        This operation is idempotent and does not wait for active reads. Each
        reader closes its file handles before returning, including on errors.
        """
        with self._lock:
            self._closed = True
            self._metadata.clear()
            self._snapshot = None

    def __enter__(self):
        self._acquire_snapshot()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def common_time_axis(self) -> pd.DatetimeIndex:
        snapshot = self._acquire_snapshot()
        with self._lock:
            cached = snapshot.common_time_axis
        if cached is not None:
            return cached.copy(deep=True)
        if not snapshot.manifest.files:
            raise ValueError("No NetCDF DataSets open in cache. Check manifest-file and run self._open_all()")
        index = None
        for entry in snapshot.manifest.files:
            with _NETCDF_LOCK, self._open_dataset(entry.path) as dataset:
                current = pd.to_datetime(dataset["time"].values)
            index = current if index is None else index.union(current)
        index = index.sort_values()
        with self._lock:
            snapshot.common_time_axis = index
        return index.copy(deep=True)

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
            is_bytes = np.frompyfunc(lambda x: isinstance(x, (bytes, bytearray)), 1, 1)(obj).astype(bool)

            out = np.empty(obj.shape, dtype=object)
            if is_bytes.any():
                # Alleen de bytes-subset in één keer decoden
                out[is_bytes] = np.char.decode(obj[is_bytes].astype("S"), "utf-8", "replace")
            if (~is_bytes).any():
                # Niet-bytes naar str (no-op voor str, netjes voor ints e.d.)
                out[~is_bytes] = obj[~is_bytes].astype(str)
            return out.astype("U")

        # Fallback: veilig naar unicode casten
        return vals.astype("U")

    @classmethod
    def from_manifest_file(cls, path: Path, *, metadata_cache_size: int = 16):
        # Capture mtime before reading, so a concurrent publication is noticed
        # on the next refresh instead of marking the older content as current.
        mtime = path.stat().st_mtime
        manifest = Manifest.from_file(path)
        manifest.validate_files()
        return cls(manifest, mtime, metadata_cache_size=metadata_cache_size)

    def refresh_if_changed(self, manifest_path: Path) -> bool:
        """Validate and atomically publish a new snapshot when mtime changes.

        Publishers must retain immutable old files until their readers finish.
        Failed publication checks leave the previous snapshot intact. Content
        decoding errors are deferred to reads of the newly published files.
        """
        # Prevent concurrent refreshes from publishing generations out of order.
        with self._refresh_lock:
            self._acquire_snapshot()
            mtime = manifest_path.stat().st_mtime
            if mtime == self.last_manifest_mtime:
                return False
            new_manifest = Manifest.from_file(manifest_path)
            try:
                new_manifest.validate_files()
                snapshot = self._prepare_snapshot(new_manifest)
            except ValueError:
                return False
            with self._lock:
                if self._closed:
                    raise RuntimeError("TimeSeriesCache is closed")
                self._snapshot = snapshot
                self.manifest = new_manifest
                self.last_manifest_mtime = mtime
                self._metadata.clear()
            return True

    def _get_metadata(
        self, snapshot: _Snapshot, path: Path, dataset: Dataset, location_ids: list[str] | None
    ) -> HeaderMetadata:
        """Reuse headers and decode the file before any matching values are read."""
        key = (snapshot, path)
        with self._lock:
            metadata = self._metadata.get(key)
        if metadata is None:
            metadata = read_metadata(dataset)
        # Header inspection can rule out a file without returning its data.
        # A later selection must still decode it before using cached metadata.
        needs_values = location_ids is None or any(location in metadata.locations for location in location_ids)
        if not metadata.decoded and (needs_values or not metadata.selective):
            # Check every variable, including those outside the selection.
            with self._open_dataset(path):
                pass
            metadata.decoded = True
        with self._lock:
            # Old/closed readers can finish but must not repopulate this cache.
            if not self._closed and snapshot is self._snapshot and self._metadata_cache_size:
                self._metadata[key] = metadata
                self._metadata.move_to_end(key)
                while len(self._metadata) > self._metadata_cache_size:
                    self._metadata.popitem(last=False)
        return metadata

    def _read_header_file(self, snapshot, path, start_time, end_time, location_ids):
        with _NETCDF_LOCK, Dataset(path, mode="r") as dataset:
            metadata = self._get_metadata(snapshot, path, dataset, location_ids)
            if not metadata.selective:
                return None
            positions = select_positions(metadata, location_ids)
            if not len(positions):
                return TimeSeriesSet()
            time_slice = metadata.time.slice_indexer(start_time, end_time)
            return read_selection(dataset, metadata, positions, time_slice)

    @classmethod
    def _read_header_fallback(cls, paths: list[Path], location_ids: list[str] | None) -> TimeSeriesSet:
        """Retain complete decoding checks for every file in the fallback read."""
        result = TimeSeriesSet()
        for path in paths:
            # A fallback can skip the selective reader for later files. Those
            # files must still pass all decoding checks before returning data.
            with _NETCDF_LOCK, cls._open_dataset(path):
                part = read_netcdf(path, series_key=SeriesKey.HEADER)
            result.time_series.extend(
                ts for ts in part.time_series if location_ids is None or ts.header.location_id in location_ids
            )
        return result

    def get_time_series(
        self,
        filter_id: str,
        parameter_id: str,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        location_ids: list[str] | None = None,
        series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER,
    ) -> pd.DataFrame:
        """Read locations and an inclusive time interval from one cache snapshot.

        Header mode preserves all seven identity fields and original headers.
        The default location_parameter mode retains its existing selection rules.
        Both enum and string modes and partial-date bounds are supported.
        """
        series_key = SeriesKey(series_key)
        snapshot = self._acquire_snapshot()
        if series_key == SeriesKey.HEADER:
            paths = [
                entry.path
                for entry in snapshot.manifest.files
                if entry.path.parent.name == filter_id and snapshot.parameters[entry.path] == parameter_id
            ]
            result = TimeSeriesSet()
            for path in paths:
                part = self._read_header_file(snapshot, path, start_time, end_time, location_ids)
                if part is None:
                    # Preserve concat-then-slice semantics for unusual time axes
                    # across the entire result, not just this individual file.
                    result = self._read_header_fallback(paths, location_ids)
                    break
                result.time_series.extend(part.time_series)
            if not result.time_series:
                raise ValueError("No full-header series match the cache selection")
            return result.to_df(series_key=SeriesKey.HEADER).loc[start_time:end_time]

        entry = snapshot.manifest.get_entry(filter_id=filter_id, parameter_id=parameter_id)
        with _NETCDF_LOCK, self._open_dataset(entry.path) as dataset:
            return self._read_location_parameter(dataset, parameter_id, start_time, end_time, location_ids)

    def _read_location_parameter(self, dataset, parameter_id, start_time, end_time, location_ids):
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
