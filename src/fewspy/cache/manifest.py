import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path
from pydantic import BaseModel, field_validator
from fewspy import __version__ as fewspy_version
from fewspy.time_series import TimeSeriesSet


class FieldEndtry(BaseModel):
    path: Path
    nbytes: int
    sha256: str

    @property
    def name(self) -> str:
        return self.path.name

    @classmethod
    def _sha256(cls, path: Path) -> str:
        with path.open("rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest()

    @field_validator("nbytes")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("nbytes must be non-negative")
        return v

    @classmethod
    def from_file(cls, path: Path) -> "FieldEndtry":
        return cls(path=path, nbytes=path.stat().st_size, sha256=cls._sha256(path))


class Coverage(BaseModel):
    start_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None

    @field_validator("end_date")
    @classmethod
    def check_start_before_end(cls, v, values):
        start_date = values.data["start_date"]
        if start_date is not None and v <= start_date:
            raise ValueError("end_date must be after start_date")
        return v

    def update_coverage(self, start_date: datetime.datetime, end_date: datetime.datetime):
        """Udate coverage start_date and end_date if the provided times are outside the current

        Parameters
        ----------
        start_date : datetime.datetime
           new start time to check
        end_date : datetime.datetime
            new end time to check
        """

        # update start_date if provided start_date is earlier or current is None
        if self.start_date is None:
            self.start_date = start_date
        elif start_date < self.start_date:
            self.start_date = start_date
        # update end_date if provided end_date is later or current is None
        if self.end_date is None:
            self.end_date = end_date
        elif end_date > self.end_date:
            self.end_date = end_date

    def update_coverage_from_timeserieset(self, tss: TimeSeriesSet):
        for ts in tss.time_series:
            self.update_coverage(start_date=ts.header.start_date, end_date=ts.header.end_date)


class Manifest(BaseModel):
    filepath: Path | None = None
    current_cache: str
    expected_file_count: int = 0
    max_cache_count: int = 3
    cache_dirs: list[Path] = []
    current_coverage: Coverage = Coverage()
    files: list[FieldEndtry] = []
    fewspy_version: str = fewspy_version

    @classmethod
    def current_cache_from_datetime(cls, current_cache_datetime) -> str:
        return current_cache_datetime.strftime("%Y%m%dT%H%M%S")

    @property
    def current_cache_datetime(self) -> datetime.datetime:
        return datetime.datetime.strptime(self.current_cache, "%Y%m%dT%H%M%S")

    @property
    def current_cache_dir(self) -> Path:
        if self.filepath is None:
            return None
        else:
            return self.filepath.parent.joinpath(self.current_cache)

    @classmethod
    def from_file(cls, filepath: Path, **kwargs) -> "Manifest":
        with open(filepath, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            for k, v in kwargs.items():
                json_data[k] = v
            return cls.model_validate(json_data)

    def validate_files(self):
        """Validate file cache on expected number of files, filex existence, size and hash"""

        # Validate that the number of files matches the expected count
        if len(self.files) != self.expected_file_count:
            raise ValueError(f"Expected {self.expected_file_count} files, but got {len(self.files)}")

        # Validate each file's existence, size, and hash
        errors = []
        for file_entry in self.files:
            # Check if file exists
            if not file_entry.path.exists():
                errors.append(f"File does not exist: {file_entry.path}")
                continue
            # Check file size
            actual_size = file_entry.path.stat().st_size
            if actual_size != file_entry.nbytes:
                errors.append(f"Size mismatch for {file_entry.path}: expected {file_entry.nbytes}, got {actual_size}")
                continue
            # Check file hash
            actual_hash = FieldEndtry._sha256(file_entry.path)
            if actual_hash != file_entry.sha256:
                errors.append(f"Hash mismatch for {file_entry.path}: expected {file_entry.sha256}, got {actual_hash}")
        if errors:
            raise ValueError("File validation errors:\n" + "\n".join(errors))

    def clean_cache_dirs(self):
        """Clean all directories in root_dir except those in cache_dirs"""
        # Exclude current_cache from deletion

        current_cache_dir = self.current_cache_dir
        root_dir = current_cache_dir.parent
        remove_candidates = [
            d for d in root_dir.glob("*") if d.is_dir() and (d != current_cache_dir) and (d not in self.cache_dirs)
        ]  # make sure we don't do current cache
        for i in remove_candidates:
            if i is not self.current_cache_dir:  # extra check
                shutil.rmtree(i, ignore_errors=True)

    def update_cache_dirs(self):
        """Update cache_dirs list with current_cache_dir if not already present"""
        if self.current_cache_dir is not None and self.current_cache_dir not in self.cache_dirs:
            self.cache_dirs.append(self.current_cache_dir)

        self.cache_dirs = sorted(self.cache_dirs, reverse=True)[: self.max_cache_count]

    def atomic_write(self, filepath: Path, clean_old_caches: bool = True):
        """Atomic replacement of (an existing) manifest file

        Parameters
        ----------
        filepath : Path
            Path to (existing) manifest-file to write to
        clean_old_caches : bool, optional
            If True (default) clean old cache directories, by default True
        """

        # store filepath
        self.filepath = filepath
        tmp_filepath = filepath.with_name(f".{filepath.stem}.tmp.json")

        # Validate files before writing
        self.validate_files()

        # make sure we have a clean cache_dirs list
        self.update_cache_dirs()

        # atomic write data
        with open(tmp_filepath, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
            f.flush()  # Python to kernel
            os.fsync(f.fileno())  # Ensure data is written to disk
        os.replace(tmp_filepath, filepath)  # atomic replace

        # clean old cache dirs
        if clean_old_caches:
            self.clean_cache_dirs()
