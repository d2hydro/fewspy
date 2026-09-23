import logging
from datetime import datetime

import pandas as pd
import requests

from fewspy.io.read_netcdf import read_netcdf_from_content
from fewspy.io.read_xml import read_xml_from_string
from fewspy.time_series import SeriesKey, TimeSeriesSet
from fewspy.utils.timer import Timer
from fewspy.utils.transformations import parameters_to_fews

LOGGER = logging.getLogger(__name__)


def _ts_or_headers(only_headers=False):
    if only_headers:
        return "Headers {status}"
    else:
        return "TimeSeries {status}"


def get_time_series(
    url: str,
    filter_id: str,
    location_ids: str | list[str] | None = None,
    parameter_ids: str | list[str] | None = None,
    qualifier_ids: str | list[str] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    thinning: int | None = None,
    only_headers: bool = False,
    omit_missing: bool = True,
    show_statistics: bool = False,
    document_format: str = "PI_JSON",
    verify: bool = False,
    logger=LOGGER,
    series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER,
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
        series_key: "location_parameter" (default) or "header"; header mode
            preserves all series returned by asynchronous requests.
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default, a logger will ge created.

    Returns
    -------
        df (pandas.DataFrame): Pandas dataframe with index "id" and columns
        "name" and "group_id".

    """
    series_key = SeriesKey(series_key)
    report_string = _ts_or_headers(only_headers)

    # do the request
    timer = Timer(logger)
    parameters = parameters_to_fews(locals())
    response = requests.get(url, parameters, verify=verify)  # noqa: S113 - Preserve existing request timeout/TLS behavior.
    timer.report(report_string.format(status="request"))

    # parse the response
    if response.ok:
        logger.debug(response.url)
        if document_format == "PI_JSON":
            pi_time_series = response.json()
            time_series_set = TimeSeriesSet.from_dict(pi_time_series)
        elif document_format == "PI_XML":
            time_series_set = read_xml_from_string(response.text)
        elif document_format == "PI_NETCDF":
            time_series_set = read_netcdf_from_content(response.content, series_key=series_key)
        timer.report(report_string.format(status="parsed"))
        if time_series_set.empty:
            logger.debug(f"FEWS WebService request passing empty set: {response.url}")
    else:
        logger.error(f"FEWS WebService request {response.url} responds {response.text}")
        time_series_set = TimeSeriesSet()

    return time_series_set
