"""Helpers for extracting and resolving application assets."""

from html.parser import HTMLParser
from typing import Iterable

from tests.support.urls import resolve_url, same_origin

ASSET_ATTRIBUTES = {
    "link": "href",
    "script":"src",
    "img":"src",
}

IGNORED_PREFIXES = {
    "#",
    "data:",
    "javascript:",
    "mailto:",
    "tel:",
}

class AssetReferenceParser(HTMLParser):
    """Collect asset references from selected HTML elements."""

    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
    ) -> None:
        attribute_name = ASSET_ATTRIBUTES.get(tag.lower())

        if attribute_name is None:
            return

        attribute_map = dict(attributes)
        value = attribute_map.get(attribute_name)

        if value and value.strip():
            self.references.append(value.strip())

    def handle_startendtag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attributes)

def _unique(values: Iterable[str]) -> list[str]:
    """Remove duplicates while preserving input order."""

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def extract_asset_references(html: str) -> list[str]:
    """Extract href/src references from relevant HTML tags."""

    parser = AssetReferenceParser()
    parser.feed(html)
    parser.close()

    return _unique(parser.references)


def internal_asset_urls(
    base_url: str,
    page_url: str,
    references: Iterable[str],
) -> list[str]:
    """Resolve and return only same-origin asset URLs."""

    internal_urls: list[str] = []

    for raw_reference in references:
        reference = raw_reference.strip()

        if not reference:
            continue

        if reference.lower().startswith(tuple(IGNORED_PREFIXES)):
            continue

        absolute_url = resolve_url(page_url, reference)

        if same_origin(base_url, absolute_url):
            internal_urls.append(absolute_url)

    return _unique(internal_urls)
