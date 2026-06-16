from pathlib import Path
import json

DATA_PATH = Path(__file__).parent / "data"
FILTERS_JSON = DATA_PATH / "filters.json"
with open(FILTERS_JSON) as src:
    filter_reference = json.load(src)


def _write_reference_set(api):
    filters = api.get_filters()
    with open(FILTERS_JSON, "w+") as dst:
        dst.write(json.dumps(filters))


def test_to_reference_set(api):
    filters = api.get_filters()
    assert filter_reference == filters
