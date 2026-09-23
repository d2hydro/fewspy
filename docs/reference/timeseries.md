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

For asynchronous retrieval use
`api.get_time_series(..., parallel=True, series_key="header")` to retain every
series in each response. Requests remain concurrent. Pass the mode again to
conversion methods; it is an operation argument, not persistent set state.
Cache selection also accepts `series_key="header"` and returns all matching full
identities across the manifest's header-mode files. Location filtering does not
collapse series that share the same location and parameter.


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
