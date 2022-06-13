from .conversions import snake_to_camel_case, datetime_to_fews_str

DATETIME_KEYS = ["start_time", "end_time"]
API_KEYS = [
    "document_format",
    "document_version",
    "end_time",
    "filter_id",
    "include_location_relations",
    "location_ids",
    "only_headers",
    "parameter_ids",
    "qualifier_ids",
    "attributes",
    "show_statistics",
    "start_time",
    "thinning",
]


def flatten_list(list_of_lists: list) -> list:
    """
    Flattens a list of lists

    Args:
        list_of_lists (list): List of lists

    Returns:
        list: flattened list

    """

    return [i for j in list_of_lists for i in j]


def parameters_to_fews(parameters: dict) -> dict:
    """
    Prepare Python API dictionary for FEWS API request

    Args:
        parameters (dict): parameters passed by Python API

    Returns:
        dict: parameters prepard for FEWS API request

    """

    def _convert_kv(k: str, v) -> dict:
        if k in DATETIME_KEYS:
            v = datetime_to_fews_str(v)
        elif k == "attributes":
            k = "show_attributes"
            v = True
        k = snake_to_camel_case(k)

        return k, v

    args = (_convert_kv(k, v) for k, v in parameters.items() if k in API_KEYS)
    args = (i for i in args if i[1] is not None)
    return {i[0]: i[1] for i in args}
