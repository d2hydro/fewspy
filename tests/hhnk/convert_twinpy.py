#%%
from pathlib import Path
import pickle
import os

from TWINpy.app.TWIN_get_timeseries import TWIN_Timeserie


data_dir = Path(__file__).parent / "data"
os.environ["TWIN_BASE_URL"] = ""

with open(data_dir / "twin_response.pickle", "rb") as src:
    b = pickle.load(src)
# df = pd.read_pickle(data_dir / "twin_response.pickle")


#%%
from fewspy.time_series import TimeSeries, TimeSeriesSet, Header, Events

def convert_timeseries(time_series:TWIN_Timeserie, header_info: dict = {"type": "instantaneous", "time_step": {"unit": "nonequidistant"}}) -> TimeSeries:
    """Converts TWIN_Timeserie to fewspy.TimeSeriesSet

    Parameters
    ----------
    time_series : TWIN_Timeserie
    header_info : dict, optional
        Header-info missing in TWIN_Timeserie, by default {"type": "instantaneous", "time_step": {"unit": "nonequidistant"}}

    Returns
    -------
    TimeSeries
        _description_
    """
    header = {**time_series.ts_header, **header_info}
    header["miss_val"] = header.pop("missing_val")
    header["start_date"] = time_series.df.index.min()
    header["end_date"] = time_series.df.index.min()

    return TimeSeries(header=Header(**header), events=Events(time_series.df))
 
time_series_set = TimeSeriesSet(time_series = [convert_timeseries(i) for i in b.values()])
time_series_set.to_netcdf(out_dir=Path("netcdf"))
# %%
