"""Docker runtime integration tests for application-to-database connectivity."""

import os
import subprocess
import time
import pytest

from pathlib import Path

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

PERSISTENCE_TARGETS = [
    (
        "wordpress",
        "wordpress-db",
        "WORDPRESS_DB_HOST",
        "WORDPRESS_DB_USER",
        "WORDPRESS_DB_PASSWORD",
        "WORDPRESS_DB_NAME",
        "mysqli",
    ),
    (
        "prestashop",
        "prestashop-db",
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

DATABASE_ISOLATION_TARGETS = [
    (
        "wordpress",
        "prestashop-db",
    ),
    (
        "prestashop",
        "wordpress-db",
    ),
]

@pytest.mark.network
@pytest.mark.parametrize(
    (
        "service",
        "forbidden_database",
    ),
    DATABASE_ISOLATION_TARGETS,
)
def test_application_cannot_reach_other_database(
    project_root: Path,
    service: str,
    forbidden_database: str,
) -> None:
    """Applications must not reach another application's database."""

    php_code = f'''
$host = "{forbidden_database}";
$port = 3306;

$socket = @fsockopen(
    $host,
    $port,
    $errorNumber,
    $errorMessage,
    3
);

if ($socket !== false) {{
    fclose($socket);

    fwrite(
        STDERR,
        "Unexpected database connection succeeded."
    );

    exit(1);
}}

echo "db-isolated";
'''

    result = compose_exec(
        project_root,
        service,
        php_code,
    )

    assert result.returncode == 0, (
        f"{service} unexpectedly reached "
        f"{forbidden_database}:3306\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert result.stdout.strip() == "db-isolated"


NGINX_DATABASE_ISOLATION_TARGETS = [
    "wordpress-db",
    "prestashop-db",
]

def compose_exec_command(
    project_root: Path,
    service: str,
    command_to_run: list[str],
) -> subprocess.CompletedProcess[str]:
    """Execute an arbitrary command inside a running Compose service."""

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
        *command_to_run,
    ]

    return subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

@pytest.mark.network
@pytest.mark.parametrize(
    "forbidden_database",
    NGINX_DATABASE_ISOLATION_TARGETS,
)
def test_nginx_cannot_reach_databases(
    project_root: Path,
    forbidden_database: str,
) -> None:
    """Nginx must not have network access to application databases."""

    result = compose_exec_command(
        project_root,
        "nginx",
        [
            "sh",
            "-c",
            (
                f"nc -z -w 3 {forbidden_database} 3306 "
                "&& exit 1 || exit 0"
            ),
        ],
    )

    assert result.returncode == 0, (
        f"nginx unexpectedly reached "
        f"{forbidden_database}:3306"
    )

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
def test_application_database_is_writable(
    project_root: Path,
    service: str,
    host_variable: str,
    user_variable: str,
    password_variable: str,
    database_variable: str,
    database_driver: str,
) -> None:
    """Application DB user must be able to write and read temporary data."""

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
        "Database connection failed: "
        . $connection->connect_error
    );
    exit(1);
}

if (!$connection->query(
    "CREATE TEMPORARY TABLE liora_test_tmp (
        test_value INT NOT NULL
    )"
)) {
    fwrite(
        STDERR,
        "Could not create temporary table: "
        . $connection->error
    );
    exit(1);
}

if (!$connection->query(
    "INSERT INTO liora_test_tmp (test_value)
     VALUES (42)"
)) {
    fwrite(
        STDERR,
        "Could not insert test data: "
        . $connection->error
    );
    exit(1);
}

$result = $connection->query(
    "SELECT test_value
     FROM liora_test_tmp"
);

if ($result === false) {
    fwrite(
        STDERR,
        "Could not read test data: "
        . $connection->error
    );
    exit(1);
}

$row = $result->fetch_assoc();

if ((int) $row["test_value"] !== 42) {
    fwrite(
        STDERR,
        "Unexpected database value."
    );
    exit(1);
}

$connection->close();

