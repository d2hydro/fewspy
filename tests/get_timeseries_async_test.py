import asyncio
import importlib
import json
from datetime import datetime

import pytest

LOCATION_IDS = ["NL34.HL.KGM156.HWZ1", "NL34.HL.KGM156.LWZ1"]
PARAMETER_IDS = ["Q [m3/s] [NVT] [OW]", "WATHTE [m] [NAP] [OW]"]
QUALIFIER_IDS = ["productie"]


@pytest.mark.parametrize("nested", [False, True], ids=["standalone", "running-loop"])
def test_parallel_requests_preserve_asyncio_tasks(monkeypatch, data_dir, nested):
    """Requests must overlap and remain visible to aiohttp's task tracking."""
    wrapper = importlib.import_module("fewspy.wrappers.get_time_series_async")
    payload = (data_dir / "pi_time_series.json").read_text()
    started = []
    ready = asyncio.Event()

    class Response:
        def raise_for_status(self):
            pass

        async def json(self):
            return json.loads(payload)

    class Session:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def request(self, **kwargs):
            task = asyncio.current_task()
            assert task is not None
            assert task in asyncio.all_tasks()
            started.append(kwargs["params"]["locationIds"][0])
            if len(started) == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), timeout=5)
            return Response()

    monkeypatch.setattr(wrapper.aiohttp, "ClientSession", Session)

    def retrieve():
        return wrapper.get_time_series_async(
            url="https://example.invalid/timeseries",
            filter_id="test",
            location_ids=["one", "two"],
            parameter_ids=["Q"],
            start_time=datetime(2022, 5, 1),
            end_time=datetime(2022, 5, 5),
        )

    async def retrieve_nested():
        parent = asyncio.current_task()
        result = retrieve()
        assert asyncio.current_task() is parent
        return result

    result = asyncio.run(retrieve_nested()) if nested else retrieve()
    assert sorted(started) == ["one", "two"]
    assert len(result) == 2


@pytest.fixture(scope="module")
def time_series_set(api):
    return api.get_time_series(
        filter_id="WDB_OW_KGM",
        location_ids=LOCATION_IDS,
        start_time=datetime(2022, 5, 1),
        end_time=datetime(2022, 5, 5),
        parameter_ids=PARAMETER_IDS,
        qualifier_ids=QUALIFIER_IDS,
        parallel=True,
    )


def test_time_zone(time_series_set):
    assert time_series_set.time_zone == 1.0


def test_version(time_series_set):
    assert time_series_set.version == "1.31"


def test_empty(time_series_set):
    assert not time_series_set.empty


def test_length(time_series_set):
    assert len(time_series_set) == 2


def test_parameter_ids(time_series_set):
    assert all(i in PARAMETER_IDS for i in time_series_set.parameter_ids)


def test_location_ids(time_series_set):
    assert all(i in LOCATION_IDS for i in time_series_set.location_ids)


def test_qualifier_ids(time_series_set):
    assert time_series_set.qualifier_ids == ["productie"]
