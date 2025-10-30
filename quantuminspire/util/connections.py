
from urllib.parse import urlparse

import requests
import logging

def add_protocol(url: str) -> str:
    """Add 'https://' protocol to the URL if not already present.
    Args:
        url: The URL to which to add the protocol.
    """
    parsed = urlparse(url)

    if parsed.scheme:
        logging.warn('It is not necessary to specify the protocol in the URL. \
The protocol will be determined automatically.')
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