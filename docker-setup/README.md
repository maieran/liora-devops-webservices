# Docker Setup

Production-like Docker infrastructure for the Liora web-services project.

This directory contains the Dockerfiles, Docker Compose environments, NGINX reverse-proxy configuration, persistent storage definitions, and network design for a containerized PrestaShop and WordPress platform.

The scope of this README is intentionally limited to the **Docker setup milestone**. Testing, CI/CD, Kubernetes, monitoring, security scanning, infrastructure as code, and disaster recovery will be developed as separate project phases and documented in their corresponding directories and branches.

---

## 1. Milestone Scope

This Docker milestone primarily addresses the following project requirements:

| Requirement | Docker milestone status |
|---|---|
| 1. Dockerize the application | Implemented locally; registry publishing still needs multi-architecture images |
| 2. Development and production environments | Implemented with separate Compose files, values, networks, and volumes |
| 3. Run tests | Partially implemented through manual validation and an initial smoke test; formal suite is the next milestone |
| 4. Kubernetes orchestration | Not part of this directory; planned after testing and CI/CD |
| 5. CI/CD pipeline | Not implemented yet; this setup provides its build and deployment foundation |
| 6. Infrastructure as Code | Not implemented yet |
| 7. Monitoring | Basic NGINX status endpoint only; Prometheus and Grafana are planned |
| 8. DevSecOps | Network isolation and basic NGINX hardening implemented; scanning and secret management are pending |
| 9. Disaster recovery | Persistent volumes implemented, but backups and restore procedures are pending |
| 10. Documentation | This README documents the Docker-specific architecture and operations |

The completed Docker milestone provides a stable base for the next development sequence:

```text
Docker setup
    |
    v
Automated testing
    |
    v
CI/CD pipeline and container registry
    |
    v
Kubernetes deployment
```

---

## 2. Architecture

The stack contains five services:

- **NGINX** - the only public entry point and reverse proxy
- **PrestaShop** - the primary e-commerce storefront
- **PrestaShop database** - MySQL-compatible persistent database
- **WordPress** - the secondary blog and content-management system
- **WordPress database** - MariaDB persistent database

```text
                         Client
                            |
                            v
                  NGINX reverse proxy
                public port 8080 / 8081
                    /                \
                   /                  \
                  v                    v
         PrestaShop:'/'     WordPress:'/wordpress/'
                  |                    |
                  v                    v
        PrestaShop database     WordPress database
```

### Routing decision

The project currently uses path-based routing:

| Route | Target |
|---|---|
| `/` | PrestaShop |
| `/wordpress/` | WordPress |
| `/healthy` | NGINX liveness endpoint |
| `/nginx_status` | Internal NGINX statistics |

PrestaShop owns `/` because its storefront, themes, images, modules, JavaScript, cart, and checkout use root-relative paths naturally.

WordPress is explicitly configured to run below `/wordpress/` with `WP_HOME` and `WP_SITEURL`.

Host-based routing with separate subdomains remains a possible future alternative, especially when Kubernetes Ingress and TLS will be introduced, because these make it easier then to separate the concerns technically.

---

## 3. Directory Structure

```text
docker-setup/
├── README.md
├── docker-compose.dev.yaml
├── docker-compose.prod.yaml
├── .env.dev
├── .env.prod
├── nginx/
│   ├── Dockerfile
│   └── nginx.conf
├── wordpress/
│   └── Dockerfile
├── wordpress-db/
│   └── Dockerfile
├── prestashop/
│   └── Dockerfile
└── prestashop-db/
    └── Dockerfile
```

Environment files containing actual values must not be committed:

```text
.env.dev
.env.prod
```

Only `.env.example` can be version-controlled, but I haven't included it into my repository.

Hence, read the documentation properly :-). 

---

## 4. Docker Images

Each service has its own Dockerfile so that the complete platform can be built reproducibly.

The current Compose files build images locally:

```yaml
build:
  context: ./nginx
image: liora-nginx-proxy:dev
```

This approach is currently intentional.

Images previously pushed from an Apple Silicon system used the `linux/arm64` architecture, while the target EC2 host uses `linux/amd64`. 

Registry-based deployment is therefore postponed until the CI/CD milestone, where Docker Buildx will create either:

- `linux/amd64` images, or
- multi-architecture images for both `linux/amd64` and `linux/arm64`.

### Multi-stage builds

Multi-stage builds are not currently used for the CMS and database images because they are based on complete vendor runtime images. 

Reusing the same heavy runtime image in multiple stages would not provide a meaningful size reduction.

---

