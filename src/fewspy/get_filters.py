import requests
import logging
from typing import List
from .utils.timer import Timer
from .utils.transformations import parameters_to_fews

LOGGER = logging.getLogger(__name__)


def get_filters(
    url: str,
    filter_id: str = None,
    document_format: str = "PI_JSON",
    verify: bool = False,
    logger=LOGGER,
) -> List[dict]:
    """
    Get FEWS qualifiers as a pandas DataFrame

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default a logger will ge created.

    Returns:
        df (pandas.DataFrame): Pandas dataframe with index "id" and columns
        "name" and "group_id".

    """

    # do the request
    timer = Timer(logger)
    parameters = parameters_to_fews(locals())
    response = requests.get(url, parameters, verify=verify)
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
