import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data"
PARAMETERS_CSV = DATA_PATH / "parameters.csv"
parameters_reference = pd.read_csv(PARAMETERS_CSV).set_index("id")


def _write_reference_set(api):
    parameters = api.get_parameters()
    parameters.to_csv(PARAMETERS_CSV)


def test_to_refrence_set(api):
    parameters = api.get_parameters()
    assert parameters.sort_index().equals(parameters_reference.sort_index())
