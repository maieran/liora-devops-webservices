"""Shared pytest fixtures."""


import pytest
import os

from pathlib import Path

from tests.support.compose import (
    ComposeModel,
    render_compose_config,
)

from tests.support.urls import normalize_base_url

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the repository root independently of the current directory."""

    return Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session")
def compose_models(
    project_root: Path,
) -> dict[str, ComposeModel]:
    """Render Development, Staging and Production Compose models."""

    fixtures = project_root / "tests" / "fixtures" / "env"

    return {
        "dev": render_compose_config(
            project_root=project_root,
            env_file=fixtures / "dev.env",
            override_file=project_root / "docker-compose.dev.yml",
            project_name="liora-config-dev",
        ),
        "staging": render_compose_config(
            project_root=project_root,
            env_file=fixtures / "staging.env",
            override_file=project_root / "docker-compose.staging.yml",
            project_name="liora-config-staging",
        ),
        "prod": render_compose_config(
            project_root=project_root,
            env_file=fixtures / "prod.env",
            override_file=project_root / "docker-compose.prod.yml",
            project_name="liora-config-prod",
        ),
    }

@pytest.fixture(scope="session")
def base_url() -> str:
    """Return the externally reachable application base URL."""

    value = os.environ.get("BASE_URL")

    if not value:
        pytest.fail(
            "BASE_URL is required for runtime tests. "
            "Example: BASE_URL=http://localhost:8080"
        )

    return normalize_base_url(value)