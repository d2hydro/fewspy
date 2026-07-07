import requests
import logging
from typing import List
from ..utils.timer import Timer
from ..utils.transformations import parameters_to_fews

LOGGER = logging.getLogger(__name__)


def get_filters(
    url: str,
    filter_id: str = None,
    document_format: str = "PI_JSON",
    verify: bool = False,
    http_headers: dict = None,
    logger=LOGGER,
    headers: dict = None,
) -> List[dict]:
    """
    Get FEWS qualifiers as a pandas DataFrame

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/filters
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
    response = requests.get(url, parameters, verify=verify, headers=http_headers)
    timer.report("Filters request")

    # parse the response
    result = []
    if response.status_code == 200:
        if "filters" in response.json().keys():
            result = response.json()["filters"]
        timer.report("Filters parsed")
    else:
        logger.error(f"FEWS Server responds {response.text}")

    return result
