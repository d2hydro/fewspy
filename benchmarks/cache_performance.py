"""Compare cache lifecycles in isolated processes against a Git revision.

Example (from the repository root)::

    pixi run python benchmarks/cache_performance.py --stations 21095 --steps 720 --runs 5 --output .tmp/large.json

Use --density .05 for sparse histories and --stations 128 --steps 168 for a
small fixture. Filesystem caches are warm; fixture creation, instrumentation,
and memory sampling are outside the timed measurements. psutil, when available
in the development environment, measures RSS and open files without adding a
library dependency. Retained RSS includes the Python/native allocator's pools.
"""

import argparse
import gc
import hashlib
import importlib
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from time import perf_counter
from unittest.mock import patch

import netCDF4
import numpy as np
import pandas as pd
import xarray as xr

from fewspy.cache.manifest import FieldEndtry, Manifest
from fewspy.cache.time_series_cache import TimeSeriesCache
from fewspy.time_series import Header

try:
    import psutil
except ImportError:
    psutil = None


def fixture(root, generation, stations, steps, density):
    path = root / generation / "filter" / "P.nc"
    path.parent.mkdir(parents=True)
    base = Header(
        type="instantaneous",
        location_id="L",
        parameter_id="P",
        module_instance_id="M",
        value_type="scalar",
        time_series_type="external historical",
        time_step={"unit": "hour", "multiplier": 1},
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2025, 1, 1),
    )
    headers = []
    for i in range(stations):
        base.location_id = f"L{i}"
        headers.append(base.to_json())
    rng = np.random.default_rng(42)
    values = rng.standard_normal((steps, stations)).astype("f4")
    if density < 1:
        values[rng.random(values.shape) >= density] = np.nan
    with netCDF4.Dataset(path, "w", format="NETCDF4_CLASSIC") as ds:
        ds.createDimension("time", steps)
        ds.createDimension("stations", stations)
        time = ds.createVariable("time", "f8", ("time",))
        time.units = "hours since 2024-01-01"
        time[:] = np.arange(steps)
        value = ds.createVariable(
            "value",
            "f4",
            ("time", "stations"),
            fill_value=np.nan,
            zlib=True,
            complevel=4,
            shuffle=True,
            chunksizes=(max(1, steps // 10), min(stations, 128)),
        )
        value[:] = values
        ds.parameter_id = "P"
        ds.fewspy_series_key = "header"
        ds.fewspy_headers = json.dumps(headers)
    manifest = Manifest(
        filepath=root / f"{generation}.json",
        current_cache=generation,
        expected_file_count=1,
        files=[FieldEndtry.from_file(path)],
    )
    manifest.atomic_write(manifest.filepath, clean_old_caches=False)
    return manifest.filepath


def release(cache):
    if hasattr(cache, "close"):
        cache.close()
    else:
        for dataset in cache._datasets.values():
            dataset.close()


def selection(cache, stations, index, full=False):
    locations = None if full else [f"L{(index * 23 + j) % stations}" for j in range(min(20, stations))]
    return cache.get_time_series(
        "filter",
        "P",
        None if full else "2024-01-02",
        None if full else "2024-01-03",
        locations,
        "header",
    )


def measure(operation, runs):
    samples = []
    for i in range(runs):
        gc.collect()
        start = perf_counter()
        operation(i)
        samples.append(perf_counter() - start)
    return {
        "seconds": samples,
        "median": float(np.median(samples)),
        "p10": float(np.quantile(samples, 0.1)),
        "p90": float(np.quantile(samples, 0.9)),
    }


def instrument(cls, path, stations):
    reader = importlib.import_module("fewspy.io.read_netcdf")
    cache_reader = importlib.import_module("fewspy.cache._header_reader")
    cache_module = importlib.import_module("fewspy.cache.time_series_cache")
    with ExitStack() as stack:
        opens = [
            stack.enter_context(patch.object(module, name, wraps=getattr(module, name)))
            for module, name in [(xr, "open_dataset"), (reader, "Dataset"), (cache_module, "Dataset")]
        ]
        headers = stack.enter_context(patch.object(Header, "from_json", wraps=Header.from_json))
        series = [
            stack.enter_context(patch.object(module, "TimeSeries", wraps=module.TimeSeries))
            for module in [reader, cache_reader]
        ]
        cache = cls.from_manifest_file(path)
        selection(cache, stations, 0)
        first = {
            "opens": sum(mock.call_count for mock in opens),
            "headers": headers.call_count,
            "series": sum(mock.call_count for mock in series),
        }
        for mock in [*opens, headers, *series]:
            mock.reset_mock()
        selection(cache, stations, 1)
        repeated = {
            "opens": sum(mock.call_count for mock in opens),
            "headers": headers.call_count,
            "series": sum(mock.call_count for mock in series),
        }
        release(cache)
    return {"constructor_and_first": first, "repeated": repeated}


def memory(cls, path, stations, runs):
    if psutil is None:
        return {"unavailable": "Install psutil in the benchmark environment to sample native RSS and file handles."}
    process = psutil.Process()
    done = Event()
    start_rss = process.memory_info().rss
    start_files = len(process.open_files())
    rss = [start_rss]
    handles = [start_files]

    def sample():
        while not done.wait(0.01):
            rss.append(process.memory_info().rss)
            handles.append(len(process.open_files()))

    thread = Thread(target=sample)
    thread.start()
    cache = cls.from_manifest_file(path)
    try:
        for i in range(runs):
            selection(cache, stations, i)
        gc.collect()
        retained = process.memory_info().rss
        retained_files = len(process.open_files())
    finally:
        release(cache)
        done.set()
        thread.join()
    gc.collect()
    return {
        "rss_start": start_rss,
        "rss_peak": max(rss),
        "rss_retained": retained,
        "rss_after_close": process.memory_info().rss,
        "files_start": start_files,
        "files_peak": max(handles),
        "files_retained": retained_files,
        "files_after_close": len(process.open_files()),
    }


def worker(args):
    if args.worker == "old":
        spec = importlib.util.spec_from_file_location("baseline_cache", args.baseline)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = module.TimeSeriesCache
    else:
        cls = TimeSeriesCache
    paths = [args.root / f"{generation}.json" for generation in ["20240101T000000", "20240102T000000"]]
    result = {"memory": memory(cls, paths[0], args.stations, args.runs)}
    for full in [False, True]:

        def first(i, full=full):
            cache = cls.from_manifest_file(paths[0])
            try:
                selection(cache, args.stations, i, full)
            finally:
                release(cache)

        cache = cls.from_manifest_file(paths[0])
        try:
            # Both implementations receive exactly one unmeasured warm-up read.
            selection(cache, args.stations, 0, full)
            repeated = measure(
                lambda i, full=full, cache=cache: selection(cache, args.stations, i + 1, full), args.runs
            )
        finally:
            release(cache)

        def refresh(i, full=full):
            cache = cls.from_manifest_file(paths[0])
            selection(cache, args.stations, 0, full)
            # Exclude preparation; include the complete validation and refresh.
            cache.last_manifest_mtime = -1
            start = perf_counter()
            try:
                cache.refresh_if_changed(paths[1])
                selection(cache, args.stations, i + 1, full)
                return perf_counter() - start
            finally:
                release(cache)

        refresh_samples = [refresh(i) for i in range(args.runs)]
        result["full" if full else "narrow"] = {
            "constructor_and_first": measure(first, args.runs),
            "repeated": repeated,
            "refresh_and_read": {
                "seconds": refresh_samples,
                "median": float(np.median(refresh_samples)),
                "p10": float(np.quantile(refresh_samples, 0.1)),
                "p90": float(np.quantile(refresh_samples, 0.9)),
            },
        }
    result["instrumentation"] = instrument(cls, paths[0], args.stations)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stations", type=int, default=21095)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--density", type=float, default=1)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--revision", default="0037f92fb43b9b503ff72376fb739965cb4f6309")
    parser.add_argument("--output", type=Path, default=Path(".tmp/cache-performance.json"))
    parser.add_argument("--worker", choices=["old", "new"])
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args)))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as temp:
        root = Path(temp).resolve()
        source = subprocess.check_output(  # noqa: S603 - Explicit developer-supplied local baseline revision.
            [shutil.which("git"), "show", f"{args.revision}:fewspy/cache/time_series_cache.py"],
            text=True,
        )
        baseline = root / "baseline_cache.py"
        baseline.write_text(source, encoding="utf-8")
        for generation in ["20240101T000000", "20240102T000000"]:
            fixture(root, generation, args.stations, args.steps, args.density)
        results = {
            "machine": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version,
            "versions": {
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "xarray": xr.__version__,
                "netCDF4": netCDF4.__version__,
            },
            "baseline_revision": args.revision,
            "candidate": "working tree",
            "candidate_sha256": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in [Path("fewspy/cache/time_series_cache.py"), Path("fewspy/cache/_header_reader.py")]
            },
            "fixture": {"stations": args.stations, "steps": args.steps, "density": args.density, "seed": 42},
            "cache_conditions": "Warm filesystem caches; isolated processes; identical object lifecycles",
        }
        for implementation in ["old", "new"]:
            print(f"Benchmarking {implementation}: {args.stations} stations, density {args.density}", file=sys.stderr)
            output = subprocess.check_output(  # noqa: S603 - Runs this benchmark with generated local fixtures.
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker",
                    implementation,
                    "--baseline",
                    str(baseline),
                    "--root",
                    str(root),
                    "--stations",
                    str(args.stations),
                    "--runs",
                    str(args.runs),
                ],
                text=True,
            )
            results[implementation] = json.loads(output)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(args.output)


if __name__ == "__main__":
    main()