## 5. Development and Production Environments

Two independent Docker Compose projects are provided.

### Development environment

File:

```text
docker-compose.dev.yaml
```

Purpose:

- local development,
- feature validation,
- test execution,
- fast rebuilds,
- non-production credentials.

Typical characteristics:

| Setting | Development |
|---|---|
| Compose project | `liora-webservices-dev` |
| NGINX host port | `8080` |
| Image tags | `:dev` |
| Database names | development-specific |
| Networks | development-specific |
| Volumes | development-specific |
| Restart policy | `on-failure` |
| Backend networks | isolated by membership |

### Production-like environment

File:

```text
docker-compose.prod.yaml
```

Purpose:

- stable production-like validation,
- public browser testing,
- future CI/CD deployment target before Kubernetes,
- stricter service startup and isolation.

Typical characteristics:

| Setting | Production-like |
|---|---|
| Compose project | `liora-webservices-prod` |
| NGINX host port | `8081` |
| Image tags | `:prod` |
| Database names | production-specific |
| Networks | production-specific |
| Volumes | production-specific |
| Restart policy | `always` |
| Database health checks | enabled |
| Backend networks | marked `internal: true` |

---

## 6. Network Design

Each environment uses three bridge networks.

### Proxy network

Members:

```text
nginx
wordpress
prestashop
```

Purpose:

- NGINX can forward HTTP requests to both CMS containers.
- Database services are not attached to this network.

### WordPress backend network

Members:

```text
wordpress
wordpress-db
```

Purpose:

- WordPress can resolve and connect to `wordpress-db`.
- NGINX and PrestaShop cannot directly resolve the WordPress database.

### PrestaShop backend network

Members:

```text
prestashop
prestashop-db
```

Purpose:

- PrestaShop can resolve and connect to `prestashop-db`.
- NGINX and WordPress cannot directly resolve the PrestaShop database.

### Verified DNS behavior

The following behavior was manually validated:

```text
NGINX -> wordpress             reachable
NGINX -> prestashop            reachable
NGINX -> wordpress-db          not resolvable
NGINX -> prestashop-db         not resolvable
WordPress -> wordpress-db      reachable
PrestaShop -> prestashop-db    reachable
```

This validation will later become a dedicated automated network-isolation test.

---

## 7. Persistent Storage

Named Docker volumes are used for CMS files and database data.

### Development volumes

```text
liora-dev-wordpress-files
liora-dev-wordpress-db-data
liora-dev-prestashop-files
liora-dev-prestashop-db-data
```

### Production volumes

```text
liora-prod-wordpress-files
liora-prod-wordpress-db-data
liora-prod-prestashop-files
liora-prod-prestashop-db-data
```

Persistence was validated by:

1. starting the Compose stack,
2. confirming the services were reachable,
3. running `docker compose down`,
4. starting the stack again without `-v`,
5. confirming the services remained functional.

Important distinction:

```bash
docker compose down
```

removes containers and Compose networks but keeps named volumes.

```bash
docker compose down -v
```

also deletes the named volumes and all stored CMS and database data.

Named volumes provide persistence, but they are **not backups**. 

Backup and restore automation belongs to the disaster-recovery milestone.

---

## 8. NGINX Responsibilities

NGINX is the only service that publishes a host port.

It provides:

- reverse-proxy routing,
- a single external entry point,
- request-header forwarding,
- request-body size control,
- upstream connection reuse,
- connection and response timeouts,
- an external liveness endpoint,
- internal status information,
- reduced version disclosure.

### Active routes

```text
/             -> PrestaShop
/wordpress/   -> WordPress
/healthy      -> NGINX liveness
/nginx_status -> internal NGINX statistics
```

### Liveness endpoint

```text
/healthy
```

This endpoint confirms only that NGINX is running.

It does not verify:

- WordPress,
- PrestaShop,
- database connectivity,
- application workflows.

Those checks belong in the integration and smoke test suites.

### Internal NGINX statistics

```text
/nginx_status
```

Access is restricted to loopback addresses inside the NGINX container.

This provides basic connection statistics, but it is not a replacement for Prometheus and Grafana.

---

## 9. Prerequisites

Required tools:

- Docker Engine
- Docker Compose v2
- Git
- `curl`

Verify:

```bash
docker --version
docker compose version
git --version
curl --version
```

For public production-like access, the host firewall and cloud security group must allow inbound TCP traffic on port the specified port in your `env.prod` file .

---

## 10. Environment Configuration

Create the environment files from the example:

```bash
cp .env.example .env.dev
cp .env.example .env.prod
```

