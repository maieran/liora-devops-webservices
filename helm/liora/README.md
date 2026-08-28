# Liora Helm Chart

Helm chart for deploying the Liora web platform on Kubernetes.

The chart deploys:

- Nginx as the public entry point
- WordPress
- PrestaShop
- MySQL for WordPress
- MySQL for PrestaShop
- Persistent volumes for both databases
- ConfigMaps
- NetworkPolicies

---

## Architecture

```text
                 Environment NodePort
          Dev:30080 / Staging:30081 / Prod:30082
                              |
                              v
                       nginx-service
                              |
                              v
                     nginx-deployment
                       /          \
                      /            \
                     v              v
          wordpress-app-service   prestashop-app-service
                  |                       |
                  v                       v
          wordpress-app            prestashop-app
                  |                       |
                  v                       v
 wordpress-db-service-headless   prestashop-db-service-headless
                  |                       |
                  v                       v
          wordpress-db-0          prestashop-db-0
                  |                       |
                  v                       v
                 PVC                     PVC
```

Public routes:

```text
/              -> PrestaShop
/prestashop/   -> PrestaShop convenience alias
/wordpress/    -> WordPress
/health        -> Nginx health endpoint
```

---

## Chart structure

```text
helm/liora/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml
└── templates/
    ├── nginx-configmap.yaml
    ├── nginx-deployment.yaml
    ├── nginx-service.yaml
    ├── prestashop-configmap.yaml
    ├── prestashop-deployment.yaml
    ├── prestashop-service.yaml
    ├── prestashop-db-service.yaml
    ├── prestashop-db-statefulset.yaml
    ├── wordpress-deployment.yaml
    ├── wordpress-service.yaml
    ├── wordpress-db-service.yaml
    ├── wordpress-db-statefulset.yaml
    └── networkpolicy-*.yaml
```

---

## Requirements

You need:

- Kubernetes cluster
- `kubectl`
- Helm
- one namespace per environment
- an existing Secret named `liora-db-secrets` in each namespace

The chart does **not** store database passwords in `values.yaml`.

---

## Environment configuration

Three environment-specific values files are available:

```text
values-dev.yaml
values-staging.yaml
values-prod.yaml
```

| Environment | Namespace | Helm release | NodePort | WordPress Debug | PrestaShop Dev Mode |
|---|---|---|---:|---|---|
| Dev | `liora-dev` | `liora-dev` | `30080` | `true` | `true` |
| Staging | `liora-staging` | `liora-staging` | `30081` | `false` | `false` |
| Prod | `liora-prod` | `liora-prod` | `30082` | `false` | `false` |

Different NodePorts allow all three environments to run at the same time in the same Kubernetes cluster.

Later, CI/CD can deploy the same chart to different machines by selecting the correct values file and target host.

---

## Database Secret

Each environment requires its own namespace and its own `liora-db-secrets` Secret.

Example for Dev:

```bash
kubectl create namespace liora-dev
```

Create the Secret:

```bash
kubectl create secret generic liora-db-secrets \
  -n liora-dev \
  --from-literal=WORDPRESS_DB_NAME='wordpress' \
  --from-literal=WORDPRESS_DB_USER='wordpress' \
  --from-literal=WORDPRESS_DB_PASSWORD='<real-wordpress-password>' \
  --from-literal=WORDPRESS_DB_ROOT_PASSWORD='<real-wordpress-root-password>' \
  --from-literal=PRESTASHOP_DB_NAME='prestashop' \
  --from-literal=PRESTASHOP_DB_USER='prestashop' \
  --from-literal=PRESTASHOP_DB_PASSWORD='<real-prestashop-password>' \
  --from-literal=PRESTASHOP_DB_ROOT_PASSWORD='<real-prestashop-root-password>'
```

> **Important:** Replace every `<...>` placeholder with a real value before running the command. Do not use placeholder text literally.

You can generate passwords with:

```bash
openssl rand -hex 16
```

Do not commit passwords to Git.

For Staging and Prod, create the same Secret separately in:

```text
liora-staging
liora-prod
```

Secrets are namespace-scoped.

Verify only the Secret keys:

```bash
kubectl get secret liora-db-secrets \
  -n liora-dev \
  -o json \
  | jq -r '.data | keys[]'
```

---

## Public IP

For the current NodePort setup, PrestaShop needs the public host.

Get the current public IP:

