import warnings
from dataclasses import field
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

# Re-export header types and helpers to preserve existing import paths.
from fewspy._header import (
    DATETIME_KEYS as DATETIME_KEYS,
    FLOAT_KEYS as FLOAT_KEYS,
    HEADER_KEY_FIELDS as HEADER_KEY_FIELDS,
    STRING_KEYS as STRING_KEYS,
    Header as Header,
    SeriesKey as SeriesKey,
    TimeStepDict as TimeStepDict,
    canonical_json as canonical_json,
)
from fewspy.io.header_file import get_header_file
from fewspy.io.write_netcdf import _validate_file_naming, write_netcdf
from fewspy.utils.transformations import flatten_list

EVENT_COLUMNS = ["datetime", "value", "flag"]


def reliables(df: pd.DataFrame, threshold: int = 6) -> pd.DataFrame:
    """
    Filters reliables from an Events type Pandas DataFrame

    Args:
        df (pd.DataFrame): input Events-type Pandas Dataframe
        threshold (int, optional): threshold for unreleables. Defaults to 6.

    Returns
    -------
        pd.DataFrame: Pandas DataFrame with reliable data only

    """
    if "flag" not in df.columns:
        return df
    else:
        return df.loc[df["flag"] < threshold]


class Events(pd.DataFrame):
    """FEWS-PI events in pandas DataFrame"""

    @classmethod
    def from_pi_events(
        cls,
        pi_events: list,
        missing_value: float | None = None,
        tz_offset: float | None = None,
    ) -> pd.DataFrame:
        warnings.warn("from_pi_events is deprecated, use from_dict instead.", DeprecationWarning, stacklevel=1)
        return cls.from_dict(pi_events=pi_events, missing_value=missing_value, tz_offset=tz_offset)

    @classmethod
    def from_dict(
        cls,
        pi_events: list,
        missing_value: float | None = None,
        tz_offset: float | None = None,
    ) -> pd.DataFrame:
        """
        Parse Events from FEWS PI events dict.

        Args:
            pi_events (dict): FEWS PI events as dictionary

        Returns
        -------
            Events: pandas DataFrame

        """
        df = cls(pi_events)

        if df.empty:
            return pd.DataFrame(columns=EVENT_COLUMNS).set_index("datetime")

        # set datetime
        if tz_offset is not None:
            df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"]) - pd.Timedelta(hours=tz_offset)
        else:
            df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"])

        # drop columns and add missing columns
        drop_cols = [i for i in df.columns if i not in EVENT_COLUMNS]
        df.drop(columns=drop_cols, inplace=True)

        # set numeric types
        if "flag" not in df.columns:
            df["flag"] = pd.Series(dtype="int")
        else:
            df["flag"] = df["flag"].astype("int")

        df["value"] = pd.to_numeric(df["value"], downcast="float")

        # remove missings (if specified)
        if missing_value is not None:
            df = df.loc[df["value"] != missing_value]

        # set datetime to index
        df.set_index("datetime", inplace=True)

        return df


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class TimeSeries:
    """FEWS-PI time series"""

    header: Header
    events: Events | pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(columns=EVENT_COLUMNS).set_index("datetime")
    )

    def __len__(self):
        return len(self.events)

    @classmethod
    def from_pi_time_series(cls, pi_time_series: dict, time_zone: float | None = None):
        warnings.warn(
            "from_pi_time_series is deprecated, use from_dict instead.",
            DeprecationWarning,
            stacklevel=1,
        )
        return cls.from_dict(pi_time_series=pi_time_series, time_zone=time_zone)

    @classmethod
    def from_dict(cls, pi_time_series: dict, time_zone: float | None = None):
        """Parse TimeSeries from FEWS PI timeseries dict.

        Args:
            pi_time_series (dict): FEWS PI timeseries as dictionary
            time_zone (float, optional): time_zone. Defaults to None.

        Returns
        -------
            fewspy.TimeSeries: time series in FEWS PI format
        """
        header = Header.from_dict(pi_time_series["header"])
        kwargs = {"header": header}
        if "events" in pi_time_series:
            kwargs["events"] = Events.from_dict(pi_time_series["events"], header.miss_val, time_zone)
        return cls(**kwargs)


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class TimeSeriesSet:
    """FEWS-PI time series set"""

    version: str | None = None
    time_zone: float | None = None
    time_series: list[TimeSeries] = field(default_factory=list)

    def __len__(self):
        return len(self.time_series)

    @classmethod
    def from_pi_time_series(cls, pi_time_series_set):
        warnings.warn(
            "from_pi_time_series is deprecated, use from_dict instead.",
            DeprecationWarning,
            stacklevel=1,
        )
        return cls.from_dict(pi_time_series_set)

    @classmethod
    def from_dict(cls, pi_time_series_set: dict):
        """Parse TimeSeries from FEWS PI time series set dict.

        Args:
            pi_time_series_set (dict): FEWS PI time series set as dictionary

        Returns
        -------
            fewspy.TimeSeriesSet: Time series set with multiple time series
        """
        kwargs = {}
        if "version" in pi_time_series_set:
            kwargs["version"] = pi_time_series_set["version"]
        if "timeZone" in pi_time_series_set:
            time_zone = float(pi_time_series_set["timeZone"])
            kwargs["time_zone"] = time_zone
        else:
            time_zone = None
        if "timeSeries" in pi_time_series_set:
            kwargs["time_series"] = [TimeSeries.from_dict(i, time_zone) for i in pi_time_series_set["timeSeries"]]
        return cls(**kwargs)

    def add(self, time_series_set):
        # add time_series to the time_series_set
        self.time_series += [time_series_set]
        return self

    @property
    def empty(self):
        return all(i.events.empty for i in self.time_series)

    @property
    def parameter_ids(self):
        return list({i.header.parameter_id for i in self.time_series})

    @property
    def location_ids(self):
        return list({i.header.location_id for i in self.time_series})

    @property
    def qualifier_ids(self):
        qualifiers = (i.header.qualifier_id for i in self.time_series)
        qualifiers = [i for i in qualifiers if i is not None]

        return list(set(flatten_list(qualifiers)))

    def to_df(self, series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER) -> pd.DataFrame:
        """Reliable values with location/parameter columns or seven header levels.

        Header mode stores complete headers in DataFrame.attrs for I/O. Timestep
        and qualifier levels are canonical JSON strings; no hashes are used.
        """
        series_key = SeriesKey(series_key)
        columns = pd.MultiIndex.from_tuples(
            [i.header.series_identity(series_key) for i in self.time_series],
            names=(HEADER_KEY_FIELDS if series_key == SeriesKey.HEADER else ["location_id", "parameter_id"]),
        )
        if series_key == SeriesKey.HEADER and not self.time_series:
            df = pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], name="datetime"))
            df.attrs["fewspy_headers"] = []
            return df
        df = pd.concat(
            [reliables(i.events)["value"] for i in self.time_series],
            axis=1,
            sort=True,
        )
        df.columns = columns

        if series_key == SeriesKey.HEADER:
            df.attrs["fewspy_headers"] = [i.header.to_json() for i in self.time_series]
        return df

    def to_netcdf(
        self,
        out_dir: Path,
        global_attributes: dict = {"source": "fewspy"},  # noqa: B006 - Preserve the existing read-only API default.
        file_template: str = "{parameter_id}.nc",
        remove_dir: bool = False,
        series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER,
        file_naming: Literal["default", "archive"] = "default",
        include_time_series_type: bool = False,
    ) -> None:
        """Write fewspy.TimeSeriesSet to netCDF files, one per parameter_id.

        Args:
            out_dir (Path): Directory to save NetCDF files.
            global_attributes (dict, optional): Global attributes for the NetCDF files. Defaults to {"source": "fewspy"}.
            file_template (str, optional): Template for naming the NetCDF files. Defaults to "{parameter_id}.nc".
            remove_dir (bool, optional): If True, removes the output directory before writing. Defaults to False.
            series_key: "location_parameter" (default) or "header". Header mode
                groups matching identities across locations and uses archive-style
                filenames. Custom templates can use {identity}.
            file_naming: "default" preserves existing names; "archive" uses readable
                names and requires series_key="header".
            include_time_series_type: Append the full type to archive names when known.
                Missing value_type and time_series_type are omitted from archive names.
        """
        series_key = SeriesKey(series_key)
        _validate_file_naming(series_key, file_naming, include_time_series_type)
        if not self.empty or (series_key == SeriesKey.HEADER and self.time_series):
            df = self.to_df(series_key=series_key)

            write_netcdf(
                df=df,
                out_dir=out_dir,
                global_attributes=global_attributes,
                file_template=file_template,
                remove_dir=remove_dir,
                series_key=series_key,
                file_naming=file_naming,
                include_time_series_type=include_time_series_type,
            )

    def to_parquet(
        self,
        parquet_file: Path,
        include_header: bool = False,
        series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER,
    ):
        """Write fewspy.TimeSeriesSet to arrow parquet file

        Args:
            parquet_file (Path): parquet-file to store
            include_header (bool, optional): if true all headers will be stored as a parquet-file next to the timeseries. Defaults to False.
            series_key: "location_parameter" (default) or "header". Header mode
                always embeds complete headers in the event file's metadata.
        """
        series_key = SeriesKey(series_key)
        # make dir-structure to file(s)
        parquet_file.parent.mkdir(exist_ok=True, parents=True)
        parquet_file.unlink(missing_ok=True)

        # concat events to one dataframe and write to parquet
        df = self.to_df(series_key=series_key)
        if series_key == SeriesKey.HEADER:
            # Parquet cannot reliably encode nested MultiIndex levels. Keep the
            # complete headers in pandas metadata and use positional columns.
            df.columns = [str(i) for i in range(len(df.columns))]
        df.to_parquet(parquet_file, engine="pyarrow")

        # if include_header, write header_file
        if include_header:
            header_file = get_header_file(parquet_file)
            header_file.unlink(missing_ok=True)
            header_df = pd.DataFrame([i.header.to_row() for i in self.time_series])
            header_df.to_parquet(header_file, engine="pyarrow")
