# Time Series in FEWS PI format

See also: https://publicwiki.deltares.nl/display/FEWSDOC/Delft-Fews+Published+Interface+timeseries+Format+%28PI%29+Import

::: src.fewspy.time_series


## Full FEWS series identity

The default remains `series_key="location_parameter"`: two DataFrame column
levels, existing selection behavior, and one NetCDF file named `{parameter_id}.nc`.

Use `series_key="header"` explicitly for full identity:

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

Timesteps use compact JSON with sorted attribute names, including multiplier,
divider, and ID when present. Qualifiers use JSON arrays, retaining the original
list order, repeated entries, and exact strings. No qualifiers (`None` or `[]`)
produce the identity `[]`; the stored header preserves the original representation.
This avoids ambiguities between, for example, `["a,b"]` and `["a", "b"]`.
Select a series with `frame[header.series_identity("header")]`.

Header-mode NetCDF files group stations only when the other six identity fields
match. Filenames contain percent-encoded JSON components in this order:
`parameter_qualifiers_timestep_valueType_moduleInstance_timeSeriesType.nc`.
This adapts the [FEWS Open Archive scalar naming pattern](https://publicwiki.deltares.nl/spaces/FEWSDOC/pages/112167200/22-2+Export+to+Delft-FEWS+Open+Archive).
Fewspy always includes module instance and time-series type so names do not depend
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
