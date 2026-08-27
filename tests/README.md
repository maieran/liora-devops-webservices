# Tests

This directory contains the automated validation suite for the Docker Compose deployment of WordPress, PrestaShop, Nginx, and their databases.

The tests validate our own infrastructure, configuration, routing, integration, persistence, and recovery behavior rather than the internal implementation of WordPress or PrestaShop.

The public-facing tests are intentionally designed so that they can later be reused against another deployment platform by changing the externally reachable `BASE_URL`.

---

## Current Public Routing

The current Nginx routing is:

```text
/              -> PrestaShop (canonical route)
/wordpress/    -> WordPress
/health        -> Nginx health endpoint
/prestashop    -> 301 redirect to /prestashop/
/prestashop/   -> optional PrestaShop convenience alias
```

### PrestaShop at the root path

An earlier PrestaShop asset problem occurred when PrestaShop was treated only as an application below:

```text
/prestashop/
```

PrestaShop generates root-relative paths such as:

```text
/themes/...
/modules/...
/img/...
```

To avoid broken CSS, JavaScript, and image resources, the current Compose implementation serves PrestaShop canonically at `/`:

```nginx
location / {
    proxy_pass http://prestashop;
}
```

As a consequence, PrestaShop owns the remaining root namespace. Paths not intercepted by another Nginx location are forwarded to PrestaShop.

The `/prestashop/` route is kept only as a convenience alias. The automated tests use `/` as the canonical PrestaShop page location and validate the alias separately.

---

## Proxy Details for Future Deployment Platforms

The Nginx configuration currently contains:

```nginx
proxy_set_header X-Forwarded-Port $server_port;
```

Inside the Nginx container, `$server_port` normally represents port `80`, although the Docker host currently exposes Nginx through port `8080`.

The tests therefore validate that public URLs remain consistent with the configured external host and port.

The configuration also contains:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

This may require reconsideration later if another proxy or Ingress terminates HTTPS before traffic reaches Nginx.

This is not a blocker for the current Docker Compose implementation.

---

# Test Architecture

Current structure:

```text
tests/
├── conftest.py
├── requirements-test.txt
├── run-python-tests.sh
│
├── fixtures/
│   └── env/
│       ├── dev.env
│       ├── staging.env
│       └── prod.env
│
├── support/
│   ├── __init__.py
│   ├── assets.py
│   ├── compose.py
│   └── urls.py
│
├── unit/
│   ├── test_assets.py
│   ├── test_compose_helpers.py
│   └── test_urls.py
│
├── config/
│   └── test_compose_config.py
│
├── health/
│   └── test_health.py
│
├── smoke/
│   └── test_smoke.py
│
├── assets/
│   └── test_assets_runtime.py
│
├── routing/
│   └── test_routing.py
│
└── integration/
    ├── test_application_readiness.py
    └── test_database_connectivity.py
```

Pytest configuration is stored at the project root:

```text
pyproject.toml
```

---

# Test Dependencies

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the test dependencies:

```bash
python -m pip install -r tests/requirements-test.txt
```

On later sessions, only activate the existing environment again:

```bash
source .venv/bin/activate
```

---

# Pytest Markers

The suite uses markers to separate different test layers:

```text
unit
config
health
smoke
assets
routing
integration
network
docker
kubernetes
persistence
resilience
```

---

# Unit Tests

Unit tests validate the Python support code without requiring Docker or network access.

They cover:

- URL normalization and construction
- Same-origin detection
- Internal and external URL handling
- Asset extraction
- Compose helper functionality

Because WordPress and PrestaShop are third-party applications, their internal PHP implementation is not unit tested here.

Instead, this project validates how they are configured, deployed, connected, exposed, and recovered.

---

# Docker Compose Configuration Tests

Configuration tests render the Dev, Staging, and Prod Compose configurations without starting containers.

They verify, among other things:

- Dev, Staging, and Prod Compose configurations render successfully
- Required environment variables are not empty
- WordPress debug mode is enabled in Dev
- PrestaShop development mode is enabled in Dev
- Debug/development modes are disabled in Staging and Prod
- Prod services use the expected restart policy
- Only Nginx publishes a host port
- Databases do not publish host ports
- Nginx healthcheck targets `/health`
- Nginx waits for healthy application containers
- Applications wait for healthy database containers
- Database services use persistent volumes
- WordPress and PrestaShop use separate private database networks
- Each database is connected only to its own private application network
- Public host and port configuration is consistent
- PrestaShop `PS_DOMAIN` is derived from the selected environment file

The expected database topology is:

