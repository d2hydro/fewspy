# %%
import fewspy
from config import data_dir


xml_file = data_dir.joinpath("io", "sample.xml")
json_file = data_dir.joinpath("io", "sample.json")
nc_file = data_dir.joinpath("io", "sample.nc")

xml_ts = fewspy.read_xml(xml_file)
json_ts = fewspy.read_json(json_file)
nc_ts = fewspy.read_netcdf(nc_file)
