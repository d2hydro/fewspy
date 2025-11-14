import requests


class URLNotFoundError(Exception):
    pass


def validate_url(url: str, test_postfix: str = "timezoneid") -> str:
    """

    Args:
        url: input url to be validated
        test_postfix: postfix to url used for testing. Defaults to 'filters'.

    Returns: validated url

    """

    # add / if not in input_url
    if not url.endswith("/"):
        url += "/"

    # test with request
    response = requests.get(f"{url}{test_postfix}", verify=False)
    if not response.ok:
        raise URLNotFoundError(f"{url} is not a root to a live FEWS PI Rest WebService")

    # estimate ssl_verify
    if url.startswith("https"):
        ssl_verify = True
    else:
        ssl_verify = False

    return url, ssl_verify
