#%%
import fewspy
from datetime import datetime, timedelta
import logging
import requests
import json
from xml.dom.minidom import parseString
from xml.dom import minidom


for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

base_url = r"https://fews.hhnk.nl/FewsWebServices/rest/fewspiservice/v1"
base_url = r"http://localhost:8080/FewsWebServices/rest/fewspiservice/v1"
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


logger = logging.getLogger(__name__)
api = fewspy.Api(url=base_url, logger=logger)


start_time = datetime(2025,4,1)
end_time = start_time + timedelta(days=21)
location_ids = ["CMB_03751-21","CMB_6100-04"]
parameter_ids = ["vullingsgraad"]

ts = api.get_time_series(
    filter_id="VullingsgraadOutput",
    location_ids=location_ids,
    parameter_ids=parameter_ids,
    start_time=start_time,
    end_time=end_time

    )


# %%get JSON
url = f"{base_url}/timeseries?filterId=VullingsgraadOutput&locationIds=CMB_03751-21&locationIds=CMB_6100-04&parameterIds=vullingsgraad&startTime=2025-04-01T00%3A00%3A00Z&endTime=2025-04-22T00%3A00%3A00Z&onlyHeaders=False&omitMissing=True&showStatistics=False&documentFormat=PI_JSON"
response = requests.get(url)
response.raise_for_status()
with open("sample.json", "w") as f:
    json.dump(response.json(), f, indent=4)

# %%get XML
def remove_whitespace_nodes(node):
    remove_list = []
    for child in node.childNodes:
        if child.nodeType == minidom.Node.TEXT_NODE and child.data.strip() == "":
            remove_list.append(child)
        elif child.hasChildNodes():
            remove_whitespace_nodes(child)
    for node in remove_list:
        node.parentNode.removeChild(node)
            


url = f"{base_url}/timeseries?filterId=VullingsgraadOutput&locationIds=CMB_03751-21&locationIds=CMB_6100-04&parameterIds=vullingsgraad&startTime=2025-04-01T00%3A00%3A00Z&endTime=2025-04-22T00%3A00%3A00Z&onlyHeaders=False&omitMissing=True&showStatistics=False"

response = requests.get(url)
response.raise_for_status()
with open("sample.xml", "w") as f:
    dom = parseString(response.text)
    remove_whitespace_nodes(dom)
    f.write(dom.toprettyxml(indent="  "))

# %%get NetCDF
url = f"{base_url}/timeseries?filterId=VullingsgraadOutput&locationIds=CMB_03751-21&locationIds=CMB_6100-04&parameterIds=vullingsgraad&startTime=2025-04-01T00%3A00%3A00Z&endTime=2025-04-22T00%3A00%3A00Z&onlyHeaders=False&omitMissing=True&showStatistics=False&documentFormat=PI_NETCDF"

response = requests.get(url)
response.raise_for_status()

with open("sample.zip", "wb") as f:
    f.write(response.content)

# %%
