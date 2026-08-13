# Kubernetes Deployment

This directory contains the Kubernetes implementation of the Liora DevOps web services stack.

The current configuration deploys the development environment into the namespace:

```text
liora-dev
```

The implementation intentionally follows the principle:

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
                         /          \\
                        /            \\
                     :80              :80
                      v                v
          wordpress-app-service   prestashop-app-service
                      |                |
                      v                v
              wordpress-app      prestashop-app
                      |                |
                   :3306            :3306
                      |                |
                      v                v
     wordpress-db-service-headless   prestashop-db-service-headless
                      |                |
                      v                v
              wordpress-db       prestashop-db
               StatefulSet        StatefulSet
                      |                |
                      v                v
                     PVC              PVC
```

The databases use StatefulSets because their persistent storage and stable network identity must survive Pod recreation.

The application workloads use Deployments because WordPress, PrestaShop and Nginx are replaceable application Pods.

---

## Public Routing

Nginx is the only public entry point into the application stack.

The development environment exposes Nginx through:

```text
NodePort 30080
```

Routing:

```text
/             -> PrestaShop
/wordpress/   -> WordPress
/health       -> Nginx health endpoint
```

Additional redirects are configured for paths such as:

```text
/wordpress
/prestashop
/wp-admin/
/wp-login.php
```

PrestaShop is canonically served from `/` because it generates root-relative URLs for assets and application routes.

---

## Resource Structure

```text
kubernetes/
├── README.md
└── base/
    ├── namespace/
    │   └── namespace.yaml
    │
    ├── database/
    │   ├── wordpress-db-service-headless.yaml
    │   ├── wordpress-db-statefulset.yaml
    │   ├── prestashop-db-service-headless.yaml
    │   └── prestashop-db-statefulset.yaml
    │
    ├── applications/
    │   ├── wordpress-service.yaml
    │   ├── wordpress-deployment.yaml
    │   ├── prestashop-service.yaml
    │   └── prestashop-deployment.yaml
    │
    ├── nginx/
    │   ├── nginx-configmap.yaml
    │   ├── nginx-deployment.yaml
    │   └── nginx-service.yaml
    │
    ├── network-policy/
    │   ├── default-deny.yaml
    │   ├── allow-nginx-ingress.yaml
    │   ├── allow-nginx-wordpress.yaml
    │   ├── allow-nginx-prestashop.yaml
    │   ├── allow-wordpress-db.yaml
    │   └── allow-prestashop-db.yaml
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

These Services provide stable DNS names for the database StatefulSets.

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

---

## Startup Dependencies

Kubernetes does not use Docker Compose-style `depends_on`.

Instead, Init Containers are used to ensure required dependencies are reachable before the main application container starts.

WordPress waits for:

```text
wordpress-db-service-headless:3306
```

PrestaShop waits for:

```text
prestashop-db-service-headless:3306
```

Nginx waits for:

```text
wordpress-app-service:80
prestashop-app-service:80
```

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

HTTP probes are intentionally avoided because WordPress is publicly configured under `/wordpress/`.

Direct HTTP probes against the WordPress Pod would bypass Nginx and follow WordPress redirects to `/wordpress/...`, which can create a redirect loop.

HTTP routing is therefore validated externally through Nginx instead.

### PrestaShop

PrestaShop also uses TCP startup, readiness and liveness probes on port `80`.

The startup probe gives PrestaShop enough time to complete its initial installation before Kubernetes evaluates normal readiness and liveness.

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
External   ---> Nginx
Nginx      ---> WordPress
Nginx      ---> PrestaShop
WordPress  ---> WordPress DB
PrestaShop ---> PrestaShop DB
```

### Blocked Traffic

```text
WordPress  -X-> PrestaShop DB
PrestaShop -X-> WordPress DB
Nginx      -X-> WordPress DB
Nginx      -X-> PrestaShop DB
```

Architecture:

```text
                     External
                        |
                        | :80
                        v
                     [Nginx]
                     /     \\
                  :80       :80
                   /         \\
                  v           v
          [WordPress]     [PrestaShop]
               |               |
             :3306           :3306
               |               |
               v               v
        [wordpress-db]   [prestashop-db]
```

Only ingress is currently default-denied.

Egress traffic is not currently restricted.

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
kubectl apply \\
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
kubectl get secret \\
  liora-db-secrets \\
  -n liora-dev
```

---

## 3. Deploy Databases

```bash
kubectl apply \\
  -f kubernetes/base/database/
```

Wait until both databases are healthy:

```bash
kubectl get pods \\
  -n liora-dev \\
  -w
```

Expected:

```text
wordpress-db-0     1/1 Running
prestashop-db-0    1/1 Running
```

Verify persistent storage:

```bash
kubectl get pvc \\
  -n liora-dev
```

Both PVCs should be:

```text
Bound
```

---

## 4. Configure and Deploy Applications

### Configure the PrestaShop Public Domain

Before deploying the applications, configure the public Kubernetes Node address in:

```text
kubernetes/base/applications/prestashop-deployment.yaml
```

Set the `PS_DOMAIN` environment variable to the public Node IP and the Nginx NodePort:

```yaml
- name: PS_DOMAIN
  value: "YOUR_NODE_IP:30080"
```

Replace `YOUR_NODE_IP` with the public IP address of the Kubernetes Node.

`PS_DOMAIN` is required because PrestaShop uses its configured public domain when generating URLs, redirects and asset links.

This is a manual environment-specific setting in the current raw Kubernetes implementation. In the next Helm implementation, this value will be moved into environment-specific Helm values instead of being hard-coded in the Deployment manifest.

Then deploy the applications:

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

---

## 5. Deploy Nginx

```bash
kubectl apply \\
  -f kubernetes/base/nginx/
```

Verify:

```bash
kubectl get deployment \\
  -n liora-dev
```

Expected:

```text
nginx-deployment   1/1
```

Check the NodePort:

```bash
kubectl get svc nginx-service \\
  -n liora-dev
```

---

## 6. Verify Public Routing

Set:

```bash
export BASE_URL="http\://<NODE_PUBLIC_IP>:30080"
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
curl -IL \\
  --max-redirs 10 \\
  "$BASE_URL/wordpress/"
```

PrestaShop:

```bash
curl -IL \\
  --max-redirs 10 \\
  "$BASE_URL/"
```

---

## 7. Apply NetworkPolicies

Only after the normal application communication has been verified:

```bash
kubectl apply \\
  -f kubernetes/base/network-policy/
```

Verify:

```bash
kubectl get networkpolicy \\
  -n liora-dev
```

After applying the policies, repeat the public routing tests to ensure that required application traffic still works.

---

## Verify the Complete Environment

```bash
kubectl get \\
  pods,deployments,statefulsets,services,pvc,networkpolicies \\
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
    /       \\
   /         \\
  v           v
WordPress   PrestaShop
   |           |
   v           v
WP MySQL     PS MySQL
   |           |
   v           v
  PVC         PVC
```

The current Kubernetes implementation serves as the manually validated base architecture.

The next implementation phase converts these resources into Helm templates while keeping the same resource relationships and network isolation model. Environment-specific values such as PrestaShop `PS_DOMAIN` will then move out of the raw manifests and into Helm values.