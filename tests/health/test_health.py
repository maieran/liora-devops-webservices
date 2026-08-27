import requests
import pytest

from tests.support.urls import join_url


pytestmark = pytest.mark.health


def test_nginx_health_endpoint(base_url: str) -> None:
    """The public Nginx health endpoint must report healthy."""

    health_url = join_url(
        base_url,
        "/health",
    )

    response = requests.get(
        health_url,
        timeout=5,
        allow_redirects=False,
    )

    assert response.status_code == 200
    assert response.text.strip().lower() == "ok"