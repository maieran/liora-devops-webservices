# Kubernetes Deployment

This directory contains the Kubernetes implementation of the Liora DevOps web services stack.

The current configuration deploys the development environment into the namespace:

```text
liora-dev
```

The implementation follows the principle:

> **One manifest file = one top-level Kubernetes API resource**

This keeps Services, Deployments, StatefulSets, ConfigMaps and NetworkPolicies clearly separated and makes the later migration to Helm templates easier to understand.

---

## Kubernetes Architecture

```text
                         External Request
                                |
                                | NodePort :30080
                                v
                         nginx-service
                                |
                                v
                        nginx-deployment
                          /          \
                         /            \
                      :80              :80
                       v                v
          wordpress-app-service   prestashop-app-service
                       |                |
                       v                v
               wordpress-app      prestashop-app
                       |                |
                    :3306            :3306
                       |                |
                       v                v
      wordpress-db-service-headless   prestashop-db-service-headless
                       |                |
                       v                v
               wordpress-db       prestashop-db
                StatefulSet        StatefulSet
                       |                |
                       v                v
                      PVC              PVC
```

The databases use StatefulSets because persistent storage and stable database identities must survive Pod recreation.

WordPress, PrestaShop and Nginx use Deployments because their Pods are replaceable application workloads.

---

## Public Routing

Nginx is the only public entry point into the stack.

The development environment exposes Nginx through:

```text
NodePort 30080
```

Current routing:

```text
/              -> PrestaShop (canonical route)
/wordpress/    -> WordPress
/health        -> Nginx health endpoint
/prestashop    -> 301 redirect to /prestashop/
/prestashop/   -> optional PrestaShop convenience alias
```

Additional WordPress redirects are configured for:

```text
/wordpress
/wp-admin/
/wp-login.php
```

PrestaShop is canonically served from `/` because it generates root-relative URLs for assets and application routes.

The `/prestashop/` route is kept only as a convenience alias. The canonical PrestaShop route remains `/`.

---

## Resource Structure

```text
kubernetes/
├── README.md
└── base/
    ├── namespace/
    │   └── namespace.yaml
    │
    ├── database/
    │   ├── wordpress-db-service-headless.yaml
    │   ├── wordpress-db-statefulset.yaml
    │   ├── prestashop-db-service-headless.yaml
    │   └── prestashop-db-statefulset.yaml
    │
    ├── applications/
    │   ├── wordpress-service.yaml
    │   ├── wordpress-deployment.yaml
    │   ├── prestashop-service.yaml
    │   ├── prestashop-configmap.yaml
    │   └── prestashop-deployment.yaml
    │
    ├── nginx/
    │   ├── nginx-configmap.yaml
    │   ├── nginx-deployment.yaml
    │   └── nginx-service.yaml
    │
    ├── network-policy/
    │   ├── default-deny.yaml
    │   ├── allow-nginx-ingress.yaml
    │   ├── allow-nginx-wordpress.yaml
    │   ├── allow-nginx-prestashop.yaml
    │   ├── allow-wordpress-db.yaml
    │   └── allow-prestashop-db.yaml
    │
    └── secrets/
        └── README.md
```

---

## Database Services

Both databases use Headless Services:

```text
wordpress-db-service-headless
prestashop-db-service-headless
```

The applications connect through:

```text
wordpress-app
    -> wordpress-db-service-headless:3306

prestashop-app
    -> prestashop-db-service-headless:3306
```

Each database StatefulSet requests:

```text
1Gi
ReadWriteOnce
```

The current K3s environment uses the default `local-path` StorageClass.

Database image versions are pinned to avoid unexpected minor-version upgrades during redeployment.

---

## Startup Dependencies

Kubernetes does not use Docker Compose-style `depends_on`.

Init Containers are used to wait for required dependencies before the main containers start.

WordPress waits for:

```text
wordpress-db-service-headless:3306
```

PrestaShop waits for:

```text
prestashop-db-service-headless:3306
```

These database dependency checks use TCP connectivity because the applications only need MySQL to be reachable on port `3306` before startup.

Nginx waits for both application Services over HTTP:

```text
http://wordpress-app-service/
http://prestashop-app-service/
```

The Nginx Init Container performs HTTP requests instead of only checking whether TCP port `80` is open.

Redirect responses are accepted because WordPress and PrestaShop can legitimately redirect during startup. Connection failures and HTTP `4xx`/`5xx` responses keep the Init Container waiting.

This creates the startup order:

```text
Databases
    |
    v
Applications
    |
    v
Nginx
```

---

## Health Probes

### MySQL

The database StatefulSets use `mysqladmin ping` for readiness and liveness checks.

### WordPress

