import importlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from threading import Event, current_thread

import numpy as np
import pandas as pd
import pytest
from netCDF4 import Dataset

from fewspy.cache.manifest import FieldEndtry, Manifest
from fewspy.cache.time_series_cache import TimeSeriesCache
from fewspy.io.read_netcdf import read_netcdf
from fewspy.time_series import Header, SeriesKey, TimeSeriesSet

cache_module = importlib.import_module("fewspy.cache.time_series_cache")


def write_file(path, *, times=None, offset=0, module="M", dtype="f4", locations=("A", "B", "A")):
    path.parent.mkdir(parents=True, exist_ok=True)
    times = [0, 1, 24, 25] if times is None else times
    headers = [
        Header(
            type="instantaneous",
            location_id=location,
            parameter_id="P",
            time_step={"unit": "hour", "multiplier": 1, "divider": 2},
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            module_instance_id=module,
            value_type="scalar" if i < 2 else None,
            time_series_type="external historical",
            qualifier_id=None if i < 2 else ["a", "a,b", "a"],
        ).to_json()
        for i, location in enumerate(locations)
    ]
    with Dataset(path, "w") as ds:
        ds.createDimension("time", len(times))
        ds.createDimension("stations", len(locations))
        time = ds.createVariable("time", "f8", ("time",))
        time.units = "hours since 2024-01-01"
        time[:] = times
        value = ds.createVariable("value", dtype, ("time", "stations"), fill_value=-999)
        values = np.arange(len(times) * len(locations)).reshape(len(times), len(locations)) + offset
        values[:, 1] = -999  # Entirely missing series must remain present.
        value[:] = values
        ds.parameter_id = "P"
        ds.fewspy_series_key = "header"
        ds.fewspy_headers = json.dumps(headers)
    return path


def make_manifest(root, generation="20240101T000000", *, offset=0, times=None):
    paths = [
        write_file(root / generation / "filter" / "first.nc", times=times, offset=offset),
        write_file(root / generation / "filter" / "second.nc", times=times, offset=offset + 100, module="N"),
    ]
    return Manifest(
        filepath=root / "manifest.json",
        current_cache=generation,
        expected_file_count=len(paths),
        files=[FieldEndtry.from_file(path) for path in paths],
    )


def reference(manifest, start=None, end=None, locations=None):
    result = TimeSeriesSet()
    for entry in manifest.files:
        part = read_netcdf(entry.path, series_key="header")
        result.time_series.extend(
            ts for ts in part.time_series if locations is None or ts.header.location_id in locations
        )
    if not result.time_series:
        raise ValueError("No full-header series match the cache selection")
    return result.to_df("header").loc[start:end]


def assert_exact(actual, expected):
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    assert actual.attrs == expected.attrs


@pytest.mark.parametrize("size", [0, 1, 16])
@pytest.mark.parametrize("mode", ["header", SeriesKey.HEADER])
@pytest.mark.parametrize("locations", [None, [], ["missing"], ["B"], ["missing", "B", "A", "B"]])
@pytest.mark.parametrize(
    ("start", "end"),
    [
        (None, None),
        ("2024-01-01", "2024-01-01"),
        (datetime(2024, 1, 1, 1), "2024-01-02"),
        ("2025", None),
        ("2024-01-02", "2024-01-01"),
    ],
)
def test_matches_original(tmp_path, size, mode, locations, start, end):
    manifest = make_manifest(tmp_path)
    with TimeSeriesCache(manifest, metadata_cache_size=size) as cache:
        for _ in range(2):
            if locations in ([], ["missing"]):
                with pytest.raises(ValueError, match="No full-header series"):
                    cache.get_time_series("filter", "P", start, end, locations, mode)
            else:
                assert_exact(
                    cache.get_time_series("filter", "P", start, end, locations, mode),
                    reference(manifest, start, end, locations),
                )


