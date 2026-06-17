# %%
import geopandas as gpd
import pytest

ATTRIBUTES = ["MPN_IDENT", "MPN_BRON"]


@pytest.fixture(scope="module")
def locations_reference(data_dir):
    return gpd.read_file(data_dir / "locations.gpkg").set_index("location_id")


def _write_reference_set(api, data_dir):
    locations = api.get_locations(attributes=ATTRIBUTES)
    reference_gpkg = data_dir / "locations.gpkg"
    locations.to_file(reference_gpkg, driver="GPKG")


def test_pi_json_to_reference_set(api, locations_reference):
    locations = api.get_locations(attributes=ATTRIBUTES, document_format="PI_JSON")
    cols = [i for i in locations_reference.columns if i != "geometry"]
    assert locations[cols].sort_index().equals(locations_reference[cols].sort_index())


def test_geo_json_to_reference_set(api, locations_reference):
    locations = api.get_locations(attributes=ATTRIBUTES, document_format="GEO_JSON")
    cols = [i for i in locations_reference.columns if i != "geometry"]
    assert locations[cols].sort_index().equals(locations_reference[cols].sort_index())
