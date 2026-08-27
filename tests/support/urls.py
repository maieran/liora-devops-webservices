"""
Helpers function for constructing and comparing HTTP URLs.
"""

from urllib.parse import ParseResult, urljoin, urlparse

SUPPORTED_SCHEMES = {"http", "https"}


def normalize_base_url(base_url: str) -> str:
    """Validate and normalize a base URL."""

    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("Base URL must not be empty.")
    
    normalized = base_url.strip().rstrip("/")
    parsed = urlparse(normalized)

    if parsed.scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            "Base URL must use http or https."
        )
    
    if not parsed.hostname:
        raise ValueError(
            "Base URL must contain a hostname "
        )

    return normalized

def join_url(base_url: str, path: str) -> str:
    """Join a public base URL with an application path."""

    normalized_url = normalize_base_url(base_url)

    if not isinstance(path, str) or not path.strip():
        return normalized_url
    
    return urljoin(
        f"{normalized_url}/",
        path.strip().lstrip("/"),
    )

def resolve_url(page_url: str, reference: str) -> str:
    """Resolve a relative or root-relative reference"""
    
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("URL reference must not be empty.")
    
    return urljoin(page_url, reference.strip())

def _effective_port(parsed: ParseResult) -> int:
    """Return the explicit or default port of a parsed URL."""

    if parsed.port is not None:
        return parsed.port

    if parsed.scheme == "https":
        return 443

    return 80

def origin(url: str) -> tuple[str, str, int]:
    """Return scheme, hostname and effective port."""

    parsed = urlparse(url)

    if parsed.scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            f"Unsupported URL scheme: {parsed.scheme}"
        )

    if not parsed.hostname:
        raise ValueError(
            f"URL has no hostname: {url}"
        )

    return (
        parsed.scheme.lower(),
        parsed.hostname.lower(),
        _effective_port(parsed),
    )


def same_origin(first_url: str, second_url: str) -> bool:
    """Return True when both URLs use the same origin."""

    return origin(first_url) == origin(second_url)