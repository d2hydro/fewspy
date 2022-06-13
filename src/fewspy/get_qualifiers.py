import requests
from xml.etree import ElementTree
import pandas as pd
import logging
from .utils.timer import Timer

NS = "{http://www.wldelft.nl/fews/PI}"
LOGGER = logging.getLogger(__name__)
COLUMNS = ["id", "name", "group_id"]


def _element_to_tuple(qualifier_element: ElementTree.Element) -> tuple:
    """
    Parses a qualifier element to a tuple

    Args:
        qualifier_element (xml.etree.ElementTree.Element): ET.Element with
        Delft-FEWS qualifier tags.

    Returns:
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


def get_qualifiers(url: str, verify: bool = False, logger=LOGGER) -> pd.DataFrame:
    """
    Get FEWS qualifiers as Pandas DataFrame

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
    response = requests.get(url, verify=False)
    timer.report("Qualifiers request")

    logger.debug(response.url)

    # parse the response
    if response.status_code == 200:
        tree = ElementTree.fromstring(response.content)
        qualifiers_tree = [i for i in tree.iter(tag=f"{NS}qualifier")]
        qualifiers_tuple = (_element_to_tuple(i) for i in qualifiers_tree)
        df = pd.DataFrame(qualifiers_tuple, columns=COLUMNS)
        timer.report("Qualifiers parsed")
    else:
        logger.error(f"FEWS Server responds {response.text}")
        df = pd.DataFrame(columns=COLUMNS)
    df.set_index("id", inplace=True)

    return df
