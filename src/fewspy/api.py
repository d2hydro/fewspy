"""
Module for calling the FEWS REST API.

The module contains one class and methods corresponding with the FEWS PI-REST requests:
https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service
"""

import pandas as pd
from .utils.timer import Timer
import logging
import urllib3

from .get_qualifiers import get_qualifiers
from .get_time_series import get_time_series
from .get_time_series_async import get_time_series_async
from .get_locations import get_locations
from .get_filters import get_filters
from .get_parameters import get_parameters

LOGGER = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Api:
    """
    FEWS PI-REST api it needs an server url and a logger.

    All variables related to PI-REST variables are defined camelCase. All others are
    snake_case.
    """

    def __init__(self, url, logger=LOGGER, ssl_verify=False):
        self.document_format = "PI_JSON"
        self.url = url
        self.logger = logger
        self.timer = Timer(logger)
        self.ssl_verify = ssl_verify

    def __kwargs(self, url_post_fix: str, kwargs: dict) -> dict:
        kwargs = {
            **kwargs,
            **dict(
                url=f"{self.url}{url_post_fix}",
                document_format=self.document_format,
                verify=self.ssl_verify,
                logger=self.logger,
            ),
        }
        kwargs.pop("self")
        kwargs.pop("parallel", None)
        return kwargs

    def get_parameters(self, filter_id=None):

        kwargs = self.__kwargs(url_post_fix="parameters", kwargs=locals())
        result = get_parameters(**kwargs)

        return result

    def get_filters(self, filter_id=None):
        """Get filters as dictionary, or sub-filters if a filter_id is specified."""

        kwargs = self.__kwargs(url_post_fix="filters", kwargs=locals())
        result = get_filters(**kwargs)

        return result

    def get_locations(self, filter_id=None, attributes=[]):
        """Get location en return as a GeoDataFrame."""

        kwargs = self.__kwargs(url_post_fix="locations", kwargs=locals())
        result = get_locations(**kwargs)

        return result

    def get_qualifiers(self) -> pd.DataFrame:
        """
        Get FEWS qualifiers as Pandas DataFrame

        Returns:
            result (pandas.DataFrame): Pandas DataFrame with index "id" and
            columns "name" and "group_id".

        """
        url = f"{self.url}qualifiers"
        result = get_qualifiers(url, verify=self.ssl_verify, logger=self.logger)
        return result

    def get_time_series(
        self,
        filter_id,
        location_ids=None,
        start_time=None,
        end_time=None,
        parameter_ids=None,
        qualifier_ids=None,
        thinning=None,
        only_headers=False,
        show_statistics=False,
        parallel=False,
    ):

        kwargs = self.__kwargs(url_post_fix="timeseries", kwargs=locals())
        if parallel:
            kwargs.pop("only_headers")
            kwargs.pop("show_statistics")
            result = get_time_series_async(**kwargs)
        else:
            result = get_time_series(**kwargs)

        return result
