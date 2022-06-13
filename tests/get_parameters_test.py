import pandas as pd
from pathlib import Path
from config import api

DATA_PATH = Path(__file__).parent / "data"

parameters_reference = pd.read_csv(DATA_PATH / "parameters.csv").set_index("id")
parameters = api.get_parameters()


def test_to_refrence_set():
    assert parameters.sort_index().equals(parameters_reference.sort_index())
