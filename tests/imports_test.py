import subprocess
import sys

import pytest

from fewspy.time_series import TimeStepDict


def test_time_step_dict_preserves_optional_fields():
    assert TimeStepDict(unit="nonequidistant") == {"unit": "nonequidistant"}
    assert TimeStepDict(unit="second", multiplier=60, divider=None) == {
        "unit": "second",
        "multiplier": 60,
        "divider": None,
    }


@pytest.mark.parametrize(
    "module",
    [
        "fewspy.time_series",
        "fewspy.io.write_netcdf",
        "fewspy.cache.time_series_cache",
    ],
)
def test_import_in_fresh_interpreter(module):
    """Catch import cycles without relying on pytest's already loaded modules."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import {module}; "
            "from fewspy.time_series import Header, TimeStepDict; "
            "from fewspy._header import Header as InternalHeader, "
            "TimeStepDict as InternalTimeStepDict; "
            "assert Header is InternalHeader; "
            "assert TimeStepDict is InternalTimeStepDict",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
