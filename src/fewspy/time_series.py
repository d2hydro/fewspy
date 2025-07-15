import pandas as pd
from typing import List
from datetime import datetime
from dataclasses import dataclass, field
from .utils.conversions import camel_to_snake_case, dict_to_datetime
from .utils.transformations import flatten_list
import warnings


DATETIME_KEYS = ["start_date", "end_date"]
FLOAT_KEYS = ["miss_val", "lat", "lon", "x", "y", "z"]
STRING_KEYS = ["module_instance_id"]
EVENT_COLUMNS = ["datetime", "value", "flag"]


def reliables(df: pd.DataFrame, threshold: int = 6) -> pd.DataFrame:
    """
    Filters reliables from an Events type Pandas DataFrame

    Args:
        df (pd.DataFrame): input Events-type Pandas Dataframe
        threshold (int, optional): threshold for unreleables. Defaults to 6.

    Returns:
        pd.DataFrame: Pandas DataFrame with reliable data only

    """

    return df.loc[df["flag"] < threshold]


@dataclass
class Header:
    """FEWS-PI header-style dataclass"""

    type: str
    module_instance_id: str | None
    location_id: str
    parameter_id: str
    time_step: dict
    start_date: datetime
    end_date: datetime
    miss_val: float
    lat: float | None = None
    lon: float | None = None
    x: float | None = None
    y: float | None = None
    units: str | None = None
    station_name: str | None = None
    z: float | None = None
    qualifier_id: List[str] | None = None

    @classmethod
    def from_pi_header(cls, pi_header: dict):
        warnings.warn(
            "from_pi_header is depricated, use from_dict instead.", DeprecationWarning
        )
        return cls.from_dict(pi_header=pi_header)

    @classmethod
    def from_dict(cls, pi_header: dict):
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
            if k in FLOAT_KEYS:
                v = float(v)
            if k in STRING_KEYS:
                if v == "None":
                    v = None
                else:
                    str(v)
            return k, v

        args = (_convert_kv(k, v) for k, v in pi_header.items())
        return cls(**{i[0]: i[1] for i in args})


class Events(pd.DataFrame):
    """FEWS-PI events in pandas DataFrame"""

    @classmethod
    def from_pi_events(
        cls, pi_events: list, missing_value: float = None, tz_offset: float = None
    ):
        warnings.warn(
            "from_pi_events is deprecated, use from_dict instead.", DeprecationWarning
        )
        return cls.from_dict(
            pi_events=pi_events, missing_value=missing_value, tz_offset=tz_offset
        )

    @classmethod
    def from_dict(
        cls, pi_events: list, missing_value: float = None, tz_offset: float = None
    ):
        """
        Parse Events from FEWS PI events dict.

        Args:
            pi_events (dict): FEWS PI events as dictionary

        Returns:
            Events: pandas DataFrame

        """

        df = cls(pi_events)

        # set datetime
        if tz_offset is not None:
            df["datetime"] = pd.to_datetime(
                df["date"] + " " + df["time"]
            ) - pd.Timedelta(hours=tz_offset)
        else:
            df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"])

        # drop columns and add missing columns
        drop_cols = [i for i in df.columns if i not in EVENT_COLUMNS]
        df.drop(columns=drop_cols, inplace=True)

        # set numeric types
        if "flag" not in df.columns:
            df["flag"] = pd.Series(dtype="int")
        else:
            df.loc[:, ["flag"]] = df["flag"].astype("int")

        df.loc[:, "value"] = pd.to_numeric(df["value"])

        # remove missings (if specified)
        if missing_value is not None:
            df = df.loc[df["value"] != missing_value]

        # set datetime to index
        df.set_index("datetime", inplace=True)

        return df


@dataclass
class TimeSeries:
    """FEWS-PI time series"""

    header: Header
    events: Events = field(
        default_factory=lambda: pd.DataFrame(columns=EVENT_COLUMNS).set_index(
            "datetime"
        )
    )

    @classmethod
    def from_pi_time_series(cls, pi_time_series: dict, time_zone: float = None):
        warnings.warn(
            "from_pi_time_series is deprecated, use from_dict instead.",
            DeprecationWarning,
        )
        return cls.from_dict(pi_time_series=pi_time_series, time_zone=time_zone)

    @classmethod
    def from_dict(cls, pi_time_series: dict, time_zone: float = None):
        """Parse TimeSeries from FEWS PI timeseries dict.

        Args:
            pi_time_series (dict): FEWS PI timeseries as dictionary
            time_zone (float, optional): time_zone. Defaults to None.

        Returns:
            fewspy.TimeSeries: time series in FEWS PI format
        """
        header = Header.from_dict(pi_time_series["header"])
        kwargs = dict(header=header)
        if "events" in pi_time_series.keys():
            kwargs["events"] = Events.from_dict(
                pi_time_series["events"], header.miss_val, time_zone
            )
        return cls(**kwargs)


@dataclass
class TimeSeriesSet:
    """FEWS-PI time series set"""

    version: str = None
    time_zone: float = None
    time_series: List[TimeSeries] = field(default_factory=list)

    def __len__(self):
        return len(self.time_series)

    @classmethod
    def from_pi_time_series(cls, pi_time_series_set):
        warnings.warn(
            "from_pi_time_series is deprecated, use from_dict instead.",
            DeprecationWarning,
        )
        return cls.from_dict(pi_time_series_set)

    @classmethod
    def from_dict(cls, pi_time_series_set: dict):
        """Parse TimeSeries from FEWS PI time series set dict.

        Args:
            pi_time_series_set (dict): FEWS PI time series set as dictionary

        Returns:
            fewspy.TimeSeriesSet: Time series set with multiple time series
        """
        kwargs = {}
        if "version" in pi_time_series_set.keys():
            kwargs["version"] = pi_time_series_set["version"]
        if "timeZone" in pi_time_series_set.keys():
            time_zone = float(pi_time_series_set["timeZone"])
            kwargs["time_zone"] = time_zone
        else:
            time_zone = None
        if "timeSeries" in pi_time_series_set.keys():
            kwargs["time_series"] = [
                TimeSeries.from_dict(i, time_zone)
                for i in pi_time_series_set["timeSeries"]
            ]
        return cls(**kwargs)

    def add(self, time_series_set):
        # add time_series to the time_series_set
        self.time_series += [time_series_set]
        return self

    @property
    def empty(self):
        return all([i.events.empty for i in self.time_series])

    @property
    def parameter_ids(self):
        return list(set([i.header.parameter_id for i in self.time_series]))

    @property
    def location_ids(self):
        return list(set([i.header.location_id for i in self.time_series]))

    @property
    def qualifier_ids(self):
        qualifiers = (i.header.qualifier_id for i in self.time_series)
        qualifiers = [i for i in qualifiers if i is not None]

        return list(set(flatten_list(qualifiers)))
