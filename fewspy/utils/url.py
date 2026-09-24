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
def validate_url(url: str, test_postfix: str = "timezoneid") -> str:
    """Validate a FEWS PI REST service URL.

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
        response = requests.get(f"{url}{test_postfix}", verify=False, cert=cert) # noqa: S113, S501 - Preserve existing request timeout/TLS behavior.
    except requests.RequestException as err:
        raise URLNotFoundError(
            f"{url} is not a root to a live FEWS PI Rest WebService"
        ) from err

    # 401/403 means the endpoint exists but is protected.
    if response.status_code not in (401, 403) and not response.ok:
        raise URLNotFoundError(f"{url} is not a root to a live FEWS PI Rest WebService")
    
    # estimate ssl_verify
    ssl_verify = url.startswith("https")

    return url, ssl_verify
