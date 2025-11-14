# %%
from fewspy.time_series import TimeSeriesSet, Header, TimeSeries
from pathlib import Path
import pandas as pd
from fewspy.io.header_file import get_header_file


def _row_to_header(row):
    d = row.to_dict()
    header = d.copy()
    header["time_step"] = {
        "unit": header.pop("time_step.unit"),
        "multiplier": header.pop("time_step.multiplier"),
    }
    return Header(**header)


def _column_to_time_series(df, column):
    df = pd.DataFrame(df[column])
    df.columns = ["value"]
    return df


def read_parquet(parquet_file: Path) -> TimeSeriesSet:
    """Parse parquet file to fewspy TimeSeriesSet

    Args:
        parquet_file (Path): path to parquet-file

    Returns:
        TimeSeriesSet: timeseries
    """
    # header to list of dict
    header_df = pd.read_parquet(get_header_file(parquet_file))
    header_df.set_index(["location_id", "parameter_id"], drop=False, inplace=True)
    header_series = header_df.apply(_row_to_header, axis=1)

    # read timeseries
    df = pd.read_parquet(parquet_file, engine="pyarrow")

    time_series_set = TimeSeriesSet()

    time_series_set.time_series = [
        TimeSeries(
            header=i,
            events=_column_to_time_series(df, (i.location_id, i.parameter_id)),
        )
        for i in header_series
    ]

    return time_series_set
