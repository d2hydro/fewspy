from pathlib import Path
import json
from config import api

DATA_PATH = Path(__file__).parent / "data"
FILTERS_JSON = DATA_PATH / "filters.json"
with open(FILTERS_JSON) as src:
    filter_reference = json.load(src)
filters = api.get_filters()


def _write_reference_set():
    with open(FILTERS_JSON, "w+") as dst:
        dst.write(json.dumps(filters))


def test_to_reference_set():
    assert filter_reference == filters
