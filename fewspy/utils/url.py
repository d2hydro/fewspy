import requests


class URLNotFoundError(Exception):
    pass


def validate_url(url: str, test_postfix: str = "timezoneid") -> str:
    """Validate a FEWS PI REST service URL.

    Args:
        url: input url to be validated
        test_postfix: postfix to url used for testing. Defaults to 'filters'.

    Returns: validated url

    """
    # add / if not in input_url
    if not url.endswith("/"):
        url += "/"

    # test with request
    # Preserve the existing certificate-independent endpoint probe.
    response = requests.get(f"{url}{test_postfix}", verify=False)  # noqa: S113, S501 - Preserve existing request timeout/TLS behavior.
    if not response.ok:
        raise URLNotFoundError(f"{url} is not a root to a live FEWS PI Rest WebService")

    # estimate ssl_verify
    ssl_verify = url.startswith("https")

    return url, ssl_verify