@pytest.mark.parametrize("times", [[24, 0, 25, 1], [0, 0, 24, 25], [], [0]])
def test_unusual_time_axes(tmp_path, times, monkeypatch):
    manifest = make_manifest(tmp_path, times=times)
    calls = []
    original = TimeSeriesCache._read_header_fallback

    def fallback(paths, locations):
        calls.append(True)
        return original(paths, locations)

    monkeypatch.setattr(TimeSeriesCache, "_read_header_fallback", staticmethod(fallback))
    with TimeSeriesCache(manifest) as cache:
        assert_exact(cache.get_time_series("filter", "P", series_key="header"), reference(manifest))
    assert bool(calls) == (len(times) > 1)


def test_different_axes_overlapping_identities_and_float64(tmp_path):
    manifest = make_manifest(tmp_path)
    write_file(manifest.files[1].path, times=[1, 2, 49], module="M", dtype="f8")
    with TimeSeriesCache(manifest) as cache:
        for start, end in [(None, None), ("2024-01-02", "2024-01-03"), ("2023", "2023")]:
            assert_exact(
                cache.get_time_series("filter", "P", start, end, series_key="header"), reference(manifest, start, end)
            )


@pytest.mark.parametrize("alternative", [False, True])
def test_scaled_values_and_alternative_dimensions(tmp_path, alternative):
    manifest = make_manifest(tmp_path)
    with Dataset(manifest.files[0].path, "a") as ds:
        ds.variables["value"].scale_factor = 0.5
        ds.variables["value"].add_offset = 10.0
    if alternative:
        with Dataset(manifest.files[1].path, "a") as ds:
            # The original reader accepts this shape, despite the nonstandard name.
            ds.renameDimension("stations", "series")
    with TimeSeriesCache(manifest) as cache:
        assert_exact(
            cache.get_time_series("filter", "P", "2024-01-01", "2024-01-01", ["A"], "header"),
            reference(manifest, "2024-01-01", "2024-01-01", ["A"]),
        )


def test_filter_and_parameter_routing(tmp_path):
    manifest = make_manifest(tmp_path)
    other_filter = write_file(tmp_path / manifest.current_cache / "other" / "extra.nc")
    other_parameter = write_file(tmp_path / manifest.current_cache / "filter" / "other.nc")
    with Dataset(other_parameter, "a") as ds:
        ds.parameter_id = "Q"
        ds.delncattr("fewspy_headers")  # Unrelated parameter is not parsed.
    expected = reference(manifest)
    manifest.files.extend([FieldEndtry.from_file(other_filter), FieldEndtry.from_file(other_parameter)])
    with TimeSeriesCache(manifest) as cache:
        assert_exact(cache.get_time_series("filter", "P", series_key="header"), expected)
        with pytest.raises(ValueError, match="No full-header series"):
            cache.get_time_series("absent", "P", series_key="header")


def test_integer_fill_error_outside_selection_is_preserved(tmp_path):
    manifest = make_manifest(tmp_path)
    write_file(manifest.files[0].path, dtype="i4")
    with pytest.raises(TypeError):
        reference(manifest, locations=["A"])
    with TimeSeriesCache(manifest) as cache, pytest.raises(TypeError):
        cache.get_time_series("filter", "P", location_ids=["A"], series_key="header")


def test_first_read_closes_all_datasets_even_on_decode_failure(tmp_path, monkeypatch):
    manifest = make_manifest(tmp_path)
    original = TimeSeriesCache._open_dataset
    active = []
    opened = []

    @contextmanager
    def tracked(path):
        if len(opened) == 1:
            raise ValueError("cannot decode second file")
        with original(path) as ds:
            active.append(ds)
            opened.append(path)
            try:
                yield ds
            finally:
                active.pop()

    monkeypatch.setattr(TimeSeriesCache, "_open_dataset", staticmethod(tracked))
    with TimeSeriesCache(manifest) as cache:
        assert not opened
        with pytest.raises(ValueError, match="second file"):
            cache.get_time_series("filter", "P", series_key="header")
    assert len(opened) == 1
    assert not active


