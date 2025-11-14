from fewspy import Api
from pathlib import Path

api = Api(
    url=r"https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1/",
    ssl_verify=False,
)

data_dir = Path(__file__).parent / "data"
