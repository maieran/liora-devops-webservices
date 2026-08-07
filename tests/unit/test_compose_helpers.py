
from pathlib import Path

import pytest

from tests.support.compose import (
    build_compose_config_command,
    find_empty_environment_values,
    published_services,
)

pytestmark = pytest.mark.unit


def test_build_compose_config_command_contains_all_files() -> None:
    project_root = Path("/tmp/liora-project")
    env_file = project_root / "tests/fixtures/env/dev.env"
    override_file = project_root / "docker-compose.dev.yml"

    command = build_compose_config_command(
        project_root=project_root,
        env_file=env_file,
        override_file=override_file,
        project_name="liora-test",
    )

    assert "--env-file" in command
    assert str(env_file) in command
    assert str(project_root / "docker-compose.yml") in command
    assert str(override_file) in command

    assert command[-3:] == [
        "config",
        "--format",
        "json",
    ]

def test_find_empty_environment_values() -> None:
    model = {
        "services": {
            "wordpress": {
                "environment": {
                    "WORDPRESS_DB_NAME": "wordpress",
                    "WORDPRESS_DB_USER": "",
                }
            }
        }
    }

    result = find_empty_environment_values(
        model,
        {
            "wordpress": [
                "WORDPRESS_DB_NAME",
                "WORDPRESS_DB_USER",
            ]
        },
    )

    assert result == [
        "wordpress.WORDPRESS_DB_USER",
    ]

def test_published_services_returns_only_services_with_ports() -> None:
    model = {
        "services": {
            "nginx": {
                "ports": [
                    {
                        "target": 80,
                        "published": "8080",
                    }
                ]
            },
            "wordpress": {},
            "wordpress-db": {},
        }
    }

    assert published_services(model) == {"nginx"}    