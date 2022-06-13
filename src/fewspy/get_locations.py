import requests
import pandas as pd
import geopandas as gpd
import logging
from .utils.timer import Timer
from .utils.transformations import parameters_to_fews
from .utils.conversions import (
    attributes_to_array,
    camel_to_snake_case,
    geo_datum_to_crs,
    xy_array_to_point,
)


LOGGER = logging.getLogger(__name__)


def get_locations(
    url: str,
    filter_id: str = None,
    document_format: str = "PI_JSON",
    attributes: list = [],
    verify: bool = False,
    logger=LOGGER,
) -> pd.DataFrame:
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
    timer.report("Locations request")

    # parse the response
    if response.status_code == 200:
        # convert to gdf and snake_case
        gdf = gpd.GeoDataFrame(response.json()["locations"])
        gdf.columns = [camel_to_snake_case(i) for i in gdf.columns]
        gdf.set_index("location_id", inplace=True)

        # handle geometry and crs
        gdf["geometry"] = xy_array_to_point(gdf[["x", "y"]].values)
        gdf.crs = geo_datum_to_crs(response.json()["geoDatum"])

        # handle attributes
        if attributes:
            gdf.loc[:, attributes] = attributes_to_array(
                gdf["attributes"].values, attributes
            )
        gdf.drop(columns=["attributes"], inplace=True)

        timer.report("Locations parsed")

    else:
        logger.error(f"FEWS Server responds {response.text}")
        gdf = gpd.GeoDataFrame()

    return gdf
