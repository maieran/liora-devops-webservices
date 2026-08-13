"""Runtime tests for reverse-proxy application paths."""

from urllib.parse import urlparse

import pytest
import requests

from tests.support.assets import (
    extract_asset_references,
    internal_asset_urls,
)

from tests.support.urls import (
    join_url,
    same_origin,
)


pytestmark = pytest.mark.routing


APPLICATION_PATHS = [
    ("wordpress", "/wordpress/"),
    ("prestashop", "/"),
]

SUBPATH_APPLICATIONS = [
    ("wordpress", "/wordpress/"),
]

@pytest.mark.parametrize(
    ("application", "public_path"),
    APPLICATION_PATHS,
)
def test_application_final_url_stays_under_public_path(
    base_url: str,
    application: str,
    public_path: str,
) -> None:
    """Redirects must remain underneath the application's public path."""

    application_url = join_url(
        base_url,
        public_path,
    )

    response = requests.get(
        application_url,
        timeout=10,
        allow_redirects=True,
    )

    assert response.status_code == 200

    final_path = urlparse(response.url).path

    assert final_path.startswith(public_path), (
        f"{application} escaped its public path "
        f"{public_path}: {response.url}"
    )


@pytest.mark.parametrize(
    ("application", "public_path"),
    SUBPATH_APPLICATIONS,
)
def test_application_final_url_stays_under_public_path(
    base_url: str,
    application: str,
    public_path: str,
) -> None:
    application_url = join_url(
        base_url,
        public_path,
    )

    response = requests.get(
        application_url,
        timeout=10,
        allow_redirects=True,
    )

    assert response.status_code == 200

    final_path = urlparse(response.url).path

    assert final_path.startswith(public_path), (
        f"{application} escaped its public path "
        f"{public_path}: {response.url}"
    )

def test_prestashop_is_reachable_at_root(
    base_url: str,
) -> None:
    """PrestaShop is intentionally exposed at the public root path."""

    response = requests.get(
        join_url(base_url, "/"),
        timeout=10,
        allow_redirects=True,
    )

    assert response.status_code == 200

    assert same_origin(
        base_url,
        response.url,
    ), (
        "PrestaShop root redirected outside "
        f"the expected origin: {response.url}"
    )