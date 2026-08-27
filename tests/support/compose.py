"""Helpers for rendering and inspecting Docker Compose models."""

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

ComposeModel = dict[str, Any]

def build_compose_config_command(
    project_root: Path,
    env_file: Path,
    override_file: Path,
    project_name: str,
) -> list[str]:
    """Build the docker compose config command."""

    root = project_root.resolve()
    base_file = root / "docker-compose.yml"

    return [
        "docker",
        "compose",
        "--project-directory",
        str(root),
        "-p",
        project_name,
        "--env-file",
        str(env_file.resolve()),
        "-f",
        str(base_file),
        "-f",
        str(override_file.resolve()),
        "config",
        "--format",
        "json",
    ]

def render_compose_config(
    project_root: Path,
    env_file: Path,
    override_file: Path,
    project_name: str,
) -> ComposeModel:
    """Render the final Docker Compose model as a dictionary."""

    required_files = (
        project_root / "docker-compose.yml",
        env_file,
        override_file,
    )

    missing_files = [
        str(path)
        for path in required_files
        if not path.is_file()
    ]

    if missing_files:
        raise RuntimeError(
            "Required Compose test files are missing: "
            + ", ".join(missing_files)
        )

    command = build_compose_config_command(
        project_root=project_root,
        env_file=env_file,
        override_file=override_file,
        project_name=project_name,
    )

    try:
        result = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Docker CLI was not found in PATH."
        ) from error

    if result.returncode != 0:
        raise RuntimeError(
            "Docker Compose configuration could not be rendered.\n"
            f"Command: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    try:
        model = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Docker Compose returned invalid JSON.\n"
            f"Output:\n{result.stdout}"
        ) from error

    if not isinstance(model, dict):
        raise RuntimeError(
            "Rendered Compose model is not a JSON object."
        )

    return model

def find_empty_environment_values(
    model: Mapping[str, Any],
    requirements: Mapping[str, Sequence[str]],
) -> list[str]:
    """Find required service environment variables that are empty."""

    services = model.get("services", {})
    empty_values: list[str] = []

    for service_name, variable_names in requirements.items():
        service = services.get(service_name, {})
        environment = service.get("environment", {}) or {}

        for variable_name in variable_names:
            value = environment.get(variable_name)

            if value is None or not str(value).strip():
                empty_values.append(
                    f"{service_name}.{variable_name}"
                )

    return empty_values

def published_services(
    model: Mapping[str, Any],
) -> set[str]:
    """Return services that publish at least one host port."""

    services = model.get("services", {})

    return {
        service_name
        for service_name, service in services.items()
        if service.get("ports")
    }