@pytest.mark.parametrize("damage", ["count", "header", "marker"])
def test_validation_includes_unselected_headers(tmp_path, damage):
    manifest = make_manifest(tmp_path)
    with Dataset(manifest.files[0].path, "a") as ds:
        headers = json.loads(ds.fewspy_headers)
        if damage == "count":
            headers.pop()
        elif damage == "header":
            raw = json.loads(headers[1])
            del raw["time_step"]
            headers[1] = json.dumps(raw)
        else:
            ds.delncattr("fewspy_series_key")
        ds.fewspy_headers = json.dumps(headers)
    with TimeSeriesCache(manifest) as cache, pytest.raises(ValueError):
        cache.get_time_series("filter", "P", location_ids=["A"], series_key="header")


@pytest.mark.parametrize("size,expected", [(0, 4), (1, 4), (2, 2)])
def test_metadata_reuse_eviction_and_disabled_cache(tmp_path, monkeypatch, size, expected):
    manifest = make_manifest(tmp_path)
    calls = []
    decoded = []
    original_open = TimeSeriesCache._open_dataset
    original = cache_module.read_metadata

    def counted_open(path):
        decoded.append(path)
        return original_open(path)

    monkeypatch.setattr(TimeSeriesCache, "_open_dataset", staticmethod(counted_open))

    def counted(dataset):
        calls.append(dataset.filepath())
        return original(dataset)

    monkeypatch.setattr(cache_module, "read_metadata", counted)
    with TimeSeriesCache(manifest, metadata_cache_size=size) as cache:
        first = cache.get_time_series("filter", "P", location_ids=["A"], series_key="header")
        first.attrs["fewspy_headers"].clear()
        second = cache.get_time_series("filter", "P", location_ids=["B"], series_key="header")
        assert_exact(second, reference(manifest, locations=["B"]))
        assert len(cache._metadata) <= size
        assert len(calls) == expected
        assert len(decoded) == expected


def test_selects_before_loading_values(tmp_path, monkeypatch):
    manifest = make_manifest(tmp_path)
    original = cache_module.read_selection
    selections = []

    def recorded(dataset, metadata, positions, time_slice):
        selections.append((positions.tolist(), metadata.time[time_slice].tolist()))
        return original(dataset, metadata, positions, time_slice)

    monkeypatch.setattr(cache_module, "read_selection", recorded)
    with TimeSeriesCache(manifest) as cache:
        cache.get_time_series("filter", "P", "2024-01-01", "2024-01-01", ["B"], "header")
    assert len(selections) == 2
    assert all(positions == [1] and len(times) == 2 for positions, times in selections)


def test_refresh_and_common_time_axis(tmp_path, monkeypatch):
    old = make_manifest(tmp_path)
    old.atomic_write(old.filepath, clean_old_caches=False)
    new = make_manifest(tmp_path, "20240102T000000", offset=1000, times=[48, 49])
    with TimeSeriesCache.from_manifest_file(old.filepath, metadata_cache_size=2) as cache:
        cache.get_time_series("filter", "P", series_key="header")
        assert not cache.refresh_if_changed(old.filepath)
        before = cache.common_time_axis
        new.atomic_write(new.filepath, clean_old_caches=False)
        cache.last_manifest_mtime = -1
        assert cache.refresh_if_changed(old.filepath)
        assert not cache._metadata
        assert not cache.common_time_axis.equals(before)
        assert_exact(cache.get_time_series("filter", "P", series_key="header"), reference(new))


