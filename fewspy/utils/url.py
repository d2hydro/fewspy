import requests


class URLNotFoundError(Exception):
    pass


def validate_url(
    url: str,
    test_postfix: str = "timezoneid",
    cert: str | tuple[str, str] | None = None,
    ssl_verify: bool | str | None = None,
) -> tuple[str, bool | str]:
    """Validate a FEWS PI REST service URL.

    Args:
        url: input url to be validated
        test_postfix: postfix to url used for testing. Defaults to 'timezoneid'.
        cert: client certificate path or certificate/key pair passed to requests.
        ssl_verify: SSL verification setting used for the test request. Inferred from
            the URL scheme when None.

    Returns: validated URL and SSL verification setting.

    """
    # add / if not in input_url
    if not url.endswith("/"):
        url += "/"

    # verify TLS certificates for https endpoints, matching the returned ssl_verify
    if ssl_verify is None:
        ssl_verify = url.startswith("https")

    # test with request
    try:
        response = requests.get(f"{url}{test_postfix}", verify=ssl_verify, cert=cert)  # noqa: S113 - Preserve existing request timeout behavior.
    except requests.RequestException as err:
        raise URLNotFoundError(f"{url} is not a root to a live FEWS PI Rest WebService") from err

    # 401/403 means the endpoint exists but is protected.
    if response.status_code not in (401, 403) and not response.ok:
        raise URLNotFoundError(f"{url} is not a root to a live FEWS PI Rest WebService")

    return url, ssl_verify
