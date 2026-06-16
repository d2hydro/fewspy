# %%
from pathlib import Path
import geopandas as gpd
from config import api

ATTRIBUTES = ["MPN_IDENT", "MPN_BRON"]
DATA_PATH = Path(__file__).parent / "data"
REFERENCE_GPKG = DATA_PATH / "locations.gpkg"
locations_reference = gpd.read_file(REFERENCE_GPKG).set_index("location_id")


def _write_reference_set():
    locations.to_file(REFERENCE_GPKG, driver="GPKG")


def test_pi_json_to_reference_set():
    locations = api.get_locations(attributes=ATTRIBUTES, document_format="PI_JSON")
    cols = [i for i in locations.columns if i not in ["location_name", "geometry"]]
    assert locations[cols].sort_index().equals(locations_reference[cols].sort_index())


def test_geo_json_to_reference_set():
    locations = api.get_locations(attributes=ATTRIBUTES, document_format="GEO_JSON")
    cols = [i for i in locations.columns if i not in ["location_name", "geometry"]]
    assert locations[cols].sort_index().equals(locations_reference[cols].sort_index())
