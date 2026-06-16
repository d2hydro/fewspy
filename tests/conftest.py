import pytest

from fewspy import Api
from config import DATA_DIR, FEWS_API_URL


@pytest.fixture(scope="session")
def api():
    return Api(url=FEWS_API_URL, ssl_verify=False)


@pytest.fixture(scope="session")
def data_dir():
    return DATA_DIR
