# Tests

This directory contains the automated validation suite for the Docker Compose deployment of WordPress, PrestaShop, Nginx, and their databases.

The tests validate our own infrastructure, configuration, routing, integration, persistence, and recovery behavior rather than the internal implementation of WordPress or PrestaShop.

The public-facing tests are intentionally designed so that they can later be reused against Kubernetes by changing the externally reachable `BASE_URL`.

---

## Current Public Routing

The current Nginx routing is:

```text
/             -> PrestaShop
/wordpress/   -> WordPress
/health       -> Nginx health endpoint
```

### PrestaShop at the root path

An earlier PrestaShop asset problem occurred when PrestaShop was served below:

```text
/prestashop/
```

PrestaShop generated root-relative paths such as:

```text
/themes/...
/modules/...
/img/...
```

To avoid broken CSS, JavaScript, and image resources, the current Compose prototype serves PrestaShop at `/`:

```nginx
location / {
    proxy_pass http://prestashop;
}
```

As a consequence, PrestaShop currently owns the remaining root namespace. Paths not intercepted by another Nginx location are forwarded to PrestaShop.

This is the intended behavior for the current Docker Compose implementation.

Before finalizing the Kubernetes architecture, the routing strategy can be reconsidered:

- **Option A — Current choice:** PrestaShop remains at `/`.
- **Option B:** PrestaShop is configured completely below `/prestashop/`.
- **Option C:** WordPress and PrestaShop receive separate hostnames.

The current automated tests validate **Option A**.

---

## Proxy Details for Future Kubernetes Deployment

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

This may require reconsideration once Kubernetes Ingress is placed in front of Nginx.

For example:

```text
Client
  |
 HTTPS
  |
Ingress
  |
 HTTP
  |
Nginx
```

In this case, `$scheme` inside Nginx may be `http` even though the original client request used HTTPS.

This is not a blocker for the current Compose implementation, but it should be reviewed during Kubernetes/Ingress implementation.

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

Install the test dependencies with:

```bash
python -m pip install -r tests/requirements-test.txt
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

Configuration tests render the Dev and Prod Compose configurations without starting containers.

They verify, among other things:

- Dev and Prod Compose configurations render successfully
- Required environment variables are not empty
- WordPress debug mode is enabled in Dev
- PrestaShop development mode is enabled in Dev
- Debug/development modes are disabled in Prod
- Prod services use the expected restart policy
- Only Nginx publishes a host port
- Databases do not publish host ports
- Nginx healthcheck targets `/health`
- Nginx waits for healthy application containers
- Applications wait for healthy database containers
- Database services use persistent volumes
- WordPress and its database share a private network
- PrestaShop and its database should share a private network
- Public host and port configuration is consistent

The PrestaShop private-network requirement currently exposes a known Docker Compose architecture issue. See **Known Network Isolation Issue** below.

---

# Public Runtime Tests

Runtime tests communicate with the deployment through its externally reachable Nginx URL.

Set:

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

Because these tests use `BASE_URL`, they can later be reused against another platform.

For example:

```bash
export BASE_URL=https://example.test
```

can later point the same public tests to a Kubernetes Ingress.

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

The Docker-specific tests use the running Compose project and therefore require:

```bash
export RUNTIME_PROJECT_NAME=liora-runtime-test
export RUNTIME_ENV_FILE=/tmp/liora-runtime.env
```

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

# Known Network Isolation Issue

The current Compose architecture does not provide PrestaShop with a dedicated private database network.

The desired topology is:

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

Currently, `prestashop-db` participates in the frontend network.

As a consequence, the test suite currently proves that:

```text
WordPress -> prestashop-db   reachable
Nginx     -> prestashop-db   reachable
```

This is intentionally reported as a test failure.

The failing tests should **not** be weakened or removed. After the Compose topology is corrected, the same tests should become green.

---

# Running the Test Suites

The preferred entry point is:

```bash
./tests/run-python-tests.sh <suite>
```

## Static Tests

No running Docker stack is required.

```bash
./tests/run-python-tests.sh static
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

## All Currently Green Groups

```bash
./tests/run-python-tests.sh green
```

## Network Isolation Tests

```bash
./tests/run-python-tests.sh network
```

This suite contains both static Compose topology tests and runtime isolation tests. It is currently expected to remain red until the documented PrestaShop database network issue is fixed.

---

# Current Test Status

At the current implementation stage:

```text
Static tests              46 passed
Public runtime tests      11 passed
Functional integration    13 passed
------------------------------------
Green test groups         70 passed
```

The network test group currently contains:

```text
6 network-related checks
2 passed
4 failed
```

The four failures represent the known PrestaShop database network-isolation issue rather than four unrelated defects.

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
Publish JUnit Reports
```

Jenkins should call the test runner rather than duplicating the pytest expressions inside the Jenkinsfile:

```bash
./tests/run-python-tests.sh static
./tests/run-python-tests.sh runtime
./tests/run-python-tests.sh integration
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

The network-isolation suite should initially remain separate from the blocking CI quality gate because it currently detects the known Compose architecture issue.

After the Compose network topology has been corrected and the tests are green, it can become a blocking CI stage.

---

# Kubernetes Reuse

The public-facing test layers are intentionally based on `BASE_URL`.

For Docker Compose:

```bash
export BASE_URL=http://127.0.0.1:8080
```

Later, for Kubernetes:

```bash
export BASE_URL=https://example.test
```

The following test groups can therefore largely remain unchanged:

- health
- smoke
- assets
- routing

Docker-specific tests that use `docker compose exec` will require Kubernetes-native counterparts.

The future Kubernetes implementation should also revisit:

- Host and path-based routing
- `X-Forwarded-Port`
- `X-Forwarded-Proto`
- HTTPS termination
- Ingress behavior
- Environment-specific configuration for Dev, Staging, and Prod