```text
frontend-network
├── nginx
├── wordpress
└── prestashop

wordpress-network
├── wordpress
└── wordpress-db

prestashop-network
├── prestashop
└── prestashop-db
```

The database network tests assert the exact expected network sets, so accidental cross-network connections are detected.

---

# Public Runtime Tests

Runtime tests communicate with the deployment through its externally reachable Nginx URL.

For a local Docker Compose test run:

```bash
export BASE_URL=http://127.0.0.1:8080
```

They cover:

- Nginx health
- WordPress availability
- PrestaShop availability
- Redirect behavior
- Same-origin redirects
- CSS, JavaScript, and image availability
- Asset content types
- WordPress routing below `/wordpress/`
- PrestaShop routing at `/`
- PrestaShop convenience routing through `/prestashop/`

Asset responses are loaded once per application and reused by the reachability and Content-Type tests to avoid duplicate HTTP requests.

Failed asset requests are checked before their Content-Type is evaluated, so HTTP failures are reported clearly.

Because these tests use `BASE_URL`, the same public-facing test layers can later be reused against another deployment platform.

---

# Docker Integration Tests

Docker-specific integration tests validate communication and recovery behavior between running containers.

They cover:

- Application-to-database TCP connectivity
- Database authentication
- Real SQL queries
- Database read/write permissions
- Persistence after database container restart
- Application recovery after restart
- Nginx recovery after restart
- PrestaShop schema readiness
- WordPress database/application-state consistency
- Runtime network isolation

The Docker-specific tests use the running Compose project and require:

```bash
export RUNTIME_PROJECT_NAME=liora-runtime-test
export RUNTIME_ENV_FILE=/tmp/liora-runtime.env
```

The test runner validates these variables before starting Docker integration or network tests. It also checks that `RUNTIME_ENV_FILE` exists, so configuration errors fail early with a clear message.

The Nginx database-isolation check verifies that `nc` is available before using it, so a missing command cannot be mistaken for successful network isolation.

---

# Persistence Tests

The persistence tests verify that database data survives a database-container restart.

The test flow is:

```text
Create persistent test table
        |
        v
Insert test value
        |
        v
Restart database container
        |
        v
Wait until database becomes reachable
        |
        v
Read the same value
        |
        v
Remove test table
```

This validates the Docker volume configuration at runtime.

---

# Resilience Tests

Resilience tests verify that services recover after container restarts.

They currently cover:

- WordPress restart and public recovery
- PrestaShop restart and public recovery
- Nginx restart and public recovery

---

# Application Readiness Tests

The readiness tests verify that the applications and their databases are in a consistent state.

## PrestaShop

PrestaShop is expected to have an initialized schema. Representative core tables are checked, including:

```text
ps_configuration
ps_shop
ps_product
ps_orders
```

## WordPress

WordPress is currently allowed to be in its installation state.

The test verifies that the database state agrees with the HTTP state:

```text
Empty WordPress database
        |
        v
WordPress installer is reachable
```

If WordPress later contains an initialized schema, the installer should no longer be the final application state.

---

# Manual Docker Compose Test Run

The following sequence starts a disposable Dev runtime and runs the tests manually.

## 1. Prepare the runtime environment

Copy the Dev test fixture:

```bash
cp tests/fixtures/env/dev.env /tmp/liora-runtime.env
```

For local testing on the same machine, make the public PrestaShop host match the test URL:

```bash
sed -i \
  's/^SERVER_HOST=.*/SERVER_HOST=127.0.0.1:8080/' \
  /tmp/liora-runtime.env
```

Export the runtime variables:

```bash
export BASE_URL=http://127.0.0.1:8080
export RUNTIME_PROJECT_NAME=liora-runtime-test
export RUNTIME_ENV_FILE=/tmp/liora-runtime.env
```

`BASE_URL` and `SERVER_HOST` should describe the same public origin. PrestaShop receives:

```text
PS_DOMAIN=${SERVER_HOST}
```

so using different hosts can cause PrestaShop to generate absolute URLs for another origin.

## 2. Start the Docker Compose runtime

Define the Compose command once:

```bash
DC_RUNTIME=(
  docker compose
  -p "$RUNTIME_PROJECT_NAME"
  --env-file "$RUNTIME_ENV_FILE"
  -f docker-compose.yml
  -f docker-compose.dev.yml
)
```

Build and start:

```bash
"${DC_RUNTIME[@]}" up -d --build
```

Check the containers:

```bash
"${DC_RUNTIME[@]}" ps
```

All five services should become healthy:

```text
nginx
wordpress
wordpress-db
prestashop
prestashop-db
```

