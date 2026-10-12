# Time Series in FEWS PI format

See also: https://publicwiki.deltares.nl/display/FEWSDOC/Delft-Fews+Published+Interface+timeseries+Format+%28PI%29+Import

::: src.fewspy.time_series


## Available FEWS header identity

The default remains `series_key="location_parameter"`: two DataFrame column
levels, existing selection behavior, and one NetCDF file named `{parameter_id}.nc`.

All `series_key` arguments also accept the string enum `SeriesKey`, available
from `fewspy` and `fewspy.time_series`:

```python
from fewspy import SeriesKey

frame = time_series_set.to_df(series_key=SeriesKey.HEADER)
```

`SeriesKey.LOCATION_PARAMETER` is the default; `SeriesKey.HEADER` preserves the
available header identity. The strings `"location_parameter"` and `"header"`
remain supported. Invalid values raise `ValueError` before requests or file I/O.

Use `series_key="header"` explicitly to preserve the available header identity:

```python
frame = time_series_set.to_df(series_key="header")
time_series_set.to_netcdf(out_dir, series_key="header")
restored = fewspy.read_netcdf(nc_file, series_key="header")

time_series_set.to_parquet(parquet_file, series_key="header")
restored = fewspy.read_parquet(parquet_file, series_key="header")
```

`Header.series_identity("header")` defines the column levels in this order:
`module_instance_id`, `value_type`, `location_id`, `parameter_id`,
`time_series_type`, `time_step`, `qualifier_id`. The PI `type` field
(instantaneous/accumulative) remains separate from `timeSeriesType`.
Missing optional fields remain missing; fewspy does not infer their values.
PI API responses may omit `valueType` and `timeSeriesType`. Header mode preserves
all available identity fields but cannot distinguish series solely by information
that was not supplied. The PI `type` field is not a substitute for either field.

Timesteps use compact JSON with sorted attribute names, including multiplier,
divider, and ID when present. Qualifiers use JSON arrays, retaining the original
list order, repeated entries, and exact strings. No qualifiers (`None` or `[]`)
produce the identity `[]`; the stored header preserves the original representation.
This avoids ambiguities between, for example, `["a,b"]` and `["a", "b"]`.
Select a series with `frame[header.series_identity("header")]`.

