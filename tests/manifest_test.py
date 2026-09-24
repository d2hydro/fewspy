from datetime import datetime

import pytest
from pydantic import ValidationError

from fewspy.cache.manifest import Coverage, FieldEndtry, Manifest


@pytest.mark.parametrize("end_day", [1, 2])
def test_coverage_rejects_non_increasing_dates(end_day):
    with pytest.raises(ValidationError, match="end_date must be after start_date"):
        Coverage(start_date=datetime(2026, 1, 2), end_date=datetime(2026, 1, end_day))


def test_coverage_expands_but_never_shrinks():
    coverage = Coverage()
    coverage.update_coverage(datetime(2026, 1, 2), datetime(2026, 1, 4))
    assert (coverage.start_date, coverage.end_date) == (datetime(2026, 1, 2), datetime(2026, 1, 4))

    coverage.update_coverage(datetime(2026, 1, 1), datetime(2026, 1, 5))
    coverage.update_coverage(datetime(2026, 1, 2), datetime(2026, 1, 3))
    assert (coverage.start_date, coverage.end_date) == (datetime(2026, 1, 1), datetime(2026, 1, 5))


@pytest.fixture
def manifest(tmp_path):
    cache_dir = tmp_path / "20260101T000000"
    path = cache_dir / "filter" / "level.nc"
    path.parent.mkdir(parents=True)
    # Manifest validation checks bytes, independently of the file format.
    path.write_bytes(b"original")
    return Manifest(
        filepath=tmp_path / "manifest.json",
        current_cache=cache_dir.name,
        expected_file_count=1,
        files=[FieldEndtry.from_file(path)],
    )


@pytest.mark.parametrize(
    ("damage", "message"),
    [("missing", "File does not exist"), ("size", "Size mismatch"), ("hash", "Hash mismatch")],
)
def test_manifest_detects_missing_or_corrupt_files(manifest, damage, message):
    path = manifest.files[0].path
    if damage == "missing":
        path.unlink()
    elif damage == "size":
        path.write_bytes(b"short")
    else:
        path.write_bytes(b"modified")
    with pytest.raises(ValueError, match=message):
        manifest.validate_files()


def test_manifest_detects_incomplete_file_list(manifest):
    manifest.expected_file_count = 2
    with pytest.raises(ValueError, match="Expected 2 files, but got 1"):
        manifest.validate_files()


def test_manifest_roundtrip_and_entry_lookup(manifest):
    manifest.atomic_write(manifest.filepath, clean_old_caches=False)
    restored = Manifest.from_file(manifest.filepath)
    restored.validate_files()
    assert restored.files == manifest.files
    assert restored.cache_dirs == [manifest.current_cache_dir]
    assert restored.get_entry("filter", "level") == manifest.files[0]
    with pytest.raises(ValueError, match="No entry found"):
        restored.get_entry("other_filter", "level")
    with pytest.raises(ValueError, match="No entry found"):
        restored.get_entry("filter", "other_parameter")
