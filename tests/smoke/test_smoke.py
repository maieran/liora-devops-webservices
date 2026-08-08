"""Basic runtime smoke tests for public application endpoints."""

import pytest
import requests

from tests.support.urls import (
    join_url,
    same_origin,
)


pytestmark = pytest.mark.smoke


APPLICATION_PATHS = [
    ("wordpress", "/wordpress/"),
    ("prestashop", "/prestashop/"),
]


@pytest.mark.parametrize(
    ("application", "path"),
    APPLICATION_PATHS,
)
def test_application_is_reachable(
    base_url: str,
    application: str,
    path: str,
) -> None:
    """Critical applications must return a successful HTTP response."""

    application_url = join_url(
        base_url,
        path,
    )

    response = requests.get(
        application_url,
        timeout=10,
        allow_redirects=True,
    )

    assert response.status_code == 200, (
        f"{application} returned HTTP "
        f"{response.status_code}: {response.url}"
    )


@pytest.mark.parametrize(
    ("application", "path"),
    APPLICATION_PATHS,
)
def test_application_redirects_stay_on_same_origin(
    base_url: str,
    application: str,
    path: str,
) -> None:
    """Application redirects must not unexpectedly leave our public origin."""

    application_url = join_url(
        base_url,
        path,
    )

    response = requests.get(
        application_url,
        timeout=10,
        allow_redirects=True,
    )

    assert same_origin(
        base_url,
        response.url,
    ), (
        f"{application} redirected outside the expected origin: "
        f"{response.url}"
    )