@pytest.mark.parametrize("failure", ["hash", "open"])
def test_failed_refresh_keeps_everything(tmp_path, monkeypatch, failure):
    old = make_manifest(tmp_path)
    new = make_manifest(tmp_path, "20240102T000000", offset=1000)
    new.atomic_write(new.filepath, clean_old_caches=False)
    with TimeSeriesCache(old, last_manifest_mtime=-1) as cache:
        expected = cache.get_time_series("filter", "P", series_key="header")
        before = cache.common_time_axis
        snapshot = cache._snapshot
        metadata = dict(cache._metadata)
        if failure == "hash":
            path = new.files[0].path
            content = bytearray(path.read_bytes())
            content[-1] ^= 1
            path.write_bytes(content)
        else:

            def fail(manifest):
                raise ValueError("decoding failed")

            monkeypatch.setattr(cache, "_prepare_snapshot", fail)
        assert not cache.refresh_if_changed(new.filepath)
        assert cache._snapshot is snapshot
        assert cache.last_manifest_mtime == -1
        assert dict(cache._metadata) == metadata
        assert cache.common_time_axis.equals(before)
        assert_exact(cache.get_time_series("filter", "P", series_key="header"), expected)


@pytest.mark.parametrize("action", ["refresh", "close"])
@pytest.mark.parametrize("fallback", [False, True])
def test_overlapping_read_and_lifecycle(tmp_path, monkeypatch, action, fallback):
    old = make_manifest(tmp_path, times=[24, 0, 25, 1] if fallback else None)
    new = make_manifest(tmp_path, "20240102T000000", offset=1000)
    new.atomic_write(new.filepath, clean_old_caches=False)
    cache = TimeSeriesCache(old)
    snapshot = cache._snapshot
    reached = Event()
    resume = Event()
    original = cache._read_header_file

    def paused(current, path, *args):
        part = original(current, path, *args)
        if current is snapshot and path == old.files[0].path:
            reached.set()
            assert resume.wait(10)
        return part

    monkeypatch.setattr(cache, "_read_header_file", paused)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(cache.get_time_series, "filter", "P", series_key="header")
            try:
                assert reached.wait(10)
                if action == "refresh":
                    assert cache.refresh_if_changed(new.filepath)
                    assert_exact(cache.get_time_series("filter", "P", series_key="header"), reference(new))
                else:
                    cache.close()
                    with pytest.raises(RuntimeError, match="closed"):
                        cache.get_time_series("filter", "P", series_key="header")
            finally:
                resume.set()
            assert_exact(future.result(timeout=10), reference(old))
        if action == "close":
            assert not cache._metadata
        else:
            assert all(key[0] is cache._snapshot for key in cache._metadata)
    finally:
        cache.close()


def test_common_axis_read_overlaps_refresh(tmp_path, monkeypatch):
    old = make_manifest(tmp_path)
    new = make_manifest(tmp_path, "20240102T000000", times=[48, 49])
    new.atomic_write(new.filepath, clean_old_caches=False)
    reached = Event()
    resume = Event()
    with TimeSeriesCache(old) as cache:
        original = cache._acquire_snapshot

        def paused():
            snapshot = original()
            if current_thread().name.startswith("axis"):
                reached.set()
                assert resume.wait(10)
            return snapshot

        monkeypatch.setattr(cache, "_acquire_snapshot", paused)
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="axis") as pool:
            future = pool.submit(lambda: cache.common_time_axis)
            try:
                assert reached.wait(10)
                assert cache.refresh_if_changed(new.filepath)
                current = cache.common_time_axis
            finally:
                resume.set()
            previous = future.result(timeout=10)
        assert len(previous) == 4
        assert len(current) == 2
        assert cache.common_time_axis.equals(current)


def test_lru_keeps_recently_used_file(tmp_path):
    paths = [write_file(tmp_path / name / "P.nc") for name in ["one", "two", "three"]]
    manifest = Manifest(current_cache="20240101T000000", files=[FieldEndtry.from_file(path) for path in paths])
    with TimeSeriesCache(manifest, metadata_cache_size=2) as cache:
        for name in ["one", "two", "one", "three"]:
            cache.get_time_series(name, "P", series_key="header")
        assert [key[1] for key in cache._metadata] == [paths[0], paths[2]]