WordPress uses TCP probes on port `80`:

```text
startupProbe
readinessProbe
livenessProbe
```

TCP probes are used for container-level lifecycle checks so application redirect behavior does not interfere with Kubernetes health evaluation.

Public HTTP routing is validated externally through Nginx.

### PrestaShop

PrestaShop also uses TCP startup, readiness and liveness probes on port `80`.

The startup probe gives PrestaShop enough time to initialize before Kubernetes evaluates normal readiness and liveness.

Public HTTP behavior is validated through Nginx and the automated runtime tests.

---

## Network Security

The namespace uses Kubernetes `NetworkPolicy` resources to restrict Pod-to-Pod traffic.

A default ingress deny policy is applied:

```text
default-deny-ingress
```

Only explicitly required connections are then permitted.

### Allowed Traffic

```text
External   ---> Nginx
Nginx      ---> WordPress
Nginx      ---> PrestaShop
WordPress  ---> WordPress DB
PrestaShop ---> PrestaShop DB
```

### Blocked Traffic

```text
WordPress  -X-> PrestaShop DB
PrestaShop -X-> WordPress DB
Nginx      -X-> WordPress DB
Nginx      -X-> PrestaShop DB
```

Nginx is intentionally reachable from external sources on port `80` because it is currently the public entry point exposed by the `nginx-service` NodePort.

WordPress, PrestaShop and both databases remain restricted by their respective NetworkPolicies.

If an Ingress Controller later becomes the public entry point, the Nginx ingress policy can be restricted further to traffic from that controller.

Only ingress is currently default-denied. Egress traffic is not currently restricted.

---

## Secrets

Database credentials are stored in the Kubernetes Secret:

```text
liora-db-secrets
```

Real credentials must never be committed to Git.

The Secret must be created before deploying workloads that reference it.

See:

```text
kubernetes/base/secrets/README.md
```

for the required keys and creation commands.

---

# Deployment

## 1. Create the Namespace

```bash
kubectl apply \
  -f kubernetes/base/namespace/
```

Verify:

```bash
kubectl get namespace liora-dev
```

---

## 2. Create the Database Secret

Create:

```text
liora-db-secrets
```

according to:

```text
kubernetes/base/secrets/README.md
```

Verify:

```bash
kubectl get secret \
  liora-db-secrets \
  -n liora-dev
```

---

## 3. Deploy Databases

```bash
kubectl apply \
  -f kubernetes/base/database/
```

Wait until both database Pods are running:

```bash
kubectl get pods \
  -n liora-dev \
  -w
```

Expected:

```text
wordpress-db-0     1/1 Running
prestashop-db-0    1/1 Running
```

Verify persistent storage:

```bash
kubectl get pvc \
  -n liora-dev
```

Both PVCs should be:

```text
Bound
```

---

## 4. Configure and Deploy Applications

### Configure the PrestaShop Public Domain

PrestaShop requires its externally reachable host and port to generate correct URLs, redirects and asset paths.

The PrestaShop Deployment no longer hard-codes these environment-specific values.

Instead, it reads:

```text
PUBLIC_HOST
NGINX_NODE_PORT
```

from `prestashop-configmap`.

Inside the Deployment, `PS_DOMAIN` is constructed from these values:

```yaml
- name: PUBLIC_HOST
  valueFrom:
    configMapKeyRef:
      name: prestashop-configmap
      key: PUBLIC_HOST

- name: NGINX_NODE_PORT
  valueFrom:
    configMapKeyRef:
      name: prestashop-configmap
      key: NGINX_NODE_PORT

- name: PS_DOMAIN
  value: "$(PUBLIC_HOST):$(NGINX_NODE_PORT)"
```

For the current development environment, determine the public IP of the Kubernetes Node:

```bash
PUBLIC_IP=$(curl -s https://checkip.amazonaws.com)
```

The current Nginx NodePort is:

```bash
NODE_PORT=30080
```

Verify the resulting public address:

```bash
echo "$PUBLIC_IP:$NODE_PORT"
```

Create or update the ConfigMap:

```bash
kubectl create configmap prestashop-configmap \
  --namespace liora-dev \
  --from-literal=PUBLIC_HOST="$PUBLIC_IP" \
  --from-literal=NGINX_NODE_PORT="$NODE_PORT" \
  --dry-run=client \
  -o yaml \
  | kubectl apply -f -
```

Verify:

```bash
kubectl get configmap prestashop-configmap \
  -n liora-dev \
  -o yaml
```

Example:

```yaml
data:
  NGINX_NODE_PORT: "30080"
  PUBLIC_HOST: "108.131.138.129"
```

This keeps the environment-specific public address outside the PrestaShop Deployment and prepares the same settings for later Helm values.

