# Liora Monitoring

Monitoring and observability setup for the Liora Kubernetes environments.

This setup provides:

- Prometheus
- Grafana
- kube-state-metrics
- node-exporter
- Prometheus Blackbox Exporter
- Custom Grafana dashboard
- Custom Prometheus alert rules

The monitoring configuration is stored in Git so it can later be deployed reproducibly on the final Proxmox/Kubernetes environment.

---

## Directory Structure

```text
monitoring/
├── README.md
├── values.yaml
├── blackbox-values.yaml
├── blackbox-values-liora.yaml
├── dashboards/
│   └── liora-overview.json
└── rules/
    └── liora-alerts.yaml
```

---

## Helm Chart Versions

```text
kube-prometheus-stack:        88.5.3
prometheus-blackbox-exporter: 11.17.2
```

Add the Prometheus Community Helm repository:

```bash
helm repo add prometheus-community \
  https://prometheus-community.github.io/helm-charts

helm repo update
```

---

# 1. Install Prometheus and Grafana

Run from the repository root:

```bash
helm upgrade --install monitoring \
  prometheus-community/kube-prometheus-stack \
  --version 88.5.3 \
  --namespace monitoring \
  --create-namespace \
  -f monitoring/values.yaml
```

Check the monitoring Pods:

```bash
kubectl get pods -n monitoring
```

Expected components include:

```text
Grafana
Prometheus
Prometheus Operator
kube-state-metrics
node-exporter
```

The current `values.yaml` is intentionally lightweight for the development environment.

Important settings:

- Prometheus retention: 1 day
- Prometheus retention size: 1 GB
- Grafana persistence: disabled
- Alertmanager: disabled
- K3s-incompatible control-plane monitors: disabled

---

# 2. Install Blackbox Exporter

Blackbox Exporter is used to perform HTTP availability checks.

Two separate values files exist.

## Development / Lab Configuration

`monitoring/blackbox-values.yaml`

This configuration contains a temporary Grafana health endpoint used to prove the monitoring flow:

```text
Blackbox Exporter
      ↓
Prometheus
      ↓
Grafana
```

Install it with:

```bash
helm upgrade --install monitoring-blackbox \
  prometheus-community/prometheus-blackbox-exporter \
  --version 11.17.2 \
  --namespace monitoring \
  -f monitoring/blackbox-values.yaml
```

This configuration is mainly intended for the EC2 development environment.

## Liora Environment Configuration

`monitoring/blackbox-values-liora.yaml`

This configuration contains the real application probes for:

```text
liora-dev
liora-staging
liora-prod
```

For every environment, Blackbox checks the public application routes through NGINX:

```text
NGINX       /health
PrestaShop  /
WordPress   /wordpress/
```

Example:

```text
http://nginx-service.liora-dev.svc.cluster.local/health
http://nginx-service.liora-dev.svc.cluster.local/
http://nginx-service.liora-dev.svc.cluster.local/wordpress/
```

The same pattern is used for staging and production.

Install it only on a cluster where the Liora namespaces already exist:

```bash
helm upgrade --install monitoring-blackbox \
  prometheus-community/prometheus-blackbox-exporter \
  --version 11.17.2 \
  --namespace monitoring \
  -f monitoring/blackbox-values-liora.yaml
```

Do not use this file on the EC2 lab while the Liora application namespaces are absent, otherwise all real Liora probes will intentionally fail.

---

# 3. Blackbox Labels

Each Liora probe receives labels that make dashboard filtering and alerting possible.

Example:

```text
environment="dev"
liora_namespace="liora-dev"
application="nginx"
```

Applications:

```text
nginx
wordpress
prestashop
```

Environments:

```text
dev
staging
prod
```

Example Prometheus query:

```promql
probe_success{
  liora_namespace="liora-dev",
  application="nginx"
}
```

---

# 4. Deploy the Grafana Dashboard

The dashboard is stored in Git:

```text
monitoring/dashboards/liora-overview.json
```

The JSON file is the source of truth.

Create or update the ConfigMap:

```bash
kubectl create configmap liora-overview-dashboard \
  -n monitoring \
  --from-file=liora-overview.json=monitoring/dashboards/liora-overview.json \
  --dry-run=client \
  -o yaml \
| kubectl apply -f -
```

Add the Grafana dashboard discovery label:

```bash
kubectl label configmap \
  liora-overview-dashboard \
  -n monitoring \
  grafana_dashboard=1 \
  --overwrite
```

Verify:

