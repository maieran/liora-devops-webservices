"""Runtime tests for public application assets."""

import pytest
import requests

from tests.support.assets import (
    extract_asset_references,
    internal_asset_urls,
)

from tests.support.urls import join_url


pytestmark = pytest.mark.assets


APPLICATION_PATHS = [
    ("wordpress", "/wordpress/"),
    ("prestashop", "/prestashop/"),
]


@pytest.mark.parametrize(
    ("application", "path"),
    APPLICATION_PATHS,
)
def test_internal_application_assets_are_reachable(
    base_url: str,
    application: str,
    path: str,
) -> None:
    """CSS, JavaScript and image assets must be reachable."""

    application_url = join_url(
        base_url,
        path,
    )

    page_response = requests.get(
        application_url,
        timeout=10,
        allow_redirects=True,
    )

    assert page_response.status_code == 200

    references = extract_asset_references(
        page_response.text
    )

    asset_urls = internal_asset_urls(
        base_url=base_url,
        page_url=page_response.url,
        references=references,
    )

    assert asset_urls, (
        f"No internal assets were found for {application}"
    )

    failed_assets: list[str] = []

    for asset_url in asset_urls:
        response = requests.get(
            asset_url,
            timeout=10,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            failed_assets.append(
                f"{response.status_code} {asset_url}"
            )

    assert not failed_assets, (
        f"{application} contains unreachable assets:\n"
        + "\n".join(failed_assets)
    )

from urllib.parse import urlparse


EXPECTED_CONTENT_TYPES = {
    ".css": ("text/css",),
    ".js": (
        "application/javascript",
        "text/javascript",
        "application/x-javascript",
    ),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
    ".gif": ("image/gif",),
    ".svg": ("image/svg+xml",),
    ".webp": ("image/webp",),
}


@pytest.mark.parametrize(
    ("application", "path"),
    APPLICATION_PATHS,
)
def test_internal_application_assets_have_expected_content_type(
    base_url: str,
    application: str,
    path: str,
) -> None:
    """Known asset types must return suitable HTTP Content-Types."""

    application_url = join_url(
        base_url,
        path,
    )

    page_response = requests.get(
        application_url,
        timeout=10,
        allow_redirects=True,
    )

    assert page_response.status_code == 200

    references = extract_asset_references(
        page_response.text
    )

    asset_urls = internal_asset_urls(
        base_url=base_url,
        page_url=page_response.url,
        references=references,
    )

    checked_assets = 0
    invalid_assets: list[str] = []

    for asset_url in asset_urls:
        path_lower = urlparse(asset_url).path.lower()

        extension = next(
            (
                suffix
                for suffix in EXPECTED_CONTENT_TYPES
                if path_lower.endswith(suffix)
            ),
            None,
        )

        if extension is None:
            continue

        checked_assets += 1

        response = requests.get(
            asset_url,
            timeout=10,
            allow_redirects=True,
        )

        content_type = (
            response.headers
            .get("Content-Type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )

        expected_types = EXPECTED_CONTENT_TYPES[extension]

        if content_type not in expected_types:
            invalid_assets.append(
                f"{asset_url} -> "
                f"{content_type or 'missing Content-Type'} "
                f"(expected one of {expected_types})"
            )

    assert checked_assets > 0, (
        f"No known CSS, JavaScript or image assets "
        f"were found for {application}"
    )

    assert not invalid_assets, (
        f"{application} returned unexpected asset Content-Types:\n"
        + "\n".join(invalid_assets)
    )