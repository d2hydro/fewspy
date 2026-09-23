# %%
import pickle
from pathlib import Path

from netCDF4 import Dataset

from fewspy.time_series import TimeSeriesSet

DATA_PATH = Path(__file__).parent / "data"
tmx_tss = DATA_PATH.joinpath("io", "tmx_fewspy_ts.pickle")
tmpdir = DATA_PATH.joinpath("tmx_to_netcdf")


def test_tmx(tmpdir):

    # open pickle
    with tmx_tss.open("rb") as src:
        time_series_set: TimeSeriesSet = pickle.load(src)  # noqa: S301 - Trusted repository fixture.

    # to_netcdf settings
    out_dir = Path(tmpdir).joinpath("tmx_to_netcdf")
    global_attributes = {
        "institution": "HHNK",
        "source": "TMX",
        "title": "TMX export",
    }

    time_series_set.to_netcdf(out_dir=out_dir, global_attributes=global_attributes)

    # check if netcdf files exist
    assert out_dir.joinpath("CL.berekend.nc").exists()
    assert out_dir.joinpath("EGVms_m.meting.nc").exists()
    assert out_dir.joinpath("H.meting.nc").exists()
    assert out_dir.joinpath("HTPB.meting.nc").exists()
    assert out_dir.joinpath("Hz.meting.nc").exists()
    assert out_dir.joinpath("Inlaat.stand.meting.nc").exists()
    assert out_dir.joinpath("LTPB.meting.nc").exists()
    assert out_dir.joinpath("O2.geh.meting.nc").exists()
    assert out_dir.joinpath("P.meting.1m.nc").exists()
    assert out_dir.joinpath("PB.meting.nc").exists()
    assert out_dir.joinpath("Q.berekend.nc").exists()
    assert out_dir.joinpath("Q.meting.nc").exists()
    assert out_dir.joinpath("Stuw.stand.meting.nc").exists()
    assert out_dir.joinpath("T.water.meting.nc").exists()

    for path in out_dir.glob("*.nc"):
        with Dataset(path) as dataset:
            assert dataset.source == "TMX"
            assert dataset.title == "TMX export"