```bash
kubectl get configmap \
  liora-overview-dashboard \
  -n monitoring \
  --show-labels
```

Expected label:

```text
grafana_dashboard=1
```

Grafana automatically reloads the dashboard through its dashboard sidecar.

## Verify Dashboard Reload

Find the Grafana Pod:

```bash
GRAFANA_POD=$(kubectl get pod \
  -n monitoring \
  -l app.kubernetes.io/name=grafana \
  -o jsonpath='{.items[0].metadata.name}')
```

Check the sidecar logs:

```bash
kubectl logs \
  -n monitoring \
  "$GRAFANA_POD" \
  -c grafana-sc-dashboard \
  --tail=20
```

Expected output includes:

```text
Writing /tmp/dashboards/liora-overview.json
Dashboards config reloaded
200 OK
```

---

# 5. Liora Overview Dashboard

The `Liora Overview` dashboard contains 11 panels.

```text
1. Ready Pods
2. Total Pods
3. Restarts - last 15m
4. Available Deployment Replicas
5. Ready StatefulSet Replicas
6. Bound PVCs
7. CPU Usage by Pod
8. Memory Usage by Pod
9. WordPress Availability
10. NGINX Availability
11. PrestaShop Availability
```

The dashboard uses the `$namespace` variable.

Example namespaces:

```text
liora-dev
liora-staging
liora-prod
```

When the user changes the namespace, Kubernetes metrics and application availability panels follow the selected environment.

## Application Availability States

The three Blackbox availability panels use:

```text
UP     HTTP probe succeeded
DOWN   HTTP probe failed
N/A    No matching Liora probe exists
```

Example NGINX query:

```promql
probe_success{
  liora_namespace="$namespace",
  application="nginx"
} or on() vector(-1)
```

Example WordPress query:

```promql
probe_success{
  liora_namespace="$namespace",
  application="wordpress"
} or on() vector(-1)
```

Example PrestaShop query:

```promql
probe_success{
  liora_namespace="$namespace",
  application="prestashop"
} or on() vector(-1)
```

Mappings:

```text
-1 → N/A
 0 → DOWN
 1 → UP
```

---

# 6. Grafana Access

Forward Grafana locally:

```bash
kubectl port-forward \
  -n monitoring \
  svc/monitoring-grafana \
  3000:80
```

Open:

```text
http://localhost:3000
```

Default username:

```text
admin
```

Retrieve the generated admin password:

```bash
kubectl get secret monitoring-grafana \
  -n monitoring \
  -o jsonpath='{.data.admin-password}' \
| base64 -d

echo
```

Do not store the generated password in Git.

Rotate it before using the monitoring stack in a persistent production environment.

---

# 7. Deploy Custom Prometheus Alerts

The custom alert rules are stored in:

```text
monitoring/rules/liora-alerts.yaml
```

Deploy them:

```bash
kubectl apply \
  -f monitoring/rules/liora-alerts.yaml
```

Verify:

```bash
kubectl get prometheusrule \
  -n monitoring \
  liora-alerts
```

List all custom alerts:

```bash
kubectl get prometheusrule \
  -n monitoring \
  liora-alerts \
  -o json \
| jq -r '.spec.groups[].rules[].alert'
```

Expected:

```text
LioraEndpointDown
LioraPodRestarting
LioraDeploymentUnavailable
LioraPVCNotBound
NodeHighMemory
```

---

# 8. Custom Alert Rules

## LioraEndpointDown

Triggers when a monitored Liora HTTP endpoint fails continuously for more than 2 minutes.

Covers:

```text
NGINX
WordPress
PrestaShop
```

Severity:

```text
critical
```

## LioraPodRestarting

Triggers when a Liora Pod restarts more than twice during a 15-minute period and the condition persists.

Severity:

```text
warning
```

## LioraDeploymentUnavailable

Triggers when a Liora Deployment has unavailable replicas for more than 5 minutes.

Severity:

```text
critical
```

## LioraPVCNotBound

Triggers when a Liora PVC remains in `Pending` or `Lost` state for more than 5 minutes.

Severity:

```text
critical
```

## NodeHighMemory

Triggers when node memory usage remains above 90% for at least 10 minutes.

Severity:

```text
warning
```

---

# 9. Verify Prometheus Loaded the Rules

Forward Prometheus:

```bash
kubectl port-forward \
  -n monitoring \
  svc/monitoring-kube-prometheus-prometheus \
  9090:9090
```

In another terminal:

