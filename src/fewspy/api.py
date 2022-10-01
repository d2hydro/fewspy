"""
Module for calling the FEWS REST API.

The module contains one class and methods corresponding with the FEWS PI-REST requests:
https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service
"""

import pandas as pd
from .utils.timer import Timer
from .utils.url import validate_url
import logging
import urllib3

from .wrappers import (
    get_time_series_async,
    get_qualifiers,
    get_time_series,
    get_locations,
    get_filters,
    get_parameters)

LOGGER = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Api:
    """
    Python API for the Deltares FEWS PI REST Web Service.

    For more info on how-to work with the FEWS REST Web Service, visit the Deltares Website: https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service
    """

    def __init__(self, url, logger=None, ssl_verify=None):
        self.document_format = "PI_JSON"
        self.logger = logger
        self.timer = Timer(logger)
        self.url, verify = validate_url(url)

        # set ssl_verify
        if ssl_verify is None:
            self.ssl_verify = verify
        else:
            self.ssl_verify = ssl_verify

        # set logger
        if logger is None:
            self.logger = LOGGER
        else:
            self.logger = logger

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
        """
         Get FEWS qualifiers as a pandas DataFrame

         Args:
             filter_id (str): the FEWS id of the filter to pass as request parameter

         Returns:
             df (pandas.DataFrame): Pandas dataframe with index "id" and columns
             "name" and "group_id".

         """

        kwargs = self.__kwargs(url_post_fix="parameters", kwargs=locals())
        result = get_parameters(**kwargs)

        return result

    def get_filters(self, filter_id=None):
        """
         Get FEWS qualifiers as a pandas DataFrame

         Args:
             E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
             filter_id (str): the FEWS id of the filter to pass as request parameter

         Returns:
             df (pandas.DataFrame): Pandas dataframe with index "id" and columns
             "name" and "group_id".

         """

        kwargs = self.__kwargs(url_post_fix="filters", kwargs=locals())
        result = get_filters(**kwargs)

        return result

    def get_locations(self, filter_id=None, attributes=[]):
        """
        Get FEWS qualifiers as a pandas DataFrame

        Args:
            E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
            filter_id (str): the FEWS id of the filter to pass as request parameter
            attributes (list): if not emtpy, the location attributes to include as columns in the pandas DataFrame.

        Returns:
            df (pandas.DataFrame): Pandas dataframe with index "id" and columns
            "name" and "group_id".

        """

        kwargs = self.__kwargs(url_post_fix="locations", kwargs=locals())
        result = get_locations(**kwargs)

        return result

    def get_qualifiers(self) -> pd.DataFrame:
        """
         Get FEWS qualifiers as Pandas DataFrame

         Returns:
             df (pandas.DataFrame): Pandas dataframe with index "id" and columns
             "name" and "group_id".

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
        """
         Get FEWS qualifiers as a pandas DataFrame

         Args:
             filter_id (str): the FEWS id of the filter to pass as request parameter
             location_ids (list): list with FEWS location ids to extract timeseries from. Defaults to None.
             parameter_ids (list): list with FEWS parameter ids to extract timeseries from. Defaults to None.
             qualifier_ids (list): list with FEWS qualifier ids to extract timeseries from. Defaults to None.
             start_time (datetime.datetime): datetime-object with start datetime to use in request. Defaults to None.
             end_time (datetime.datetime): datetime-object with end datetime to use in request. Defaults to None.
             thinning (int): integer value for thinning parameter to use in request. Defaults to None.
             only_headers (bool): if True, only headers will be returned. Defaults to False.
             show_statistics (bool): if True, time series statistics will be included in header. Defaults to False.
             parallel (bool): if True, timeseries are requested by the asynchronous wrapper. Defaults to False

         Returns:
             df (pandas.DataFrame): Pandas dataframe with index "id" and columns
             "name" and "group_id".

         """
        kwargs = self.__kwargs(url_post_fix="timeseries", kwargs=locals())
        if parallel:
            kwargs.pop("only_headers")
            kwargs.pop("show_statistics")
            result = get_time_series_async(**kwargs)
        else:
            result = get_time_series(**kwargs)

        return result
