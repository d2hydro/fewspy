# %%
from fewspy.time_series import TimeSeriesSet
import pickle
from pathlib import Path


DATA_PATH = Path(__file__).parent / "data"
twinpy_tss = DATA_PATH.joinpath("io", "twin_fewspy_ts.pickle")
tmpdir = DATA_PATH.joinpath("twinpy_to_netcdf")


def test_twinpy(tmpdir):

    # open pickle
    with open(twinpy_tss, "rb") as src:
        time_series_set: TimeSeriesSet = pickle.load(src)

    # to_netcdf settings
    out_dir = Path(tmpdir).joinpath("twinpy_to_netcdf")
    global_attributes = {
        "institution": "HHNK",
        "source": "TWINpy",
        "title": "TWINpy export",
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