def test_concurrent_reads_and_cleanup_on_error(tmp_path, monkeypatch):
    manifest = make_manifest(tmp_path)
    expected = {location: reference(manifest, locations=[location]) for location in ["A", "B"]}
    original = cache_module.Dataset
    active = []

    @contextmanager
    def tracked(*args, **kwargs):
        with original(*args, **kwargs) as dataset:
            active.append(dataset)
            try:
                yield dataset
            finally:
                active.remove(dataset)

    monkeypatch.setattr(cache_module, "Dataset", tracked)
    with TimeSeriesCache(manifest) as cache, ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(cache.get_time_series, "filter", "P", None, None, [location], "header")
            for location in ["A", "B"] * 4
        ]
        for future, location in zip(futures, ["A", "B"] * 4, strict=True):
            assert_exact(future.result(timeout=10), expected[location])
        with pytest.raises((ValueError, TypeError)):
            cache.get_time_series("filter", "P", "not a date", series_key="header")
        assert not active
    cache.close()
    with pytest.raises(RuntimeError, match="closed"):
        _ = cache.common_time_axis
    with pytest.raises(RuntimeError, match="closed"):
        cache.refresh_if_changed(tmp_path / "missing.json")


@pytest.mark.parametrize("size", [-1, 1.5, True, None])
def test_invalid_cache_limits(tmp_path, size):
    with pytest.raises(ValueError, match="non-negative integer"):
        TimeSeriesCache(make_manifest(tmp_path), metadata_cache_size=size)


def test_legacy_selection(tmp_path):
    path = tmp_path / "filter" / "P.nc"
    path.parent.mkdir()
    with Dataset(path, "w") as ds:
        ds.createDimension("time", 3)
        ds.createDimension("stations", 2)
        time = ds.createVariable("time", "f8", ("time",))
        time.units = "hours since 2024-01-01"
        time[:] = [0, 1, 2]
        station = ds.createVariable("station_id", str, ("stations",))
        station[:] = np.array(["B", "A"], dtype=object)
        ds.createVariable("P", "f4", ("time", "stations"))[:] = [[1, 2], [3, 4], [5, 6]]
        ds.parameter_id = "P"
    manifest = Manifest(current_cache="20240101T000000", files=[FieldEndtry.from_file(path)])
    with TimeSeriesCache(manifest) as cache:
        frame = cache.get_time_series("filter", "P", "2024-01-01T01", None, ["A"])
        assert frame.iloc[:, 0].tolist() == [4, 6]
        assert frame.columns.names == ["location_id", "parameter_id"]
        with pytest.raises(KeyError):
            cache.get_time_series("filter", "P", location_ids=["missing"])
        with pytest.raises(ValueError, match="no full FEWS header metadata"):
            cache.get_time_series("filter", "P", series_key="header")
        with pytest.raises(ValueError, match="No entry found"):
            cache.get_time_series("missing", "P")
    # All resources are closed even on the failure paths (also on Windows).
    shutil.rmtree(path.parent)


def damage_auxiliary_time(path):
    """Add a variable ignored by header selection but rejected by xarray decoding."""
    with Dataset(path, "a") as dataset:
        variable = dataset.createVariable("unused_time", "f8", ("time",))
        variable[:] = np.arange(len(dataset.dimensions["time"]))
        variable.units = "hours since not-a-date"


