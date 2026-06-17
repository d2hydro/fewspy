def test_to_reference_set(api):
    timezone_id = api.get_timezone_id()
    assert timezone_id == "GMT+01:00"
