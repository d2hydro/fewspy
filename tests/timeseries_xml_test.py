# %%
from pathlib import Path
from fewspy.time_series import TimeSeries, Events, Header, TimeSeriesSet
import pandas as pd


DATA_PATH = Path(__file__).parent / "data"

time_series_set_xml = DATA_PATH / "normal_test_series.xml"

time_series_set = TimeSeriesSet.read_xml(time_series_set_xml)
# %%

events = time_series_set.time_series[0].events
header = time_series_set.time_series[0].header
time_series = time_series_set.time_series[0]
# %%
EVENT_FLAG_TEMPLATE = '<event date="{date}" time="{time}" value="{value}" flag="{flag}" />'
EVENT_TEMPLATE = '<event date="{date}" time="{time}" value="{value}" />'
TIME_ZONE_TEMPLATE = "<timeZone>{time_zone}</timeZone>\n"
HEAD = '<?xml version="1.0" ?>\n<TimeSeries xmlns="http://www.wldelft.nl/fews/PI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.wldelft.nl/fews/PI http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd" version="1.22">\n'

def event_to_string(x):
    kwargs = dict(date=x.name.strftime("%Y-%m-%d"), time=x.name.strftime("%H:%M:%S"), value=x["value"])
    if pd.isna(x.flag):
        return EVENT_TEMPLATE.format(**kwargs)
    else:
        kwargs["flag"] = x["flag"]
        return EVENT_TEMPLATE.format(**kwargs)
    
def events_to_string(events: Events, indent=2):
    return f"{'\t'*indent}\n".join(events.apply((lambda x : event_to_string(x)), axis=1))

def header_to_string(header: Header, indent=2):
    return_str = f"""{'\t'*indent}<header>
{'\t'*(indent+1)}<type>instantaneous</type>
{'\t'*(indent+1)}<moduleInstanceId>{header.module_instance_id}</moduleInstanceId>
{'\t'*(indent+1)}<locationId>{header.location_id}</locationId>
{'\t'*(indent+1)}<parameterId>{header.parameter_id}</parameterId>"""

    if header.qualifier_id is not None:
        if not isinstance(header.qualifier_id, list):
            raise TypeError("self.qualifier_ids should be of type list.")
        # Qualifier can have multiple lines.
        return_str = "\n".join(
            [
                return_str,
                (f"{'\t'*(indent+1)}<qualifierId>{{}}</qualifierId>\n" * len(header.qualifier_id))
                .format(*header.qualifier_id)
                .rstrip("\n"),
            ]
        )

    if header.time_step is not None:
            return_str = f"""{return_str}
    {'\t'*(indent+1)}<timeStep unit="{header.time_step['unit']}" multiplier="{header.time_step['multiplier']}"/>"""

            return_str = f"""{return_str}
    {'\t'*(indent+1)}<missVal>{header.miss_val}</missVal>
    {'\t'*indent}</header>"""
    return return_str

def time_series_to_string(time_series: TimeSeries, indent=1):
    return f"""{'\t'*indent}<series>
{header_to_string(time_series.header)}{events_to_string(time_series.events)}{'\t'*indent}
</series>
""" 

