#%%
from pathlib import Path
import pandas as pd
import pickle
import os
from fewspy.time_series import TimeSeries, TimeSeriesSet, Header, Events
from TWINpy.app.TWIN_get_timeseries import TWIN_Timeserie


data_dir = Path(__file__).parent / "data"
os.environ["TWIN_BASE_URL"] = ""

with open(data_dir / "twin_response.pickle", "rb") as src:
    b = pickle.load(src)
# df = pd.read_pickle(data_dir / "twin_response.pickle")


#%%
def convert_timeseries(time_series:TWIN_Timeserie, header_info: dict = {"type": "instantaneous", "time_step": {"unit": "nonequidistant"}}) -> TimeSeries:
    header = {**time_series.ts_header, **header_info}
    header["miss_val"] = header.pop("missing_val")
    header["start_date"] = time_series.df.index.min()
    header["end_date"] = time_series.df.index.min()

    return TimeSeries(header=Header(**header), events=Events(time_series.df))
 
time_series_set = TimeSeriesSet(time_series = [convert_timeseries(i) for i in b.values()])


with open(data_dir / "twin_fewspy_ts.pickle", 'wb') as handle:
    pickle.dump(time_series_set, handle, protocol=pickle.HIGHEST_PROTOCOL)



# %%
