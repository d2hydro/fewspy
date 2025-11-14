# %%
from fewspy.time_series import TimeSeriesSet
import pickle
from pathlib import Path


DATA_PATH = Path(__file__).parent / "data"
twinpy_tss = DATA_PATH.joinpath("io", "twin_fewspy_ts.pickle")

with open(twinpy_tss, "rb") as src:
    time_series_set: TimeSeriesSet = pickle.load(src)

out_dir = DATA_PATH.joinpath("io", "twinpy_to_netcdf")
global_attributes = {
    "institution": "HHNK",
    "source": "TWINpy",
    "title": "TWINpy export",
}

time_series_set.to_netcdf(out_dir=out_dir, global_attributes=global_attributes)
