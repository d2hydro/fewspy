import requests
import logging
from typing import List
from ..utils.timer import Timer
from ..utils.transformations import parameters_to_fews

LOGGER = logging.getLogger(__name__)


def get_timezone_id(
    url: str,
    filter_id: str = None,
    document_format: str = "PI_JSON",
    verify: bool = False,
    logger=LOGGER,
) -> List[dict]:
    """
    Get FEWS timezone id

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/timezoneid
        filter_id (str): the FEWS id of the filter to pass as request parameter
        document_format (str): request document format to return. Defaults to PI_JSON.
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default, a logger will ge created.

    Returns:
        something undefined

    """

    # do the request
    timer = Timer(logger)
    parameters = parameters_to_fews(locals())
    response = requests.get(url, parameters, verify=verify)
    timer.report("Timezone request")

    # parse the response
    if response.status_code == 200:
        if "filters" in response.json().keys():
            result = response.json()
        timer.report("Timezone parsed")
    else:
        logger.error(f"FEWS Server responds {response.text}")

    return result
