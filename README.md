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