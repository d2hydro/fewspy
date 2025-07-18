import requests
import pandas as pd
import logging
from ..utils.timer import Timer
from ..utils.transformations import parameters_to_fews
from typing import List, Union
from ..time_series import TimeSeriesSet
from datetime import datetime
import aiohttp
import asyncio


LOGGER = logging.getLogger(__name__)


def _ts_or_headers(only_headers=False):
    if only_headers:
        return "Headers {status}"
    else:
        return "TimeSeries {status}"


def get_time_series(
    url: str,
    filter_id: str,
    location_ids: Union[str, List[str]] = None,
    parameter_ids: Union[str, List[str]] = None,
    qualifier_ids: Union[str, List[str]] = None,
    start_time: datetime = None,
    end_time: datetime = None,
    thinning: int = None,
    only_headers: bool = False,
    omit_missing: bool = True,
    show_statistics: bool = False,
    document_format: str = "PI_JSON",
    verify: bool = False,
    logger=LOGGER,
) -> pd.DataFrame:
    """
    Get FEWS qualifiers as a pandas DataFrame

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
        filter_id (str): the FEWS id of the filter to pass as request parameter
        location_ids (list): list with FEWS location ids to extract timeseries from. Defaults to None.
        parameter_ids (list): list with FEWS parameter ids to extract timeseries from. Defaults to None.
        qualifier_ids (list): list with FEWS qualifier ids to extract timeseries from. Defaults to None.
        start_time (datetime.datetime): datetime-object with start datetime to use in request. Defaults to None.
        end_time (datetime.datetime): datetime-object with end datetime to use in request. Defaults to None.
        thinning (int): integer value for thinning parameter to use in request. Defaults to None.
        only_headers (bool): if True, only headers will be returned. Defaults to False.
        omit_missing (bool): if True, no missings values will be returned. Defaults to True.
        show_statistics (bool): if True, time series statistics will be included in header. Defaults to False.
        document_format (str): request document format to return. Defaults to PI_JSON.
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default, a logger will ge created.

    Returns:
        df (pandas.DataFrame): Pandas dataframe with index "id" and columns
        "name" and "group_id".

    """
    report_string = _ts_or_headers(only_headers)

    # do the request
    timer = Timer(logger)
    parameters = parameters_to_fews(locals())
    response = requests.get(url, parameters, verify=verify)
    timer.report(report_string.format(status="request"))

    # parse the response
    if response.ok:
        pi_time_series = response.json()
        logger.debug(response.url)
        time_series_set = TimeSeriesSet.from_dict(pi_time_series)
        timer.report(report_string.format(status="parsed"))
        if time_series_set.empty:
            logger.debug(f"FEWS WebService request passing empty set: {response.url}")
    else:
        logger.error(f"FEWS WebService request {response.url} responds {response.text}")
        time_series_set = TimeSeriesSet()

    return time_series_set
