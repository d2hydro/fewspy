import pandas as pd
from typing import List
from datetime import datetime
from dataclasses import dataclass
from .utils.conversions import camel_to_snake_case, dict_to_datetime
from .utils.transformations import flatten_list


DATETIME_KEYS = ["start_date", "end_date"]
FLOAT_KEYS = ["miss_val", "lat", "lon", "x", "y", "z"]
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
    module_instance_id: str
    location_id: str
    parameter_id: str
    time_step: dict
    start_date: datetime
    end_date: datetime
    miss_val: float
    lat: float
    lon: float
    x: float
    y: float
    units: str
    station_name: str = None
    z: float = None
    qualifier_id: List[str] = None

    @classmethod
    def from_pi_header(cls, pi_header: dict):
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
            return k, v

        args = (_convert_kv(k, v) for k, v in pi_header.items())
        return cls(**{i[0]: i[1] for i in args})


class Events(pd.DataFrame):
    """FEWS-PI events in pandas DataFrame"""

    @classmethod
    def from_pi_events(
        cls, pi_events: list, missing_value: float, tz_offset: float = None
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
            df["datetime"] = (
                pd.to_datetime(df["date"])
                + pd.to_timedelta(df["time"])
                - pd.Timedelta(hours=tz_offset)
            )
        else:
            df["datetime"] = pd.to_datetime(df["date"]) + pd.to_timedelta(df["time"])

        # set value to numeric and remove missings
        df["value"] = pd.to_numeric(df["value"])
        df = df.loc[df["value"] != missing_value]

        # drop columns and add missing columns
        drop_cols = [i for i in df.columns if i not in EVENT_COLUMNS]
        df.drop(columns=drop_cols, inplace=True)
        for i in EVENT_COLUMNS:
            if i not in df.columns:
                df[i] = pd.NA

        # set flag to numeric
        df["flag"] = pd.to_numeric(df["flag"])

        # set datetime to index
        df.set_index("datetime", inplace=True)

        return df


@dataclass
class TimeSeries:
    """FEWS-PI time series"""

    header: Header
    events: Events = pd.DataFrame(columns=EVENT_COLUMNS).set_index("datetime")

    @classmethod
    def from_pi_time_series(cls, pi_time_series: dict, time_zone: float = None):
        # print(pi_time_series)
        header = Header.from_pi_header(pi_time_series["header"])
        kwargs = dict(header=header)
        if "events" in pi_time_series.keys():
            kwargs["events"] = Events.from_pi_events(
                pi_time_series["events"], header.miss_val, time_zone
            )
        return cls(**kwargs)


@dataclass
class TimeSeriesSet:
    version: str = None
    time_zone: float = None
    time_series: List[TimeSeries] = list
    empty: bool = True

    def __len__(self):
        return len(self.time_series)

    @classmethod
    def from_pi_time_series(cls, pi_time_series_set: dict):
        kwargs = {}
        if "version" in pi_time_series_set.keys():
            kwargs["version"] = pi_time_series_set["version"]
        if "timeZone" in pi_time_series_set.keys():
            time_zone = float(pi_time_series_set["timeZone"])
            kwargs["time_zone"] = time_zone
        if "timeSeries" in pi_time_series_set.keys():
            kwargs["time_series"] = [
                TimeSeries.from_pi_time_series(i, time_zone)
                for i in pi_time_series_set["timeSeries"]
            ]
            if len(kwargs["time_series"]) > 0:
                kwargs["empty"] = False
        return cls(**kwargs)

    def add(self, time_series_set):
        # add time_series_set to the time_series_set
        return self

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
