# liora-devops-webservices

DevOps bootcamp group project focused on building, containerizing, deploying, and operating a web services platform with WordPress, PrestaShop, NGINX reverse proxy, Docker, Kubernetes, CI/CD, Infrastructure as Code (IaC), monitoring, and disaster recovery.

This project runs WordPress and PrestaShop as containerized web applications behind an NGINX reverse proxy.

## Features

- Reverse proxy with NGINX
- Automatic public IP detection
- Automatic NGINX configuration update
- WordPress and PrestaShop behind a single endpoint
- Health checks
- Smoke tests
- Separate development and production Compose files
- One-command deployment using deploy.sh

## Architecture

Services included:

- NGINX Reverse Proxy
- WordPress
- WordPress MySQL Database
- PrestaShop
- PrestaShop MySQL Database

Only NGINX is exposed to the host machine.

Applications:

```text
http://SERVER_IP:8080/wordpress/
http://SERVER_IP:8080/prestashop/
```

---

# Deployment

## 1. Make the deployment script executable

```bash
chmod +x deploy.sh
```

## 2. Start the project

```bash
./deploy.sh
```

This script automatically:

- detects the current public IP
- updates the NGINX configuration
- rebuilds containers when required
- starts all services

---

# VM Restart / Public IP Change

Whenever the VM is restarted or its public IP changes, simply run:

```bash
./deploy.sh
```

---

# Check the detected public IP

```bash
export SERVER_HOST="$(curl -fsS https://checkip.amazonaws.com | tr -d '\n'):8080"

echo "$SERVER_HOST"
```

---

# Check container status

```bash
docker compose ps
```

---

# Health check

```bash
curl -i http://127.0.0.1:8080/health
```

---

# Test WordPress

```bash
curl -IL --max-redirs 5 \
-H "Host: ${SERVER_HOST}" \
http://127.0.0.1:8080/wordpress/
```

---

# Test PrestaShop

```bash
curl -IL --max-redirs 5 \
-H "Host: ${SERVER_HOST}" \
http://127.0.0.1:8080/prestashop/
```

---

# View logs

```bash
docker compose logs --tail=100 nginx
docker compose logs --tail=100 wordpress
docker compose logs --tail=100 prestashop
```

Follow logs in real time:

```bash
docker compose logs -f
```

---

# Run tests

```bash
chmod +x tests/run-tests.sh
chmod +x tests/smoke/smoke-test.sh

./tests/run-tests.sh
```

---

# Stop the project

```bash
docker compose down
```

---

# Complete reset

```bash
docker compose down -v
```

Then run:

```bash
./deploy.sh
```

The applications will be installed again with fresh databases.

---

# Rebuild after configuration changes

If you modify one of the following files:

- docker-compose.yml
- nginx/default.conf
- Dockerfile

simply run:

```bash
./deploy.sh
```

or manually:

```bash
docker compose up -d --build --force-recreate
```

---

# Daily workflow

```bash
cd ~/liora-devops-webservices

chmod +x deploy.sh

./deploy.sh

docker compose ps
```
---

# Docker Hub Images

The CI/CD pipeline automatically builds and publishes the following Docker images:

- shabbyalaei/liora-nginx
- shabbyalaei/liora-wordpress
- shabbyalaei/liora-prestashop

Images are versioned using the Jenkins build number and the latest tag.

---

# CI/CD Pipeline

The Jenkins pipeline performs the following stages automatically:

1. Pipeline Check
2. Environment Information
3. Prepare Environment Files
4. Validate Docker Compose Files
5. Build Docker Images
6. Deploy Development Environment
7. Run Health Checks
8. Run Smoke Tests
9. Docker Hub Login
10. Push Docker Images
11. Deploy to Staging
12. Test Staging
13. Manual Production Approval
14. Deploy to Production
15. Test Production

---

# Project Structure

```text
liora-devops-webservices/
│
├── docker-setup/
│   ├── nginx/
│   ├── wordpress/
│   └── prestashop/
│
├── helm/
│   └── liora/
│       ├── templates/
│       ├── values.yaml
│       ├── values-dev.yaml
│       ├── values-staging.yaml
│       └── values-prod.yaml
│
├── kubernetes/
│
├── monitoring/
│
├── tests/
│   ├── health/
│   ├── integration/
│   ├── kubernetes/
│   ├── network/
│   ├── routing/
│   ├── smoke/
│   ├── support/
│   └── unit/
│
├── docs/
│   └── security.md
│
├── terraform/
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.staging.yml
├── docker-compose.prod.yml
├── Jenkinsfile
├── deploy.sh
└── README.md

## HTTPS / TLS

The Kubernetes development environment supports HTTPS through the Traefik
Ingress Controller with TLS termination on port 443.

For setup, deployment and local browser testing instructions, see
[HTTPS and TLS](docs/https.md).

## Security Scanning

Docker images are automatically scanned for HIGH and CRITICAL vulnerabilities
with Trivy as part of the Jenkins CI pipeline.

The pipeline currently uses a report-only security policy. Fixable
OS-level vulnerabilities are remediated where possible, while remaining
application-level findings are documented and evaluated before dependency
upgrades.

For details about vulnerability remediation and known security findings, see
[Security and Vulnerability Management](docs/security.md).

