"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from tests.support.compose import (
    ComposeModel,
    render_compose_config,
)


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the repository root independently of the current directory."""

    return Path(__file__).resolve().parents[1]

# TODO: Add staging environment later if the project introduces one.
@pytest.fixture(scope="session")
def compose_models(
    project_root: Path,
) -> dict[str, ComposeModel]:
    """Render Development and Production Compose models."""

    fixtures = project_root / "tests" / "fixtures" / "env"

    return {
        "dev": render_compose_config(
            project_root=project_root,
            env_file=fixtures / "dev.env",
            override_file=project_root / "docker-compose.dev.yml",
            project_name="liora-config-dev",
        ),
        "prod": render_compose_config(
            project_root=project_root,
            env_file=fixtures / "prod.env",
            override_file=project_root / "docker-compose.prod.yml",
            project_name="liora-config-prod",
        ),
    }