```bash
curl -s http://localhost:9090/api/v1/rules \
| jq -r '
  .data.groups[]
  | select(.name | startswith("liora."))
  | .rules[]
  | [.name, .state, .health]
  | @tsv
'
```

Expected when no alert condition is active:

```text
LioraEndpointDown            inactive    ok
LioraPodRestarting           inactive    ok
LioraDeploymentUnavailable   inactive    ok
LioraPVCNotBound             inactive    ok
NodeHighMemory               inactive    ok
```

`inactive` means the alert condition is currently false.

`ok` means Prometheus successfully loaded and evaluated the rule.

---

# 10. Alertmanager

Alertmanager is currently disabled in:

```text
monitoring/values.yaml
```

This means:

```text
Prometheus evaluates alert rules      YES
Alerts can become pending/firing      YES
Notifications are sent               NO
```

Alertmanager can be enabled later on the final Proxmox infrastructure and connected to a notification destination such as email or Slack.

It is intentionally disabled in the small EC2 development environment to reduce resource usage.

---

# 11. Quick Verification

Check Pods:

```bash
kubectl get pods -n monitoring
```

Check Services:

```bash
kubectl get svc -n monitoring
```

Check ServiceMonitors:

```bash
kubectl get servicemonitor -n monitoring
```

Check PrometheusRules:

```bash
kubectl get prometheusrule -n monitoring
```

Check the custom rule:

```bash
kubectl get prometheusrule \
  -n monitoring \
  liora-alerts
```

---

# 12. Useful Prometheus Queries

Check all Blackbox probes:

```promql
probe_success
```

Check one Liora environment:

```promql
probe_success{
  liora_namespace="liora-dev"
}
```

Check NGINX:

```promql
probe_success{
  application="nginx"
}
```

Check WordPress:

```promql
probe_success{
  application="wordpress"
}
```

Check PrestaShop:

```promql
probe_success{
  application="prestashop"
}
```

Check container restarts during the last 15 minutes:

```promql
sum(
  increase(
    kube_pod_container_status_restarts_total[15m]
  )
)
```

Check available node memory:

```promql
node_memory_MemAvailable_bytes
```

Check Ready Pods:

```promql
sum(
  kube_pod_status_ready{
    condition="true"
  }
)
```

---

# 13. Validate the Blackbox Helm Configuration

The real Liora Blackbox values file can be validated without installing it.

Pull the pinned chart:

```bash
BLACKBOX_VERSION=11.17.2

rm -rf /tmp/prometheus-blackbox-exporter

helm pull prometheus-community/prometheus-blackbox-exporter \
  --version "$BLACKBOX_VERSION" \
  --untar \
  --untardir /tmp
```

Lint:

```bash
helm lint \
  /tmp/prometheus-blackbox-exporter \
  -f monitoring/blackbox-values-liora.yaml
```

Render:

```bash
helm template monitoring-blackbox \
  /tmp/prometheus-blackbox-exporter \
  --namespace monitoring \
  -f monitoring/blackbox-values-liora.yaml \
  > /tmp/blackbox-liora-rendered.yaml
```

Count the rendered ServiceMonitors:

```bash
grep '^kind: ServiceMonitor$' \
  /tmp/blackbox-liora-rendered.yaml \
| wc -l
```

Expected:

```text
9
```

This represents:

```text
3 applications × 3 environments = 9 probes
```

---

# 14. Deployment Notes

The current EC2 Kubernetes environment is used only as a development and validation environment.

The final project infrastructure is intended to run on Proxmox.

The monitoring configuration should therefore remain portable and reproducible from Git.

Expected future deployment flow:

```text
Git repository
      ↓
CI/CD pipeline
      ↓
Kubernetes / Proxmox
      ↓
Prometheus + Grafana
      ↓
Blackbox Exporter
      ↓
Liora Dev / Staging / Prod
```

The monitoring stack should be deployed once in the `monitoring` namespace and can observe the Liora application namespaces from there.

---

# 15. Current Status

Implemented:

```text
Prometheus                     DONE
Grafana                        DONE
kube-state-metrics             DONE
node-exporter                  DONE
Blackbox Exporter              DONE
Lab HTTP probe                 DONE
Dev/Staging/Prod probe config  DONE
Liora Overview dashboard       DONE
Prometheus alert rules         DONE
Monitoring documentation       DONE
```

Still optional / future work:

```text
Alertmanager notifications
Persistent Prometheus storage
Persistent Grafana storage
Production credential rotation
Additional security hardening
Backup / restore monitoring
```
