from config import api


timezone_id = api.get_timezone_id()


def test_to_reference_set():
    assert timezone_id == "GMT+01:00"
