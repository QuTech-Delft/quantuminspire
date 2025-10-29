
from urllib.parse import urlparse

import requests


def add_protocol(url: str) -> str:
    """Add 'https://' protocol to the URL if not already present.
    Args:
        url: The URL to which to add the protocol.
    """
    parsed = urlparse(url)

    if parsed.scheme:
        if parsed.scheme is 'http':
            print("WARNING: Using 'http' protocol is not allowed. Consider using 'https'.")
        return url

    # Try HTTPS first
    try:
        response = requests.head(f"https://{url}", timeout=3, allow_redirects=True)
        if response.status_code < 400:
            return f"https://{url}"
    except requests.RequestException:
        pass

    # Fall back to HTTP
    return f"http://{url}"