```bash
PUBLIC_IP=$(curl -s https://checkip.amazonaws.com)
echo "$PUBLIC_IP"
```

The public IP is supplied at deployment time and is not committed to Git.

---

## Validate the chart

Lint Dev:

```bash
helm lint \
  ./helm/liora \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost="$PUBLIC_IP"
```

Render Dev:

```bash
helm template liora-dev \
  ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost="$PUBLIC_IP"
```

Dry run:

```bash
helm upgrade --install liora-dev \
  ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost="$PUBLIC_IP" \
  --set networkPolicy.enabled=true \
  --dry-run
```

Validate all environments:

```bash
for ENV in dev staging prod; do
  echo "===== $ENV ====="

  helm lint \
    ./helm/liora \
    -f "helm/liora/values-${ENV}.yaml" \
    --set prestashop.publicHost="${ENV}.example.test"
done
```

---

## Install

Refresh the public IP first:

```bash
PUBLIC_IP=$(curl -s https://checkip.amazonaws.com)
```

### Dev

```bash
helm upgrade --install liora-dev \
  ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost="$PUBLIC_IP" \
  --set networkPolicy.enabled=true
```

### Staging

```bash
helm upgrade --install liora-staging \
  ./helm/liora \
  --namespace liora-staging \
  -f helm/liora/values-staging.yaml \
  --set prestashop.publicHost="$PUBLIC_IP" \
  --set networkPolicy.enabled=true
```

### Prod

```bash
helm upgrade --install liora-prod \
  ./helm/liora \
  --namespace liora-prod \
  -f helm/liora/values-prod.yaml \
  --set prestashop.publicHost="$PUBLIC_IP" \
  --set networkPolicy.enabled=true
```

When all environments run on the same Kubernetes cluster:

```text
Dev:     http://<public-ip>:30080
Staging: http://<public-ip>:30081
Prod:    http://<public-ip>:30082
```

---

## Check deployment status

Helm:

```bash
helm status liora-dev -n liora-dev
helm list -n liora-dev
helm history liora-dev -n liora-dev
```

Kubernetes:

```bash
kubectl get \
  pods,deployments,statefulsets,services,pvc,networkpolicies \
  -n liora-dev
```

Expected healthy workload state:

```text
nginx-deployment   1/1 Running
prestashop-app     1/1 Running
prestashop-db-0    1/1 Running
wordpress-app      1/1 Running
wordpress-db-0     1/1 Running
```

Both database PVCs should be `Bound`.

---

## Verify Helm values

```bash
helm get values liora-dev -n liora-dev
```

Example Dev values:

```yaml
environment: dev

networkPolicy:
  enabled: true

nginx:
  service:
    nodePort: 30080
    type: NodePort

prestashop:
  devMode: true
  publicHost: <public-ip>

wordpress:
  debug: true
```

Environment-specific NodePorts:

```text
Dev     -> 30080
Staging -> 30081
Prod    -> 30082
```

The same `nginx.service.nodePort` value is reused by:

- the Kubernetes NodePort Service
- Nginx `X-Forwarded-Port`
- the PrestaShop ConfigMap
- PrestaShop `PS_DOMAIN`

This keeps the public port configuration in one place.

---

## Verify PrestaShop public configuration

Example for Dev:

```bash
kubectl exec \
  -n liora-dev \
  deployment/prestashop-app \
  -- printenv PUBLIC_HOST NGINX_NODE_PORT PS_DOMAIN
```

Expected format:

```text
<public-ip>
30080
<public-ip>:30080
```

For Staging and Prod, the NodePorts should be `30081` and `30082`.

---

## Test public routes

Set the NodePort according to the environment:

```bash
PUBLIC_IP=$(curl -s https://checkip.amazonaws.com)

# Dev
NODE_PORT=30080

# Staging
# NODE_PORT=30081

# Prod
# NODE_PORT=30082

BASE_URL="http://${PUBLIC_IP}:${NODE_PORT}"
```

Nginx health:

```bash
curl -i "$BASE_URL/health"
```

Expected:

```text
HTTP/1.1 200 OK
```

PrestaShop:

```bash
curl -IL --max-redirs 10 "$BASE_URL/"
```

WordPress:

```bash
curl -IL --max-redirs 10 "$BASE_URL/wordpress/"
```

On a fresh WordPress installation, a redirect to:

```text
/wordpress/wp-admin/install.php
```

is expected.