Then adjust the values for each environment.

### Example `.env.dev`

```env
NGINX_PORT=8080

WORDPRESS_PUBLIC_HOST=localhost:8080
WORDPRESS_DB_NAME=wordpress_dev
WORDPRESS_DB_USER=wordpress
WORDPRESS_DB_PASSWORD=change_me
WORDPRESS_DB_ROOT_PASSWORD=change_me

PRESTASHOP_PUBLIC_HOST=localhost:8080
PRESTASHOP_DB_NAME=prestashop_dev
PRESTASHOP_DB_USER=prestashop
PRESTASHOP_DB_PASSWORD=change_me
PRESTASHOP_DB_ROOT_PASSWORD=change_me
```
Same can be applied to your `env.prod`, but use production ready (safer) password and variables.
We use port `8081` for setting up the production environment in the following examples, but you can define yourselves.

Never commit real passwords.

Use `.gitignore` to avoid password leaks.

The CI/CD pipeline will later provide these values through protected variables or secrets.

Kubernetes will later use Secrets and ConfigMaps.

---

## 11. Run the Development Environment

All commands in this README assume the current directory is `docker-setup/`.

### Validate the configuration

```bash
docker compose \
  --env-file .env.dev \
  -f docker-compose.dev.yaml \
  config
```

### Build and start

```bash
docker compose \
  --env-file .env.dev \
  -f docker-compose.dev.yaml \
  up -d --build
```

### Check services

```bash
docker compose \
  --env-file .env.dev \
  -f docker-compose.dev.yaml \
  ps
```

### Validate NGINX

```bash
docker compose \
  --env-file .env.dev \
  -f docker-compose.dev.yaml \
  exec nginx nginx -t
```

### Local routes

```text
PrestaShop: http://localhost:8080/
WordPress:  http://localhost:8080/wordpress/
Health:     http://localhost:8080/healthy
```

### Stop development

```bash
docker compose \
  --env-file .env.dev \
  -f docker-compose.dev.yaml \
  down
```

---

## 12. Run the Production-Like Environment

### Validate the configuration

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  config
```

### Build and start

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  up -d --build
```

### Check service state

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  ps
```

The database services should report `healthy`.

### Validate NGINX

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  exec nginx nginx -t
```

### Local routes

```text
PrestaShop: http://localhost:8081/
WordPress:  http://localhost:8081/wordpress/
Health:     http://localhost:8081/healthy
```

### Public routes

```text
PrestaShop:
http://yourdomain.com:8081/

WordPress:
http://yourdomain.com:8081/wordpress/

NGINX health:
http://yourdomain.com:8081/healthy
```

### Stop production-like services

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  down
```

---

## 13. Operational Validation

### Check published ports

```bash
docker ps
```

Expected:

- only NGINX publishes a host port,
- CMS containers expose only internal port `80`,
- database containers do not publish port `3306` to the host.

### Inspect networks

```bash
docker network ls
```

Inspect one network:

```bash
docker network inspect <network-name>
```

### Inspect volumes

```bash
docker volume ls
```

### Follow all logs

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  logs -f
```

### Follow one service

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  logs -f nginx
```

Available service names:

```text
nginx
wordpress
wordpress-db
prestashop
prestashop-db
```

### Check NGINX liveness

```bash
curl --connect-timeout 5 \
  -i http://localhost:8081/healthy
```

### Check internal NGINX statistics

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yaml \
  exec nginx \
  wget -qO- http://127.0.0.1/nginx_status
```

---

## 14. Completed Validation

The following Docker-specific checks have passed:

- [x] All service images build locally.
- [x] Development Compose configuration resolves correctly.
- [x] Production Compose configuration resolves correctly.
- [x] All five containers start.
- [x] Both database containers become healthy in production.
- [x] NGINX configuration validation passes.
- [x] Only NGINX publishes a host port.
- [x] PrestaShop is available from `/`.
- [x] PrestaShop assets load correctly from the root path.
- [x] WordPress is available from `/wordpress/`.
- [x] NGINX liveness returns HTTP `200`.
- [x] Backend database networks are separated from the proxy network.
- [x] Docker DNS resolves only permitted service names.
- [x] Named volumes survive container recreation.
- [x] Production-like access works through the public hostname on port `8081`.

## Next Milestone

The Docker setup has been implemented and validated.

The next project phase will introduce a structured automated test suite covering:

- configuration validation,
- smoke tests,
- service integration,
- HTTP route contracts,
- network and DNS isolation.

After the test suite is stable, it will be integrated into the CI/CD pipeline before deployment to Kubernetes.