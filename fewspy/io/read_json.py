from fewspy.time_series import TimeSeriesSet
from pathlib import Path
import json


def read_json(json_path: Path) -> TimeSeriesSet:
    """Read the content of a JSON file into a fewspy TimeSeriesSet

    Args:
        json_path (Path): path to PI_JSON file

    Returns:
        TimeSeriesSet: timeseries
    """
    return TimeSeriesSet.from_dict(json.loads(Path(json_path).read_text()))
