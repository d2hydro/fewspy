import requests
from typing import Optional, Tuple, Union


class URLNotFoundError(Exception):
    pass


def validate_url(
    url: str,
    test_postfix: str = "timezoneid",
    cert: Optional[Union[str, Tuple[str, str]]] = None,
) -> str:
    """

    Args:
        url: input url to be validated
        test_postfix: postfix to url used for testing. Defaults to 'timezoneid'.

    Returns: validated url

    """

    # add / if not in input_url
    if not url.endswith("/"):
        url += "/"

    # test with request
    try:
        response = requests.get(f"{url}{test_postfix}", verify=False, cert=cert)
    except requests.RequestException as err:
        raise URLNotFoundError(
            f"{url} is not a root to a live FEWS PI Rest WebService"
        ) from err

    # 401/403 means the endpoint exists but is protected.
    if response.status_code not in (401, 403) and not response.ok:
        raise URLNotFoundError(f"{url} is not a root to a live FEWS PI Rest WebService")

    # estimate ssl_verify
    if url.startswith("https"):
        ssl_verify = True
    else:
        ssl_verify = False

    return url, ssl_verify
