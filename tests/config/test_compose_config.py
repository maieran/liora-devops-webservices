import pytest

from typing import Any

from tests.support.compose import (
    find_empty_environment_values,
    published_services,
)

REQUIRED_ENVIRONMENT = {
    "wordpress": [
        "WORDPRESS_DB_NAME",
        "WORDPRESS_DB_USER",
        "WORDPRESS_DB_PASSWORD",
    ],
    "wordpress-db": [
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_ROOT_PASSWORD",
    ],
    "prestashop": [
        "DB_NAME",
        "DB_USER",
        "DB_PASSWD",
        "PS_DOMAIN",
    ],
    "prestashop-db": [
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_ROOT_PASSWORD",
    ],
}


pytestmark = pytest.mark.config


ENVIRONMENTS = [
    "dev",
    "staging",
    "prod",
]


EXPECTED_SERVICES = {
    "nginx",
    "wordpress",
    "wordpress-db",
    "prestashop",
    "prestashop-db",
}

def service_networks(
    service: dict[str, Any],
) -> set[str]:
    """Return all networks assigned to a service."""

    return set((service.get("networks") or {}).keys())

@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_expected_services_exist(
    compose_models,
    environment: str,
) -> None:
    services = set(
        compose_models[environment]["services"].keys()
    )

    assert services == EXPECTED_SERVICES


def test_development_debug_modes_are_enabled(
    compose_models,
) -> None:
    services = compose_models["dev"]["services"]

    assert (
        services["wordpress"]["environment"]["WORDPRESS_DEBUG"]
        == "1"
    )

    assert (
        services["prestashop"]["environment"]["PS_DEV_MODE"]
        == "1"
    )


@pytest.mark.parametrize(
    "environment",
    [
        "staging",
        "prod",
    ],
)
def test_non_development_debug_modes_are_disabled(
    compose_models,
    environment: str,
) -> None:
    services = compose_models[environment]["services"]

    assert (
        services["wordpress"]["environment"]["WORDPRESS_DEBUG"]
        == "0"
    )

    assert (
        services["prestashop"]["environment"]["PS_DEV_MODE"]
        == "0"
    )

@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_required_environment_values_are_not_empty(
    compose_models,
    environment: str,
) -> None:
    missing = find_empty_environment_values(
        compose_models[environment],
        REQUIRED_ENVIRONMENT,
    )

    assert not missing, (
        f"{environment} contains empty required variables: "
        + ", ".join(missing)
    )

@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_only_nginx_publishes_a_host_port(
    compose_models,
    environment: str,
) -> None:
    services_with_ports = published_services(
        compose_models[environment]
    )

    assert services_with_ports == {"nginx"}

@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_nginx_healthcheck_targets_health_endpoint(
    compose_models,
    environment: str,
) -> None:
    healthcheck = (
        compose_models[environment]
        ["services"]
        ["nginx"]
        ["healthcheck"]
        ["test"]
    )

    assert "/health" in " ".join(healthcheck)

@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_nginx_waits_for_healthy_applications(
    compose_models,
    environment: str,
) -> None:
    dependencies = (
        compose_models[environment]
        ["services"]
        ["nginx"]
        ["depends_on"]
    )

    assert (
        dependencies["wordpress"]["condition"]
        == "service_healthy"
    )

    assert (
        dependencies["prestashop"]["condition"]
        == "service_healthy"
    )

@pytest.mark.parametrize(
    ("application", "database"),
    [
        ("wordpress", "wordpress-db"),
        ("prestashop", "prestashop-db"),
    ],
)
@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_applications_wait_for_healthy_databases(
    compose_models,
    environment: str,
    application: str,
    database: str,
) -> None:
    dependency = (
        compose_models[environment]
        ["services"]
        [application]
        ["depends_on"]
        [database]
    )

    assert dependency["condition"] == "service_healthy"

@pytest.mark.parametrize(
    "database_service",
    [
        "wordpress-db",
        "prestashop-db",
    ],
)
@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_databases_use_persistent_volumes(
    compose_models,
    environment: str,
    database_service: str,
) -> None:
    volumes = (
        compose_models[environment]
        ["services"]
        [database_service]
        ["volumes"]
    )

    volume_targets = {
        volume["target"]
        for volume in volumes
    }

    assert "/var/lib/mysql" in volume_targets

@pytest.mark.parametrize(
    "service_name",
    sorted(EXPECTED_SERVICES),
)
def test_production_services_restart_unless_stopped(
    compose_models,
    service_name: str,
) -> None:
    service = (
        compose_models["prod"]
        ["services"]
        [service_name]
    )

    assert service.get("restart") == "unless-stopped"
    
@pytest.mark.network
@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_required_service_network_connections(
    compose_models,
    environment: str,
) -> None:
    services = compose_models[environment]["services"]

    nginx_networks = service_networks(
        services["nginx"]
    )

    wordpress_networks = service_networks(
        services["wordpress"]
    )

    wordpress_db_networks = service_networks(
        services["wordpress-db"]
    )

    prestashop_networks = service_networks(
        services["prestashop"]
    )

    prestashop_db_networks = service_networks(
        services["prestashop-db"]
    )

    print("wordpress-db:", wordpress_db_networks)
    print("prestashop-db:", prestashop_db_networks)

    # Reverse proxy can reach both applications.
    assert "frontend-network" in nginx_networks
    assert "frontend-network" in wordpress_networks
    assert "frontend-network" in prestashop_networks

    # WordPress communicates with its DB through a private network.
    assert "wordpress-network" in wordpress_networks

    # PrestaShop communicates with its DB through a private network.
    assert "prestashop-network" in prestashop_networks

    # Databases must only be connected to their own private networks.
    assert wordpress_db_networks == {
        "wordpress-network",
    }

    assert prestashop_db_networks == {
        "prestashop-network",
    }

@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_nginx_publishes_internal_port_80(
    compose_models,
    environment: str,
) -> None:
    ports = (
        compose_models[environment]
        ["services"]
        ["nginx"]
        ["ports"]
    )

    assert any(
        int(port["target"]) == 80
        for port in ports
    )

@pytest.mark.parametrize(
    ("environment", "expected_domain"),
    [
        ("dev", "dev.liora.test:8080"),
        ("staging", "staging.liora.test:8080"),
        ("prod", "prod.liora.test:8080"),
    ],
)
def test_prestashop_domain_comes_from_selected_env_file(
    compose_models,
    environment: str,
    expected_domain: str,
) -> None:
    actual_domain = (
        compose_models[environment]
        ["services"]
        ["prestashop"]
        ["environment"]
        ["PS_DOMAIN"]
    )

    assert actual_domain == expected_domain


# Check for published port consistency to detect drift.
@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_prestashop_domain_port_matches_nginx_published_port(
    compose_models,
    environment: str,
) -> None:
    prestashop_domain = (
        compose_models[environment]
        ["services"]
        ["prestashop"]
        ["environment"]
        ["PS_DOMAIN"]
    )

    published_port = (
        compose_models[environment]
        ["services"]
        ["nginx"]
        ["ports"]
        [0]
        ["published"]
    )

    domain_port = prestashop_domain.rsplit(":", 1)[1]

    assert domain_port == str(published_port)