echo "db-write-ok";
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

    $connection->exec(
        "CREATE TEMPORARY TABLE liora_test_tmp (
            test_value INT NOT NULL
        )"
    );

    $connection->exec(
        "INSERT INTO liora_test_tmp (test_value)
         VALUES (42)"
    );

    $statement = $connection->query(
        "SELECT test_value
         FROM liora_test_tmp"
    );

    $row = $statement->fetch(
        PDO::FETCH_ASSOC
    );

    if ((int) $row["test_value"] !== 42) {
        fwrite(
            STDERR,
            "Unexpected database value."
        );
        exit(1);
    }

    echo "db-write-ok";

} catch (PDOException $error) {
    fwrite(
        STDERR,
        "Database write/read test failed: "
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
        f"{service} database is not writable:\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert result.stdout.strip() == "db-write-ok"

def wait_for_database(
    project_root: Path,
    service: str,
    host_variable: str,
    timeout: int = 60,
) -> None:
    """Wait until an application's configured DB port is reachable again."""

    deadline = time.time() + timeout

    while time.time() < deadline:
        php_code = f'''
$hostValue = getenv("{host_variable}");
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
    2
);

if ($socket === false) {{
    exit(1);
}}

fclose($socket);
echo "ready";
'''

        result = compose_exec(
            project_root,
            service,
            php_code,
        )

        if (
            result.returncode == 0
            and result.stdout.strip() == "ready"
        ):
            return

        time.sleep(2)

    pytest.fail(
        f"Database for {service} did not become ready "
        f"within {timeout} seconds."
    )

def compose_restart_service(
    project_root: Path,
    service: str,
) -> subprocess.CompletedProcess[str]:
    """Restart a service in the runtime Docker Compose project."""

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
        "restart",
        service,
    ]

    return subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

@pytest.mark.persistence
@pytest.mark.parametrize(
    (
        "application_service",
        "database_service",
        "host_variable",
        "user_variable",
        "password_variable",
        "database_variable",
        "database_driver",
    ),
    PERSISTENCE_TARGETS,
)
def test_database_data_survives_restart(
    project_root: Path,
    application_service: str,
    database_service: str,
    host_variable: str,
    user_variable: str,
    password_variable: str,
    database_variable: str,
    database_driver: str,
) -> None:
    """Database data must survive a database container restart."""

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
        create_driver_php = '''
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
        "Database connection failed."
    );
    exit(1);
}

$connection->query(
    "DROP TABLE IF EXISTS liora_persistence_test"
);

if (!$connection->query(
    "CREATE TABLE liora_persistence_test (
        test_value INT NOT NULL
    )"
)) {
    fwrite(
        STDERR,
        "Could not create persistence table."
    );
    exit(1);
}

if (!$connection->query(
    "INSERT INTO liora_persistence_test (test_value)
     VALUES (42)"
)) {
    fwrite(
        STDERR,
        "Could not insert persistence value."
    );
    exit(1);
}

$connection->close();

echo "persistence-data-created";
'''

        read_driver_php = '''
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
        "Database connection failed after restart."
    );
    exit(1);
}

$result = $connection->query(
    "SELECT test_value
     FROM liora_persistence_test"
);

if ($result === false) {
    fwrite(
        STDERR,
        "Persistence table disappeared."
    );
    exit(1);
}

$row = $result->fetch_assoc();

if ((int) $row["test_value"] !== 42) {
    fwrite(
        STDERR,
        "Persisted value is incorrect."
    );
    exit(1);
}

$connection->query(
    "DROP TABLE liora_persistence_test"
);

$connection->close();

echo "persistence-ok";
'''

    elif database_driver == "pdo":
        create_driver_php = '''
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

    $connection->exec(
        "DROP TABLE IF EXISTS liora_persistence_test"
    );

    $connection->exec(
        "CREATE TABLE liora_persistence_test (
            test_value INT NOT NULL
        )"
    );

    $connection->exec(
        "INSERT INTO liora_persistence_test (test_value)
         VALUES (42)"
    );

    echo "persistence-data-created";

} catch (PDOException $error) {
    fwrite(
        STDERR,
        "Could not prepare persistence data: "
        . $error->getMessage()
    );
    exit(1);
}
'''

        read_driver_php = '''
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
        "SELECT test_value
         FROM liora_persistence_test"
    );

    $row = $statement->fetch(
        PDO::FETCH_ASSOC
    );

    if ((int) $row["test_value"] !== 42) {
        fwrite(
            STDERR,
            "Persisted value is incorrect."
        );
        exit(1);
    }

    $connection->exec(
        "DROP TABLE liora_persistence_test"
    );

    echo "persistence-ok";

} catch (PDOException $error) {
    fwrite(
        STDERR,
        "Persistence check failed: "
        . $error->getMessage()
    );
    exit(1);
}
'''

    else:
        pytest.fail(
            f"Unsupported database driver: {database_driver}"
        )

    # 1. Create permanent test data.
    create_result = compose_exec(
        project_root,
        application_service,
        common_php + create_driver_php,
    )

    assert create_result.returncode == 0, (
        f"{application_service} could not prepare persistence data:\n"
        f"STDOUT:\n{create_result.stdout}\n"
        f"STDERR:\n{create_result.stderr}"
    )

    assert (
        create_result.stdout.strip()
        == "persistence-data-created"
    )

    # 2. Restart the database container.
    restart_result = compose_restart_service(
        project_root,
        database_service,
    )

    assert restart_result.returncode == 0, (
        f"Could not restart {database_service}:\n"
        f"{restart_result.stderr}"
    )

    # 3. Wait until MySQL is reachable again.
    wait_for_database(
        project_root,
        application_service,
        host_variable,
    )

    # 4. Verify that the data survived.
    read_result = compose_exec(
        project_root,
        application_service,
        common_php + read_driver_php,
    )

    assert read_result.returncode == 0, (
        f"{application_service} persistence check failed:\n"
        f"STDOUT:\n{read_result.stdout}\n"
        f"STDERR:\n{read_result.stderr}"
    )

    assert read_result.stdout.strip() == "persistence-ok"