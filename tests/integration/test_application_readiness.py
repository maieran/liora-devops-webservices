"""Runtime checks for application and database readiness."""

import os
import subprocess
from pathlib import Path

import pytest
import requests

from tests.support.urls import join_url


pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
]


def compose_exec_php(
    project_root: Path,
    service: str,
    php_code: str,
) -> subprocess.CompletedProcess[str]:
    """Execute PHP inside a running Compose application container."""

    runtime_env_file = os.environ.get(
        "RUNTIME_ENV_FILE",
        "/tmp/liora-runtime.env",
    )

    project_name = os.environ.get(
        "RUNTIME_PROJECT_NAME",
        "liora-runtime-test",
    )

    command = [
        "docker",
        "compose",
        "-p",
        project_name,
        "--env-file",
        runtime_env_file,
        "-f",
        str(project_root / "docker-compose.yml"),
        "-f",
        str(project_root / "docker-compose.dev.yml"),
        "exec",
        "-T",
        service,
        "php",
        "-r",
        php_code,
    ]

    return subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_prestashop_schema_is_initialized(
    project_root: Path,
) -> None:
    """PrestaShop must contain its essential database tables."""

    php_code = '''
$dsn =
    "mysql:host=" . getenv("DB_SERVER")
    . ";dbname=" . getenv("DB_NAME");

try {
    $db = new PDO(
        $dsn,
        getenv("DB_USER"),
        getenv("DB_PASSWD"),
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        ]
    );

    $requiredTables = [
        "ps_configuration",
        "ps_shop",
        "ps_product",
        "ps_orders",
    ];

    foreach ($requiredTables as $table) {
        $statement = $db->prepare(
            "SHOW TABLES LIKE ?"
        );

        $statement->execute([$table]);

        if ($statement->fetch() === false) {
            fwrite(
                STDERR,
                "Missing PrestaShop table: " . $table
            );
            exit(1);
        }
    }

    echo "prestashop-schema-ok";

} catch (PDOException $error) {
    fwrite(
        STDERR,
        "PrestaShop schema check failed: "
        . $error->getMessage()
    );
    exit(1);
}
'''

    result = compose_exec_php(
        project_root,
        "prestashop",
        php_code,
    )

    assert result.returncode == 0, (
        f"PrestaShop schema is not ready:\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert (
        result.stdout.strip()
        == "prestashop-schema-ok"
    )

def test_wordpress_database_state_matches_application_state(
    project_root: Path,
    base_url: str,
) -> None:
    """WordPress HTTP state must agree with its database initialization state."""

    php_code = '''
$hostValue = getenv("WORDPRESS_DB_HOST");
$host = explode(":", $hostValue)[0];

$db = new mysqli(
    $host,
    getenv("WORDPRESS_DB_USER"),
    getenv("WORDPRESS_DB_PASSWORD"),
    getenv("WORDPRESS_DB_NAME")
);

if ($db->connect_errno) {
    fwrite(
        STDERR,
        "WordPress database connection failed."
    );
    exit(1);
}

$result = $db->query(
    "SHOW TABLES"
);

if ($result === false) {
    fwrite(
        STDERR,
        "Could not inspect WordPress tables."
    );
    exit(1);
}

echo $result->num_rows;

$db->close();
'''

    db_result = compose_exec_php(
        project_root,
        "wordpress",
        php_code,
    )

    assert db_result.returncode == 0, (
        f"Could not inspect WordPress database:\n"
        f"{db_result.stderr}"
    )

    table_count = int(
        db_result.stdout.strip()
    )

    wordpress_url = join_url(
        base_url,
        "/wordpress/",
    )

    response = requests.get(
        wordpress_url,
        timeout=10,
        allow_redirects=True,
    )

    assert response.status_code == 200

    if table_count == 0:
        assert response.url.endswith(
            "/wp-admin/install.php"
        ), (
            "WordPress database is empty, but the "
            "application did not reach the installer. "
            f"Final URL: {response.url}"
        )

    else:
        assert not response.url.endswith(
            "/wp-admin/install.php"
        ), (
            "WordPress database contains tables, but "
            "the application still redirects to the installer."
        )