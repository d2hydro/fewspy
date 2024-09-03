from datetime import datetime
from shapely.geometry import Point
import numpy as np
from typing import List

GEODATUM_MAPPING = {
    "WGS 1984": "epsg:4326",
    "Ordnance Survey Great Britain 1936": "epsg:4277",
    "TWD 1967": "epsg:3828",
    "Gauss Krueger Meridian2": None,
    "Gauss Krueger Meridian3": None,
    "Gauss Krueger Austria M34": "epsg:18009",
    "Gauss Krueger Austria M31": "epsg:18008",
    "Rijks Driehoekstelsel": "epsg:28992",
    "JRC": "epsg:3040",
    "DWD": None,
    "KNMI Radar": None,
    "CH1903": "epsg:4149",
    "PAK1": None,
    "PAK2": None,
    "SVY21": "epsg:3414",
}


def camel_to_snake_case(camel_case: str) -> str:
    """
    Convert camelCase to snake_case

    Args:
        camel_case (str): sentence in camelCase (e.g. myInputVariable)

    Returns:
        str: converted sentence in snake_case (in example my_input_variable)

    """

    return "".join(["_" + i.lower() if i.isupper() else i for i in camel_case]).lstrip(
        "_"
    )


def snake_to_camel_case(snake_case: str) -> str:
    """
    Convert snake_case to camelCase

    Args:
        snake_case (str): sentence in snake_case (in example my_input_variable)

    Returns:
        str: converted sentence in camelCase (e.g. myInputVariable)

    """

    words = snake_case.split("_")
    return words[0] + "".join(i.title() for i in words[1:])


def dict_to_datetime(data: dict) -> datetime:
    """
    Convert a FEWS PI datetime dict to datetime object

    Args:
        data (dict): FEWS PI datetime (e.g. {'date': '2022-05-01', 'time': '00:00:00'})

    Returns:
        datetime: Converted datetime object (in example datetime.datetime(2022, 5, 1, 0, 0))

    """

    if "time" in data.keys():
        time = data["time"]
    else:
        time = "00:00:00"

    date_time = datetime.fromisoformat(f'{data["date"]}T{time}')

    return date_time


def datetime_to_fews_str(date_time: datetime) -> str:
    """
    Convert a FEWS PI datetime dict to datetime object

    Args:
        date_time (datetime): datetime object (e.g. datetime.datetime(2022, 5, 1, 0, 0))


    Returns:
        datetime: Converted datetime for FEWS REST API format  %Y-%m-%dT%H:%M:%SZ
        (in example 2022-05-01T00:00:00Z)

    """

    return date_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def xy_array_to_point(xy_array: np.ndarray) -> List[Point]:
    return [Point(i.astype(float)) for i in xy_array]


def attributes_to_array(attribute_values: np.ndarray, attributes: list) -> np.ndarray:
    def _get_values(x, attributes):
        selection = {i["id"]: i["value"] for i in x if i["id"] in attributes}
        return [selection[i] if i in selection.keys() else None for i in attributes]

    return np.array([_get_values(i, attributes) for i in attribute_values])


def geo_datum_to_crs(geo_datum: str) -> str:
    if geo_datum.startswith("UTM"):
        epsg_code = 32600
        zone = int(geo_datum[3:5].lstrip("0"))
        epsg_code += int(zone)
        if geo_datum[-1] == "S":
            epsg_code += 100
        crs = f"epsg:{epsg_code}"
    elif geo_datum.lower().startswith("epsg"):
        crs = geo_datum.lower()
    elif geo_datum in GEODATUM_MAPPING.keys():
        crs = GEODATUM_MAPPING[geo_datum]
    else:
        crs = None
    return crs
