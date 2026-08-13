""" Unit Tests for Asset simulates when the PrestaShop redirect requests to subpages with assets"""

import pytest

from tests.support.assets import (
    extract_asset_references,
    internal_asset_urls,
)

pytestmark = pytest.mark.unit

def test_extract_asset_references_from_html() -> None:
    html = """
    <html>
      <head>
        <link rel="stylesheet" href="/themes/app.css">
        <script src="/modules/app.js"></script>
      </head>
      <body>
        <img src="/img/logo.png" alt="Logo">
      </body>
    </html>
    """

    assert extract_asset_references(html) == [
        "/themes/app.css",
        "/modules/app.js",
        "/img/logo.png",
    ]

def test_extract_asset_references_removes_duplicates() -> None:
    html = """
    <link href="/themes/app.css">
    <link href="/themes/app.css">
    """

    assert extract_asset_references(html) == [
        "/themes/app.css",
    ]

def test_internal_asset_urls_excludes_external_and_data_urls() -> None:
    references = [
        "/themes/app.css",
        "modules/app.js",
        "https://cdn.example.org/library.js",
        "data:image/png;base64,AAAA",
        "#content",
    ]

    result = internal_asset_urls(
        base_url="http://localhost:8080",
        page_url="http://localhost:8080/prestashop/",
        references=references,
    )

    assert result == [
        "http://localhost:8080/themes/app.css",
        "http://localhost:8080/prestashop/modules/app.js",
    ]

def test_internal_asset_urls_removes_duplicate_results() -> None:
    result = internal_asset_urls(
        base_url="http://localhost:8080",
        page_url="http://localhost:8080/prestashop/",
        references=[
            "/img/logo.png",
            "/img/logo.png",
        ],
    )

    assert result == [
        "http://localhost:8080/img/logo.png",
    ]    