def test_decoding_is_deferred_to_the_used_file(tmp_path):
    manifest = make_manifest(tmp_path)
    other = write_file(tmp_path / manifest.current_cache / "unused" / "P.nc")
    damage_auxiliary_time(other)
    manifest.files.append(FieldEndtry.from_file(other))
    manifest.expected_file_count += 1
    manifest.atomic_write(manifest.filepath, clean_old_caches=False)
    with TimeSeriesCache.from_manifest_file(manifest.filepath) as cache:
        expected = reference(make_manifest(tmp_path / "reference"))
        assert_exact(cache.get_time_series("filter", "P", series_key="header"), expected)
        for _ in range(2):
            with pytest.raises(ValueError, match=r"[Dd]ecode"):
                cache.get_time_series("unused", "P", series_key="header")
            assert all(key[1] != other for key in cache._metadata)
        # The default mode and the full time axis retain xarray's validation too.
        with pytest.raises(ValueError, match=r"[Dd]ecode"):
            cache.get_time_series("unused", "P")
        with pytest.raises(ValueError, match=r"[Dd]ecode"):
            _ = cache.common_time_axis
    # Even a failed validation releases both the raw and xarray file handles.
    other.unlink()


def test_fallback_validates_later_files_before_returning(tmp_path):
    manifest = make_manifest(tmp_path)
    write_file(manifest.files[0].path, times=[24, 0, 25, 1])
    damage_auxiliary_time(manifest.files[1].path)
    with TimeSeriesCache(manifest) as cache, pytest.raises(ValueError, match=r"[Dd]ecode"):
        cache.get_time_series("filter", "P", series_key="header")


def test_refresh_defers_content_errors_without_reusing_previous_data(tmp_path):
    old = make_manifest(tmp_path)
    new = make_manifest(tmp_path, "20240102T000000", offset=1000)
    damage_auxiliary_time(new.files[1].path)
    new.files[1] = FieldEndtry.from_file(new.files[1].path)
    new.atomic_write(new.filepath, clean_old_caches=False)
    with TimeSeriesCache(old, last_manifest_mtime=-1) as cache:
        cache.get_time_series("filter", "P", series_key="header")
        assert cache.refresh_if_changed(new.filepath)
        assert not cache._metadata
        assert cache.manifest.current_cache == new.current_cache
        with pytest.raises(ValueError, match=r"[Dd]ecode"):
            cache.get_time_series("filter", "P", series_key="header")
        assert all(key[0] is cache._snapshot for key in cache._metadata)


@pytest.mark.parametrize("size", [0, 1])
def test_later_location_selection_still_decodes_retained_headers(tmp_path, size):
    path = write_file(tmp_path / "filter" / "P.nc")
    damage_auxiliary_time(path)
    manifest = Manifest(current_cache="20240101T000000", files=[FieldEndtry.from_file(path)])
    with TimeSeriesCache(manifest, metadata_cache_size=size) as cache:
        with pytest.raises(ValueError, match="No full-header series"):
            cache.get_time_series("filter", "P", location_ids=["absent"], series_key="header")
        assert all(not metadata.decoded for metadata in cache._metadata.values())
        for _ in range(2):
            with pytest.raises(ValueError, match=r"[Dd]ecode"):
                cache.get_time_series("filter", "P", location_ids=["A"], series_key="header")
        assert all(not metadata.decoded for metadata in cache._metadata.values())


def test_first_matching_location_decodes_once(tmp_path, monkeypatch):
    path = write_file(tmp_path / "filter" / "P.nc")
    manifest = Manifest(current_cache="20240101T000000", files=[FieldEndtry.from_file(path)])
    decoded = []
    original = TimeSeriesCache._open_dataset

    def counted(path):
        decoded.append(path)
        return original(path)

    monkeypatch.setattr(TimeSeriesCache, "_open_dataset", staticmethod(counted))
    with TimeSeriesCache(manifest) as cache:
        with pytest.raises(ValueError, match="No full-header series"):
            cache.get_time_series("filter", "P", location_ids=["absent"], series_key="header")
        assert not decoded
        for location in ["A", "B"]:
            assert_exact(
                cache.get_time_series("filter", "P", location_ids=[location], series_key="header"),
                reference(manifest, locations=[location]),
            )
        assert decoded == [path]
