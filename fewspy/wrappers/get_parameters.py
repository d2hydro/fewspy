import requests
import logging
import pandas as pd
from typing import List, Optional, Tuple, Union
from ..utils.timer import Timer
from ..utils.transformations import parameters_to_fews
from ..utils.conversions import camel_to_snake_case

LOGGER = logging.getLogger(__name__)
COLUMNS = [
    "id",
    "name",
    "parameter_type",
    "unit",
    "display_unit",
    "uses_datum",
    "parameter_group",
]


def get_parameters(
    url: str,
    filter_id: str = None,
    document_format: str = "PI_JSON",
    verify: bool = False,
    cert: Optional[Union[str, Tuple[str, str]]] = None,
    http_headers: dict = None,
    logger=LOGGER,
    headers: dict = None,
) -> List[dict]:
    """
    Get FEWS qualifiers as a pandas DataFrame

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
        filter_id (str): the FEWS id of the filter to pass as request parameter
        document_format (str): request document format to return. Defaults to PI_JSON.
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default, a logger will ge created.

    Returns:
        df (pandas.DataFrame): Pandas dataframe with index "id" and columns
        "name" and "group_id".

    """

    # do the request
    timer = Timer(logger)
    if (http_headers is not None) and (headers is not None):
        raise ValueError("Use either http_headers or headers, not both")
    if http_headers is None:
        http_headers = headers
    parameters = parameters_to_fews(locals())
    response = requests.get(
        url,
        parameters,
        verify=verify,
        cert=cert,
        headers=http_headers,
    )
    timer.report("Parameters request")

    # parse the response
    df = pd.DataFrame(columns=COLUMNS)
    if response.status_code == 200:
        if "timeSeriesParameters" in response.json().keys():
            df = pd.DataFrame(response.json()["timeSeriesParameters"])
            df.columns = [camel_to_snake_case(i) for i in df.columns]
            df["uses_datum"] = df["uses_datum"] == "true"
            timer.report("Parameters parsed")
    else:
        logger.error(f"FEWS Server responds {response.text}")

    df.set_index("id", inplace=True)

    return df
