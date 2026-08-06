import pytest

from tests.support.urls import (
    join_url,
    normalize_base_url,
    resolve_url,
    same_origin,
)

pytestmark = pytest.mark.unit

def test_normalize_base_url_removes_trailing_slash() -> None:
    assert (
        normalize_base_url("http://localhost:8080/")
        == "http://localhost:8080"
    )

def test_normalize_base_url_rejects_empty_value() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        normalize_base_url("")

def test_normalize_base_url_rejects_unsupported_scheme() -> None:
    with pytest.raises(
        ValueError,
        match="must use http or https",
    ):
        normalize_base_url("ftp://localhost/files")

def test_join_url_avoids_duplicate_slashes() -> None:
    result = join_url(
        "http://localhost:8080/",
        "/wordpress/",
    )

    assert result == "http://localhost:8080/wordpress/"

def test_resolve_url_handles_root_relative_reference() -> None:
    result = resolve_url(
        "http://localhost:8080/prestashop/",
        "/themes/classic/theme.css",
    )

    assert (
        result
        == "http://localhost:8080/themes/classic/theme.css"
    )

def test_resolve_url_handles_page_relative_reference() -> None:
    result = resolve_url(
        "http://localhost:8080/prestashop/",
        "themes/classic/theme.css",
    )

    assert (
        result
        == "http://localhost:8080/prestashop/"
        "themes/classic/theme.css"
    )

def test_same_origin_understands_default_http_port() -> None:
    assert same_origin(
        "http://example.test",
        "http://example.test:80/assets/app.css",
    )

def test_same_origin_rejects_different_port() -> None:
    assert not same_origin(
        "http://example.test:8080",
        "http://example.test:8081/assets/app.css",
    )