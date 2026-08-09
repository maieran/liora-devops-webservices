"""Docker runtime integration tests for application-to-database connectivity."""

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
]


# Used for the basic TCP connectivity test.
DATABASE_TARGETS = [
    ("wordpress", "WORDPRESS_DB_HOST"),
    ("prestashop", "DB_SERVER"),
]


# Used for the real database authentication + query test.
DATABASE_AUTH_TARGETS = [
    (
        "wordpress",
        "WORDPRESS_DB_HOST",
        "WORDPRESS_DB_USER",
        "WORDPRESS_DB_PASSWORD",
        "WORDPRESS_DB_NAME",
        "mysqli",
    ),
    (
        "prestashop",
        "DB_SERVER",
        "DB_USER",
        "DB_PASSWD",
        "DB_NAME",
        "pdo",
    ),
]


def compose_exec(
    project_root: Path,
    service: str,
    php_code: str,
) -> subprocess.CompletedProcess[str]:
    """Execute PHP inside a running Docker Compose service."""

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


@pytest.mark.parametrize(
    ("service", "database_host_variable"),
    DATABASE_TARGETS,
)
def test_application_can_reach_its_database(
    project_root: Path,
    service: str,
    database_host_variable: str,
) -> None:
    """Application container must reach its configured database port."""

    php_code = f'''
$hostValue = getenv("{database_host_variable}");

if ($hostValue === false || $hostValue === "") {{
    fwrite(
        STDERR,
        "Database host environment variable is empty."
    );
    exit(2);
}}

$host = $hostValue;
$port = 3306;

if (str_contains($hostValue, ":")) {{
    [$host, $portValue] = explode(":", $hostValue, 2);
    $port = (int) $portValue;
}}

$socket = @fsockopen(
    $host,
    $port,
    $errorNumber,
    $errorMessage,
    5
);

if ($socket === false) {{
    fwrite(
        STDERR,
        "$errorNumber $errorMessage"
    );
    exit(1);
}}

fclose($socket);

echo "db-port-ok";
'''

    result = compose_exec(
        project_root,
        service,
        php_code,
    )

    assert result.returncode == 0, (
        f"{service} could not reach its database:\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert result.stdout.strip() == "db-port-ok"


@pytest.mark.parametrize(
    (
        "service",
        "host_variable",
        "user_variable",
        "password_variable",
        "database_variable",
        "database_driver",
    ),
    DATABASE_AUTH_TARGETS,
)
def test_application_can_authenticate_to_its_database(
    project_root: Path,
    service: str,
    host_variable: str,
    user_variable: str,
    password_variable: str,
    database_variable: str,
    database_driver: str,
) -> None:
    """Application credentials must allow a real query against its database."""

    common_php = f'''
$hostValue = getenv("{host_variable}");
$user = getenv("{user_variable}");
$password = getenv("{password_variable}");
$database = getenv("{database_variable}");

if (
    $hostValue === false ||
    $user === false ||
    $password === false ||
    $database === false
) {{
    fwrite(
        STDERR,
        "Required database environment variable is missing."
    );
    exit(2);
}}

$host = $hostValue;
$port = 3306;

if (str_contains($hostValue, ":")) {{
    [$host, $portValue] = explode(":", $hostValue, 2);
    $port = (int) $portValue;
}}
'''

    if database_driver == "mysqli":
        driver_php = '''
mysqli_report(MYSQLI_REPORT_OFF);

$connection = new mysqli(
    $host,
    $user,
    $password,
    $database,
    $port
);

if ($connection->connect_errno) {
    fwrite(
        STDERR,
        "Database authentication failed: "
        . $connection->connect_error
    );
    exit(1);
}

$result = $connection->query(
    "SELECT 1 AS test_value"
);

if ($result === false) {
    fwrite(
        STDERR,
        "Database query failed: "
        . $connection->error
    );
    $connection->close();
    exit(1);
}

$row = $result->fetch_assoc();

if ($row["test_value"] != 1) {
    fwrite(
        STDERR,
        "Unexpected SELECT 1 result."
    );
    $connection->close();
    exit(1);
}

$connection->close();

echo "db-auth-ok";
'''

    elif database_driver == "pdo":
        driver_php = '''
$dsn = "mysql:host=$host;port=$port;dbname=$database";

try {
    $connection = new PDO(
        $dsn,
        $user,
        $password,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        ]
    );

    $statement = $connection->query(
        "SELECT 1 AS test_value"
    );

    $row = $statement->fetch(
        PDO::FETCH_ASSOC
    );

    if ($row["test_value"] != 1) {
        fwrite(
            STDERR,
            "Unexpected SELECT 1 result."
        );
        exit(1);
    }

    echo "db-auth-ok";

} catch (PDOException $error) {
    fwrite(
        STDERR,
        "Database authentication/query failed: "
        . $error->getMessage()
    );
    exit(1);
}
'''

    else:
        pytest.fail(
            f"Unsupported database driver: {database_driver}"
        )

    php_code = common_php + driver_php

    result = compose_exec(
        project_root,
        service,
        php_code,
    )

    assert result.returncode == 0, (
        f"{service} could not authenticate/query its database:\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert result.stdout.strip() == "db-auth-ok"