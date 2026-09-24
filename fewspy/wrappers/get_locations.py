import logging
from typing import Literal

import geopandas as gpd
import requests

from ..utils.conversions import (
    attributes_to_array,
    camel_to_snake_case,
    geo_datum_to_crs,
    xy_array_to_point,
)
from ..utils.timer import Timer
from ..utils.transformations import parameters_to_fews

LOGGER = logging.getLogger(__name__)


def get_locations(
    url: str,
    filter_id: str | None = None,
    document_format: Literal["GEO_JSON", "PI_JSON"] = "GEO_JSON",
    attributes: list = [],  # noqa: B006 - Preserve the existing read-only API default.
    verify: bool = False,
    logger=LOGGER,
    remove_duplicates: bool = False,
) -> gpd.GeoDataFrame:
    """
    Get FEWS qualifiers as a pandas DataFrame

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
        filter_id (str): the FEWS id of the filter to pass as request parameter
        document_format (str): request document format to return. Defaults to PI_JSON.
        attributes (list): if not emtpy, the location attributes to include as columns in the pandas DataFrame.
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By default, a logger will ge created.

    Returns
    -------
        gdf (geopandas.GeoDataFrame): geopandas GeoDataFrame with index "id". Geometry is Point(x,y) if PI_JSON is requested. It is features geometry if GEO_JSON is requested

    """
    # do the request
    timer = Timer(logger)
    parameters = parameters_to_fews(locals())
    response = requests.get(url, parameters, verify=verify)  # noqa: S113 - Preserve existing request timeout/TLS behavior.
    timer.report("Locations request")

    # parse the response
    if response.status_code == 200:
        if document_format == "PI_JSON":
            # convert to gdf and snake_case
            gdf = gpd.GeoDataFrame(response.json()["locations"], geometry=gpd.GeoSeries())
            gdf.columns = [camel_to_snake_case(i) for i in gdf.columns]

            # remove duplicates
            if remove_duplicates:
                gdf.drop_duplicates(subset="location_id", inplace=True, ignore_index=True)

            # set index
            gdf.set_index("location_id", inplace=True)

            # handle geometry and crs
            gdf["geometry"] = xy_array_to_point(gdf[["x", "y"]].values)
            gdf.crs = geo_datum_to_crs(response.json()["geoDatum"])

        elif document_format == "GEO_JSON":
            # read from GeoJSON
            data = response.json()

            # we read as 4326
            gdf = gpd.GeoDataFrame.from_features(data, crs="4326")
            gdf.columns = [camel_to_snake_case(i) for i in gdf.columns]

            # reproject if crs is provided
            if "crs" in data:
                target_epsg = data["crs"]["properties"]["code"]
                if target_epsg != 4326:
                    gdf = gdf.to_crs(f"EPSG:{target_epsg}")

            # remove duplicates
            if remove_duplicates:
                gdf.drop_duplicates(subset="location_id", inplace=True, ignore_index=True)

            # set index
            gdf.set_index("location_id", inplace=True)
        else:
            raise ValueError(f"Reading document_format {document_format} not implemented")
        # handle attributes
        if attributes:
            gdf.loc[:, attributes] = attributes_to_array(gdf["attributes"].values, attributes)
        gdf.drop(columns=["attributes"], inplace=True)
        timer.report("Locations parsed")

        return gdf
    else:
        logger.error(f"FEWS Server responds {response.text}")
