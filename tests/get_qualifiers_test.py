from pathlib import Path
import pandas as pd
from config import api


DATA_PATH = Path(__file__).parent / "data"
QUALIFIERS_CSV = DATA_PATH / "qualifiers.csv"
qualifiers_reference = pd.read_csv(QUALIFIERS_CSV).set_index("id")
qualifiers_reference.sort_index(inplace=True)


qualifiers = api.get_qualifiers()
qualifiers.sort_index(inplace=True)


def write_reference_set():
    qualifiers.to_csv(QUALIFIERS_CSV)


def test_to_refrence_set():
    all(qualifiers.index == qualifiers_reference.index)
    assert all(qualifiers.index == qualifiers_reference.index)
