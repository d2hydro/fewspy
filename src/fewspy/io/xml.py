
from lxml import objectify
from pathlib import Path
from fewspy.utils.conversions import snake_to_camel_case

def read_xml(xml_path: Path) -> dict:
    """Parse PI XML file to fewspy TimeSeriesSet

    Args:
        xml_path (Path): Path to xml-file

    Returns:
        TimeSeriesSet: fewspy time series set
    """
    
    xml_data = objectify.parse(xml_path)  # Parse XML data
    root = xml_data.getroot()  # Root element

    time_series_set = {"timeSeries": []}

    # Get children, filter out timezone.
    rootchildren = [child for child in root.getchildren() if child.tag.endswith("series")]

    # Loop over children (individual timeseries in the xml)
    for child in rootchildren:
        subchildren = child.getchildren()  # alle headers en en timevalues
        metadata = None
        data = []

        for subchild in subchildren:
            # Write header to dict
            if subchild.tag.endswith("header"):  # gewoonlijk eerste subchild is de header
                header_childs = subchild.getchildren()
                metadata = {}
                for item in header_childs:
                    key = item.tag.split("}")[-1]

                    item_keys = item.keys()

                    if len(item_keys) == 0:
                        metadata[key] = item.text
                    else:
                        metadata[key] = {}
                        for item_key, item_value in zip(item_keys, item.values()):
                            metadata[key][item_key] = item_value
            # Get event data
            else:
                data += [{k:v for k,v in zip(subchild.keys(), subchild.values())}]

        # add to time_series_set
        if "start_date" not in metadata:
            metadata["start_date"] = {"date": data[0]["date"], "time": data[0]["time"]}
        if "end_date" not in metadata:
            metadata["end_date"] = {"date": data[-1]["date"], "time": data[-1]["time"]}

        time_series_set["timeSeries"] += [{"header": metadata, "events": data}]

    return time_series_set