### Deploy the Applications

```bash
kubectl apply \
  -f kubernetes/base/applications/
```

Verify:

```bash
kubectl get deployment \
  -n liora-dev
```

Expected:

```text
wordpress-app     1/1
prestashop-app    1/1
```

Verify that PrestaShop received the expected values:

```bash
kubectl exec \
  -n liora-dev \
  deployment/prestashop-app \
  -- printenv PUBLIC_HOST NGINX_NODE_PORT PS_DOMAIN
```

Example:

```text
108.131.138.129
30080
108.131.138.129:30080
```

---

## 5. Deploy Nginx

```bash
kubectl apply \
  -f kubernetes/base/nginx/
```

Verify:

```bash
kubectl get deployment \
  -n liora-dev
```

Expected:

```text
nginx-deployment   1/1
```

Check the NodePort:

```bash
kubectl get svc nginx-service \
  -n liora-dev
```

---

## 6. Verify Public Routing

Set:

```bash
export BASE_URL="http://<NODE_PUBLIC_IP>:30080"
```

Nginx health:

```bash
curl -i "$BASE_URL/health"
```

Expected:

```text
HTTP/1.1 200 OK
```

WordPress:

```bash
curl -IL \
  --max-redirs 10 \
  "$BASE_URL/wordpress/"
```

PrestaShop:

```bash
curl -IL \
  --max-redirs 10 \
  "$BASE_URL/"
```

Optional PrestaShop alias:

```bash
curl -I "$BASE_URL/prestashop"
```

Expected:

```text
HTTP/1.1 301 Moved Permanently
```

---

## 7. Apply NetworkPolicies

Only after normal application communication has been verified:

```bash
kubectl apply \
  -f kubernetes/base/network-policy/
```

Verify:

```bash
kubectl get networkpolicy \
  -n liora-dev
```

After applying the policies, repeat the public routing tests to confirm required application traffic still works.

---

## Verify the Complete Environment

```bash
kubectl get \
  pods,deployments,statefulsets,services,pvc,networkpolicies \
  -n liora-dev
```

All application and database Pods should be:

```text
Running
```

All Deployments and StatefulSets should report their desired replicas as ready.

All database PVCs should be:

```text
Bound
```

---

## Current Development Topology

```text
External Client
      |
      | :30080
      v
 nginx-service
      |
      v
nginx-deployment
    /       \
   /         \
  v           v
WordPress   PrestaShop
   |           |
   v           v
WP MySQL     PS MySQL
   |           |
   v           v
  PVC         PVC
```

The current Kubernetes implementation serves as the manually validated base architecture.

---

# Next Phase: Helm Chart Implementation

The next phase converts the working raw Kubernetes manifests into Helm templates.

The purpose of Helm is not to redesign the current architecture. The chart should preserve the validated relationships between Nginx, WordPress, PrestaShop, the databases, persistent storage and NetworkPolicies while making environment-specific configuration reusable.

## Configuration to Parameterize

Values that vary between environments should move into Helm values, for example:

```yaml
environment: dev

nginx:
  replicaCount: 1
  service:
    type: NodePort
    nodePort: 30080

wordpress:
  replicaCount: 1
  debug: true

prestashop:
  replicaCount: 1
  devMode: true
  publicHost: "108.131.138.129"

database:
  storageSize: 1Gi
```

Environment-specific values files can then be used:

```text
values-dev.yaml
values-staging.yaml
values-prod.yaml
```

Conceptually:

```text
values-dev.yaml
values-staging.yaml
values-prod.yaml
        |
        v
   Helm Templates
        |
        v
Kubernetes Resources
```

The existing raw Kubernetes implementation already separates the PrestaShop public address from its Deployment through `prestashop-configmap`.

The Helm implementation will extend this approach so values such as public host, NodePort, replica counts, debug/development settings, image tags and storage settings can be managed without duplicating manifests.

## Secrets

Secrets must not be committed directly inside Helm values files.

The existing Secret:

```text
liora-db-secrets
```

can continue to be referenced by the workloads unless a dedicated secret-management solution is introduced later.

## Helm Migration Principle

The raw Kubernetes manifests remain the reference implementation.

The Helm chart should preserve:

- Nginx as the public entry point
- `/` as the canonical PrestaShop route
- `/wordpress/` as the WordPress route
- the optional `/prestashop/` convenience alias
- StatefulSets for both databases
- persistent database storage
- application-to-database network isolation
- Nginx-to-application communication
- Kubernetes health probes
- startup dependency checks
- Dev, Staging and Prod configuration separation

The Helm implementation should parameterize the existing working architecture rather than introduce unnecessary architectural changes.