Header-mode NetCDF files group stations only when the other six identity fields
match. With `file_naming="default"`, filenames contain percent-encoded JSON components in this order:
`parameter_qualifiers_timestep_valueType_moduleInstance_timeSeriesType.nc`.
This adapts the [FEWS Open Archive scalar naming pattern](https://publicwiki.deltares.nl/spaces/FEWSDOC/pages/112167200/22-2+Export+to+Delft-FEWS+Open+Archive).
This default naming includes module instance and time-series type so names do not depend
on what other series happen to be exported. Location IDs remain the station
coordinate. Each file also stores the complete headers in `fewspy_headers`,
a format marker, and values in the `value` variable. Identity is never inferred
from observed sampling intervals or replaced with a hash.

Custom NetCDF templates can use `{identity}` and `{parameter_id}`. Invalid or
excessively long names, duplicate full identities, case-insensitive filename
collisions, and attempts to replace files containing different headers raise
`ValueError` before writing. Shorten identifiers if the encoded filename exceeds
240 UTF-8 bytes. This is a fewspy format inspired by Open Archive, not an Open
Archive interchange implementation. Header-mode readers require explicit stored
headers and reject legacy NetCDF files without them rather than invent metadata.
Zipped header-mode NetCDF input reads every NetCDF member.

Parquet header mode embeds complete headers in pandas metadata, with positional
physical columns; `read_parquet(..., series_key="header")` reconstructs the set
without requiring a sidecar. NetCDF's low-level writer accepts DataFrames from
`to_df(series_key="header")`, including column selections, while their
`fewspy_headers` attributes remain available. Both formats retain the existing
`to_df()` reliable-value filtering; this does not add flag serialization.

Missing required fields in embedded Parquet headers raise `ValueError` naming
the affected column and missing fields. Optional header fields remain optional.

For asynchronous retrieval use
`api.get_time_series(..., parallel=True, series_key="header")` to retain every
series in each response. Requests remain concurrent. Pass the mode again to
conversion methods; it is an operation argument, not persistent set state.
Cache selection also accepts `series_key="header"` and returns all matching full
identities across the manifest's header-mode files. Location filtering does not
collapse series that share the same location and parameter.

## Time-series cache reads and lifecycle

`TimeSeriesCache` selects locations and time before loading values from
full-header NetCDF files. Existing `get_time_series()` calls benefit without
changing arguments. Complete header identities, original header dates,
`frame.attrs["fewspy_headers"]`, missing values, and inclusive pandas time
slicing (including partial dates such as `"2024-01"`) are preserved. Unusual
time axes, including unsorted or duplicate timestamps, use the original reader
and its existing behavior. Header mode still requires explicit FEWS metadata;
it does not infer headers from legacy files. The default `location_parameter`
mode retains its selection rules.

```python
from pathlib import Path
from fewspy.cache import TimeSeriesCache

with TimeSeriesCache.from_manifest_file(
    Path("cache/manifest.json"), metadata_cache_size=16
) as cache:
    frame = cache.get_time_series(
        "filter", "P", start_time="2024-01", end_time="2024-02",
        location_ids=["location"], series_key="header",
    )
```

The constructor and `from_manifest_file()` accept the optional keyword-only
`metadata_cache_size`, defaulting to 16. This is an LRU limit on retained
**file entries**, not a RAM limit. Use `0` to disable metadata reuse. Each entry
contains all validated headers, a location lookup, and the time axis of one
file; values and selection results are not cached. Metadata for a very large
file can therefore consume substantial memory. The small manifest/parameter
catalog and the separately computed `common_time_axis` are outside this limit.
Active readers may temporarily retain evicted or previous-generation metadata.
Returned DataFrames do not share mutable header metadata with the cache.

Construction opens each manifest dataset only to read its routing attributes,
then closes it immediately. Content decoding is deferred until that file is
used for values. On a header metadata miss the reader validates every header
in the matching file, including unselected locations. If any requested location
occurs in the file, it also performs the same complete xarray decoding check
that previously ran during construction, before returning selected data.
Files without requested locations retain only validated header metadata; a
later matching selection must still pass the full decoding check. No selected
data are returned if either check fails. This saves work when files contain
none of the requested locations; a selection using every file still needs all
decoding checks and may incur additional file-opening overhead.
Successful validation is reused only
with the bounded metadata entry for that immutable generation; eviction or
`metadata_cache_size=0` causes it to run again. Legacy reads and fallback reads
retain xarray decoding checks on every read.

`from_manifest_file()` and refresh retain complete manifest file-count, size
and SHA-256 validation. Content errors in unused files can now be reported
later, on their first read rather than at construction or refresh. A successful
refresh can therefore be followed by a content error when a new file is read;
that read raises instead of returning partial data or falling back to an old
generation. `common_time_axis` still opens and decodes all files on demand,
and is recomputed after successful refresh.

Concurrent cache reads and `refresh_if_changed()` are supported within a
process. Native NetCDF access is serialized across cache instances. Each read
captures one generation: an in-flight read may finish on the old generation,
and reads started after a successful refresh use the new generation. A failed
refresh leaves the previous snapshot and metadata usable. No file handles are
retained between reads. Use the context manager or call `close()` to release
metadata promptly. Closing is idempotent and does not wait for active reads;
those reads finish and close their own resources. New reads, refreshes, and
`common_time_axis` calls on a closed cache raise `RuntimeError`.

Cache publishers must publish immutable generation directories and replace the
manifest atomically. They must retain old files until all readers of that
generation have finished, including readers in other processes. A fixed
`Manifest.max_cache_count` alone does not guarantee this. Coordinate cleanup
externally and use `atomic_write(..., clean_old_caches=False)` when necessary.
Overwriting generation files in place or deleting files still needed by active
readers is outside the snapshot guarantee. Changing a manifest object after
constructing a cache does not modify its captured generation; publish a new
manifest and refresh instead.

The reproducible benchmark is `benchmarks/cache_performance.py`. It compares
constructor plus first read (including cleanup), repeated reads with changing locations, and refresh
plus subsequent read against a specified Git revision in separate processes.
Use small and large fixtures and both `--density 1` and `--density .05`.
It records individual timings, medians, p10/p90, versions, fixture parameters,
header/series reconstruction counts and logical file opens. When `psutil` is
available in the development environment, a separate sampling pass also records
native RSS and open files. RSS after closing may include memory retained by
Python or native allocators. These warm-filesystem measurements are library
measurements and do not predict dashboard rendering times.

Run from the repository root, for example:

```shell
pixi run python benchmarks/cache_performance.py --stations 21095 --steps 720 --runs 5 --output .tmp/large-dense.json
pixi run python benchmarks/cache_performance.py --stations 21095 --steps 720 --density .05 --runs 5 --output .tmp/large-sparse.json
```

For the small fixtures, replace the station and step counts with 128 and 168.
The default baseline is revision `0037f92fb43b9b503ff72376fb739965cb4f6309`;
`--revision` selects a different local Git revision. Each output includes the
candidate source-file SHA-256 digests and every individual timing. The raw
measurements from the initial selective-reader implementation are in
`benchmarks/results/cache-*.json`. The numbers and file-open counts below
predate deferred decoding; they are not measurements of that follow-up change.

On the recorded Windows 11 / Python 3.14.6 environment, five-run medians for
the dense 21,095-station, 720-timestep fixture were:

| Selection and lifecycle | Previous (s) | Selective cache (s) |
| --- | ---: | ---: |
| 20 locations, constructor + first read + cleanup | 1.213 | 0.199 |
| 20 changing locations, repeated read | 1.165 | 0.0145 |
| 20 locations, refresh + read | 1.208 | 0.208 |
| All locations and times, constructor + first read + cleanup | 2.737 | 2.667 |
| All locations and times, repeated read | 2.683 | 2.360 |
| All locations and times, refresh + read | 2.767 | 2.561 |

The narrow selection spans two days. In this fixture, repeated reads exceed the
5x target (approximately 81x). Instrumentation confirms 20 series reconstructed
per read instead of 21,095, and zero repeated header parses after the first
read. The first read still validates all 21,095 headers. Both implementations
perform two logical dataset opens for constructor plus first read and one for
a repeated read; the new cache retains no open files between reads.

In the separate changing-selection memory pass, sampled peak process RSS was
458 MB previously and 211 MB with the new cache, including approximately 158 MB
of initial process RSS. After closing, RSS was 236 MB and 172 MB respectively;
open-file counts returned to the initial count in both cases. The default
16-entry limit is configurable because these per-file metadata costs depend
on header count and content. These measurements demonstrate this fixture's
behavior, not a universal speed or memory guarantee. Consult the raw small,
large, dense, and sparse results for distributions and source checksums.


## Readable archive filenames

Choose archive-style names explicitly; existing naming remains the default:

```python
time_series_set.to_netcdf(
    out_dir,
    series_key="header",
    file_naming="archive",
    include_time_series_type=False,
)
```

The archive pattern is
`<parameterId>_[<qualifierIds>]_<timeStep>[_<valueType>]_<moduleInstanceId>.nc`.
Here `[_<valueType>]` denotes an optional segment; the brackets around qualifiers
are literal filename characters. Value type is included only when known.
Module instance is always included. Set `include_time_series_type=True` to append
`_<timeSeriesType>` before `.nc` only when that field is known. The full type is retained literally, including
spaces, for example `P_[]_hour-1_scalar_Import_external historical.nc`.
The suffix controls naming only: time-series type always participates in identity,
grouping, and metadata. If omitting it causes a collision, export raises an error.

Qualifiers are joined with underscores in header order and enclosed in literal
square brackets: `[q1_q2]`. Without qualifiers the segment is `[]`. When using
glob patterns, escape the brackets or use literal path matching. This is an explicit fewspy convention: the linked
FEWS documentation only illustrates a single qualifier and does not specify how
multiple qualifiers are joined. Underscores inside identifiers are preserved;
ambiguous combinations such as `["a_b", "c"]` and `["a", "b_c"]` cause an error
if their filenames collide, including when a previous export already exists.

An available `time_step.id` is used literally, such as `SETS60`. Otherwise the
name uses `<unit>-<multiplier>` (multiplier defaults to 1), optionally followed by
`-div<divider>`. Irregular steps use `nonequidistant`. These fallback tokens are
fewspy representations, not inferred FEWS timestep IDs. Original timestep
attributes remain unchanged in the metadata even when a naming token is shared.

Archive names contain no JSON or percent-encoding. Invalid filename characters,
control characters, reserved device names, overlong names and filename collisions
are rejected before files are written. Missing (`None`) value type and time-series
type are omitted, without placeholders or extra separators. For example, with
both types missing: `P_[]_hour-1_Import.nc`. Metadata retains `None`.
A missing module instance still uses the literal token `null`; a literal module
identifier `null` can collide with this token. Any filename collision causes
export to fail rather than overwrite a different series. Empty strings remain
invalid. Parameter and qualifier IDs must be nonempty.

The low-level `write_netcdf` function supports the same options. Custom templates
can include `{identity}` for the archive stem and `{parameter_id}` for the literal
parameter. Archive naming requires `series_key="header"`; the type-suffix option
requires archive naming. The reader is unchanged: it reconstructs headers from
`fewspy_headers`, never by splitting filenames. This option changes naming only
and does not implement FEWS's native archive metadata format.
