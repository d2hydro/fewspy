from pathlib import Path
import pandas as pd
from config import api


DATA_PATH = Path(__file__).parent / "data"

qualifiers_reference = pd.read_csv(DATA_PATH / "qualifiers.csv").set_index("id")
qualifiers = api.get_qualifiers()


def test_to_refrence_set():
    assert qualifiers.sort_index().equals(qualifiers_reference.sort_index())
