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


def __result_async_to_time_series_set(async_result):
    time_series_set = TimeSeriesSet()
    time_series_set_gen = (i for i in async_result if "timeSeries" if type(i) == dict)
    time_series_set_list = [i for i in async_result if "timeSeries" in i.keys()]

    version = next((i for i in time_series_set_list if "version" in i.keys()), None)
    if version is not None:
        time_zone = next(
            (i for i in time_series_set_list if "timeZone" in i.keys()), None
        )
        if time_zone is not None:
            time_series = {
                "timeSeries": [
                    i["timeSeries"][0]
                    for i in time_series_set_list
                    if "timeSeries" in i.keys()
                ]
            }
            pi_time_series = {**version, **time_zone, **time_series}
            time_series_set = TimeSeriesSet.from_pi_time_series(pi_time_series)
    return time_series_set


def get_time_series_async(
    url: str,
    filter_id: str,
    location_ids: Union[str, List[str]] = None,
    parameter_ids: Union[str, List[str]] = None,
    qualifier_ids: Union[str, List[str]] = None,
    start_time: datetime = None,
    end_time: datetime = None,
    thinning: int = None,
    document_format: str = "PI_JSON",
    verify: bool = False,
    logger=LOGGER,
) -> pd.DataFrame:
    """

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
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default, a logger will ge created.

    Returns:
        df (pandas.DataFrame): Pandas dataframe with index "id" and columns
        "name" and "group_id".

    """
    parameters = parameters_to_fews(locals())

    def _get_loop():
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        finally:
            loop.set_debug(True)
            return loop

    async def get_timeseries_async(location_id, parameter_id, session):
        """Get timerseries using FEWS (asynchronously)"""
        parameters["locationIds"] = [location_id]
        parameters["parameterIds"] = [parameter_id]
        try:
            response = await session.request(
                method="GET", url=url, params=parameters, verify_ssl=verify
            )
            # print(response.url)
            response.raise_for_status()
        except Exception as err:
            # print(f"An error ocurred: {err}")
            response = None
        response_json = await response.json()
        return response_json

    async def run_program(location_id, parameter_id, session):

        """Wrapper for running program in an asynchronous manner"""
        try:
            response = await get_timeseries_async(location_id, parameter_id, session)
            # print(f"{len(response.get('timeSeries'))}")
        except Exception as err:
            # print(f"Exception occured: {err}")
            response = None
            pass
        return response

    async def asynciee():
        async with aiohttp.ClientSession(loop=loop) as session:
            print("fetching async")
            fetch_all = [
                run_program(location_id, parameter_id, session)
                for location_id in location_ids
                for parameter_id in parameter_ids
            ]
            result_async = await asyncio.gather(*fetch_all)
            return result_async

    if __name__ == "fewspy.wrappers.get_time_series_async":
        print("name=", __name__)
        loop = _get_loop()
        result_async = loop.run_until_complete(asynciee())
    time_series_set = __result_async_to_time_series_set(result_async)
    return time_series_set
