import logging
from xml.etree import ElementTree

import pandas as pd
from typing import Optional, Tuple, Union
import requests

from ..utils.timer import Timer

NS = "{http://www.wldelft.nl/fews/PI}"
LOGGER = logging.getLogger(__name__)
COLUMNS = ["id", "name", "group_id"]


def _element_to_tuple(qualifier_element: ElementTree.Element) -> tuple:
    """
    Parses a qualifier element to a tuple

    Args:
        qualifier_element (xml.etree.ElementTree.Element): ET.Element with
        Delft-FEWS qualifier tags.

    Returns
    -------
        tuple: qualifier properties (id, name, group_id). If not present they
        will be None.

    """

    def __get_text(element):
        if element is not None:
            return element.text
        else:
            return element

    ident = qualifier_element.get("id")
    name = __get_text(next(qualifier_element.iter(tag=f"{NS}name"), None))
    group_id = __get_text(next(qualifier_element.iter(tag=f"{NS}groupId"), None))

    return (ident, name, group_id)


def get_qualifiers(
    url: str,
    verify: bool = False,
    cert: Optional[Union[str, Tuple[str, str]]] = None,
    logger=LOGGER,
    http_headers: dict = None,
    headers: dict = None,
) -> pd.DataFrame:
    """
    Get FEWS qualifiers as Pandas DataFrame

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default, a new logger will ge created.

    Returns
    -------
        df (pandas.DataFrame): Pandas dataframe with index "id" and columns
        "name" and "group_id".

    """
    # do the request
    timer = Timer(logger)
    if (http_headers is not None) and (headers is not None):
        raise ValueError("Use either http_headers or headers, not both")
    if http_headers is None:
        http_headers = headers
    response = requests.get(url, verify=verify, cert=cert, headers=http_headers) # noqa: S113, S501 - Preserve existing request timeout/TLS behavior.
    # Preserve the existing qualifier endpoint's TLS behavior.
    timer.report("Qualifiers request")

    # parse the response
    if response.status_code == 200:
        # Retain the existing XML parser and accepted FEWS response semantics.
        tree = ElementTree.fromstring(response.content)  # noqa: S314
        qualifiers_tree = list(tree.iter(tag=f"{NS}qualifier"))
        qualifiers_tuple = (_element_to_tuple(i) for i in qualifiers_tree)
        df = pd.DataFrame(qualifiers_tuple, columns=COLUMNS)
        timer.report("Qualifiers parsed")
    else:
        logger.error(f"FEWS Server responds {response.text}")
        df = pd.DataFrame(columns=COLUMNS)
    df.set_index("id", inplace=True)

    return df
