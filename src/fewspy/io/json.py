from fewspy.time_series import TimeSeriesSet
from pathlib import Path
import json


def read_json(xml_path: Path):
    return TimeSeriesSet.from_dict(json.loads(Path(xml_path).read_text()))
