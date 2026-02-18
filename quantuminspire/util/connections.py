from urllib.parse import urlparse

import requests
import typer


def add_protocol(url: str) -> str:
    """Add 'https://' or 'http://' protocol to the URL if not already present.
    Args:
        url: The URL to which to add the protocol.
    """
    parsed = urlparse(url)

    if parsed.scheme:
        typer.echo(
            typer.style(
                "It is not necessary to specify the protocol in the URL. \
The protocol will be determined automatically.",
                fg=typer.colors.YELLOW,
            )
        )
        return url

    # Try HTTPS first
    try:
        response = requests.head(f"https://{url}/docs", timeout=3, allow_redirects=True)
        if response.status_code < 400:
            return f"https://{url}"
        else:
            return f"http://{url}"
    except requests.RequestException:
        # Fall back to HTTP
        return f"http://{url}"