PrestaShop alias:

```bash
curl -I "$BASE_URL/prestashop"
curl -IL --max-redirs 10 "$BASE_URL/prestashop/"
```

`/prestashop` should redirect to `/prestashop/`.

---

## NetworkPolicies

NetworkPolicies are controlled by:

```yaml
networkPolicy:
  enabled: true
```

Expected policies:

```text
default-deny-ingress
allow-nginx-ingress
allow-nginx-to-wordpress
allow-nginx-to-prestashop
allow-wordpress-to-wordpress-db
allow-prestashop-to-prestashop-db
```

Enable them:

```bash
helm upgrade liora-dev \
  ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost="$PUBLIC_IP" \
  --set networkPolicy.enabled=true
```

Disable them temporarily for troubleshooting:

```bash
helm upgrade liora-dev \
  ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost="$PUBLIC_IP" \
  --set networkPolicy.enabled=false
```

---

## Startup dependencies

Applications wait for their databases:

```text
WordPress  -> wordpress-db-service-headless:3306
PrestaShop -> prestashop-db-service-headless:3306
```

Nginx waits for both applications over HTTP before starting.

This prevents Nginx from becoming ready while one of the upstream applications is unavailable.

### PrestaShop startup

A fresh PrestaShop installation can take several minutes, especially when multiple environments run on the same machine.

The startup probe therefore allows enough time for automatic installation before Kubernetes restarts the container.

Current configuration:

```yaml
startupProbe:
  tcpSocket:
    port: http
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 72
```

This allows approximately 6 minutes for startup:

```text
72 × 5 seconds = 360 seconds
```

Readiness and liveness probes continue monitoring the application after startup.

---

## Persistent storage

Each MySQL StatefulSet requests:

```text
1Gi
ReadWriteOnce
```

Check PVCs:

```bash
kubectl get pvc -n liora-dev
```

Each environment has its own StatefulSets and PVCs because they run in separate namespaces.

---

## Multi-environment deployment

The chart supports Dev, Staging and Prod simultaneously:

```text
Kubernetes Cluster
│
├── liora-dev
│   └── nginx NodePort 30080
│
├── liora-staging
│   └── nginx NodePort 30081
│
└── liora-prod
    └── nginx NodePort 30082
```

Each environment has:

- its own namespace
- its own Helm release
- its own database Secret
- its own MySQL StatefulSets and PVCs
- its own NodePort

Later, CI/CD can deploy the same chart to separate machines over SSH by selecting the appropriate values file and target server.

---

## Troubleshooting

Check Pods:

```bash
kubectl get pods -n liora-dev
```

Describe a Pod:

```bash
kubectl describe pod -n liora-dev <pod-name>
```

PrestaShop logs:

```bash
kubectl logs \
  -n liora-dev \
  deployment/prestashop-app \
  -c prestashop-app
```

Previous PrestaShop container logs:

```bash
kubectl logs \
  -n liora-dev \
  deployment/prestashop-app \
  -c prestashop-app \
  --previous
```

Nginx initContainer logs:

```bash
NGINX_POD=$(kubectl get pod \
  -n liora-dev \
  -l app=nginx-deployment \
  -o jsonpath='{.items[0].metadata.name}')

kubectl logs \
  -n liora-dev \
  "$NGINX_POD" \
  -c wait-for-applications
```

Recent events:

```bash
kubectl get events \
  -n liora-dev \
  --sort-by=.lastTimestamp
```

Check rollout:

```bash
kubectl rollout status deployment/prestashop-app \
  -n liora-dev \
  --timeout=6m

kubectl rollout status deployment/nginx-deployment \
  -n liora-dev \
  --timeout=6m
```

### ImagePullBackOff

Check which image Kubernetes is trying to pull:

```bash
kubectl get deployment prestashop-app \
  -n liora-dev \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

The current application images use the `base` tag.

---

## Uninstall

Remove a Helm release:

```bash
helm uninstall liora-dev -n liora-dev
```

For a complete clean Dev reset:

```bash
kubectl delete namespace liora-dev
```

For Staging:

```bash
helm uninstall liora-staging -n liora-staging
kubectl delete namespace liora-staging
```

For Prod:

```bash
helm uninstall liora-prod -n liora-prod
kubectl delete namespace liora-prod
```

Deleting a namespace also removes namespaced Secrets and PVCs, so use a namespace deletion only when a full reset is intended.