Use `"${DC_RUNTIME[@]}" ps` rather than plain `docker compose ps`, because the test runtime uses a custom project name, env file, and Compose override.

## 3. Check the deployment manually

```bash
curl -I "$BASE_URL/health"
curl -I "$BASE_URL/"
curl -IL "$BASE_URL/wordpress/"
curl -I "$BASE_URL/prestashop"
```

Expected routing:

```text
/health       -> 200
/             -> PrestaShop
/wordpress/   -> WordPress
/prestashop   -> 301 /prestashop/
```

## 4. Run the test suites

```bash
./tests/run-python-tests.sh static
./tests/run-python-tests.sh runtime
./tests/run-python-tests.sh integration
./tests/run-python-tests.sh network
```

Or run the currently blocking green groups together:

```bash
./tests/run-python-tests.sh green
```

For direct debugging, individual files can also be executed:

```bash
pytest tests/assets/test_assets_runtime.py -v
pytest tests/config/test_compose_config.py -v
pytest tests/routing/test_routing.py -v
```

## 5. Stop the runtime

```bash
"${DC_RUNTIME[@]}" down
```

---

# Running the Test Suites

The preferred entry point is:

```bash
./tests/run-python-tests.sh <suite>
```

## Static Tests

No running Docker stack is required:

```bash
./tests/run-python-tests.sh static
```

The exact database-network configuration assertions can also be run directly:

```bash
pytest \
  tests/config/test_compose_config.py \
  -k "required_service_network_connections" \
  -v
```

## Public Runtime Tests

Requires the deployed application:

```bash
export BASE_URL=http://127.0.0.1:8080

./tests/run-python-tests.sh runtime
```

## Functional Docker Integration Tests

Requires the running Compose project:

```bash
export BASE_URL=http://127.0.0.1:8080
export RUNTIME_PROJECT_NAME=liora-runtime-test
export RUNTIME_ENV_FILE=/tmp/liora-runtime.env

./tests/run-python-tests.sh integration
```

## Network Isolation Tests

Requires the running Compose project:

```bash
export RUNTIME_PROJECT_NAME=liora-runtime-test
export RUNTIME_ENV_FILE=/tmp/liora-runtime.env

./tests/run-python-tests.sh network
```

The runtime network suite currently validates application/database isolation and Nginx/database isolation.

## All Currently Green Groups

```bash
./tests/run-python-tests.sh green
```

---

# Current Test Status

The suite has expanded during review, including Staging configuration coverage, stricter network-topology validation, improved routing coverage, and shared asset-response loading.

Recent verified results include:

```text
Static tests                 62 passed
Public runtime tests         15 passed
Functional integration      13 passed
Network isolation tests      4 passed
-------------------------------------
Total                        94 passed
```

All 94 currently collected tests are covered by the standard test runner
suites and pass successfully.

The test suites cover static configuration, public runtime behavior,
Docker integration, persistence, resilience, and network isolation.

The complete configuration suite passes across Dev, Staging, and Prod.

Exact total counts may change as additional tests are added, so the runner output and generated JUnit reports are the source of truth.

---

# JUnit Reports

The test runner generates machine-readable JUnit XML reports:

```text
reports/
├── static.xml
├── runtime.xml
├── integration.xml
└── network.xml
```

The `reports/` directory is ignored by Git.

These reports are intended for Jenkins.

---

# Jenkins Integration

The recommended CI order is:

```text
Checkout
   |
   v
Install Test Dependencies
   |
   v
Static Tests
   |
   v
Build / Deploy Environment
   |
   v
Runtime Tests
   |
   v
Functional Integration Tests
   |
   v
Network Isolation Tests
   |
   v
Publish JUnit Reports
```

Jenkins should call the test runner rather than duplicating the pytest expressions inside the Jenkinsfile:

```bash
./tests/run-python-tests.sh static
./tests/run-python-tests.sh runtime
./tests/run-python-tests.sh integration
./tests/run-python-tests.sh network
```

JUnit results should be published even if pytest fails.

Example:

```groovy
post {
    always {
        junit allowEmptyResults: true,
              testResults: 'reports/*.xml'
    }
}
```

---

# Kubernetes Reuse

The public-facing test layers are intentionally based on `BASE_URL`.

For Docker Compose:

```bash
export BASE_URL=http://127.0.0.1:8080
```

Later, another deployment platform can provide a different externally reachable URL:

```bash
export BASE_URL=https://example.test
```

The following test groups can therefore largely remain unchanged:

- health
- smoke
- assets
- routing

Docker-specific tests that use `docker compose exec` will require platform-native counterparts.

Environment-specific configuration should continue to remain separated for Dev, Staging, and Prod.
