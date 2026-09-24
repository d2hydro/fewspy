import asyncio
import logging
import ssl
import sys
from datetime import datetime

import aiohttp
import pandas as pd

from fewspy.time_series import SeriesKey, TimeSeriesSet
from fewspy.utils.transformations import parameters_to_fews

if sys.version_info >= (3, 14):
    import nest_asyncio2 as nest_asyncio
else:
    import nest_asyncio

nest_asyncio.apply()

LOGGER = logging.getLogger(__name__)


def __result_async_to_time_series_set(async_result, series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER):
    series_key = SeriesKey(series_key)
    if series_key == SeriesKey.HEADER:
        result = TimeSeriesSet()
        for response in async_result:
            if isinstance(response, dict) and "timeSeries" in response:
                part = TimeSeriesSet.from_dict(response)
                result.time_series.extend(part.time_series)
                result.version = part.version
                result.time_zone = part.time_zone
        return result
    time_series_set = TimeSeriesSet()
    time_series_set_gen = (i for i in async_result if "timeSeries" if type(i) is dict)
    time_series_set_list = [i for i in time_series_set_gen if "timeSeries" in i]

    version = next((i for i in time_series_set_list if "version" in i), None)
    if version is not None:
        time_zone = next((i for i in time_series_set_list if "timeZone" in i), None)
        if time_zone is not None:
            time_series = {"timeSeries": [i["timeSeries"][0] for i in time_series_set_list if "timeSeries" in i]}
            pi_time_series = {**version, **time_zone, **time_series}
            time_series_set = TimeSeriesSet.from_dict(pi_time_series)
    return time_series_set


def get_time_series_async(
    url: str,
    filter_id: str,
    location_ids: str | list[str] | None = None,
    parameter_ids: str | list[str] | None = None,
    qualifier_ids: str | list[str] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    thinning: int | None = None,
    document_format: str = "PI_JSON",
    omit_missing: bool = True,
    verify: bool = False,
    logger=LOGGER,
    series_key: SeriesKey | str = SeriesKey.LOCATION_PARAMETER,
    cert: str | tuple[str, str] | None = None,
    http_headers: dict | None = None,
    headers: dict | None = None,
) -> pd.DataFrame:
    """Retrieve FEWS time series concurrently.

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
        document_format (str): request document format to return. Defaults to PI_JSON.
        omit_missing (bool): if True, no missings values will be returned. Defaults to True
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
    if (http_headers is not None) and (headers is not None):
        raise ValueError("Use either http_headers or headers, not both")
    if http_headers is None:
        http_headers = headers

    series_key = SeriesKey(series_key)
    parameters = parameters_to_fews(locals(), bool_to_string=True)

    def _ssl_context(verify: bool, cert: str | tuple[str, str] | None) -> bool | ssl.SSLContext:
        if cert is None:
            return verify

        context = (
            ssl.create_default_context() if verify else ssl._create_unverified_context()  # noqa: S323 - Honor the caller's explicit verify=False setting.
        )

        if isinstance(cert, tuple):
            context.load_cert_chain(certfile=cert[0], keyfile=cert[1])
        else:
            context.load_cert_chain(certfile=cert)
        return context

    ssl_context = _ssl_context(verify=verify, cert=cert)

    def _get_loop():
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.set_debug(True)
        return loop

    async def get_timeseries_async(location_id, parameter_id, qualifier_id, session):
        """Get timerseries using FEWS (asynchronously)"""
        request_parameters = parameters.copy()
        request_parameters["locationIds"] = [location_id]
        request_parameters["parameterIds"] = [parameter_id]
        if qualifier_id is not None:
            request_parameters["qualifierIds"] = qualifier_id
        try:
            response = await session.request(
                method="GET",
                url=url,
                params=request_parameters,
                ssl=ssl_context,  # TODO use verify instead of ssl_context?
                headers=http_headers,
            )
            response.raise_for_status()
        except Exception as err:
            logger.error(f"An error ocurred: {err} while executing url {url} with parameters {parameters}")
            return None
        response_json = await response.json()
        return response_json

    async def run_program(location_id, parameter_id, qualifier_id, session):
        """Wrapper for running program in an asynchronous manner"""
        try:
            response = await get_timeseries_async(location_id, parameter_id, qualifier_id, session)
        except Exception as err:
            logger.error(f"Exception occured: {err}")
            response = None
            pass
        return response

    async def asynciee():
        async with aiohttp.ClientSession(loop=loop) as session:
            args = [(location_id, parameter_id) for location_id in location_ids for parameter_id in parameter_ids]
            if qualifier_ids is None:
                args = [(*i, None) for i in args]
            else:
                args = [(*i, qualifier_id) for i in args for qualifier_id in qualifier_ids]
            fetch_all = [run_program(*i, session) for i in args]
            result_async = await asyncio.gather(*fetch_all)
            return result_async

    if __name__ == "fewspy.wrappers.get_time_series_async":
        loop = _get_loop()
        result_async = loop.run_until_complete(asynciee())
        time_series_set = __result_async_to_time_series_set(result_async, series_key=series_key)
    return time_series_set
