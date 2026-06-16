# Changelog

## 2026.5.0

Changes since `2026.4.0`.

### Added
- Support in tests for reading FEWS PI XML files that contain only headers and no events.
- Sample XML fixture for header-only time series parsing.

### Changed
- Migrated time series dataclasses to `pydantic.dataclasses` and tightened type hints across the time series models.
- Made `module_instance_id`, `version`, and `time_zone` explicitly optional in the public models.
- Updated NetCDF reading to warn when `time_series_type` is omitted and to default to `instantaneous`.
- Relaxed XML and NetCDF test expectations so header start and end dates only need to cover the event range.

### Fixed
- Stopped deriving XML `start_date` and `end_date` from events when an input series has no events.
- Returned a correctly shaped empty events DataFrame when parsing empty event lists.
- Fixed string coercion in `Header.from_dict()`.
