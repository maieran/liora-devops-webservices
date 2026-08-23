# Liora Monitoring

Monitoring and observability setup for the Liora Kubernetes environments.

The monitoring configuration is stored in Git and is designed to be reproducible on the final Proxmox/Kubernetes environment.

## What is included

- Prometheus
- Grafana
- kube-state-metrics
- node-exporter
- Prometheus Blackbox Exporter
- Liora Grafana dashboard
- Custom Prometheus alert rules
- Reproducible deployment script

---

## Directory structure

```text
monitoring/
├── README.md
├── deploy-monitoring.sh
├── values.yaml
├── blackbox-values.yaml
├── blackbox-values-liora.yaml
├── dashboards/
│   └── liora-overview.json
└── rules/
    └── liora-alerts.yaml
```

---

# 1. Prerequisites

The machine or CI runner executing the monitoring deployment needs:

```text
kubectl
helm
jq          # only required for some verification commands
```

It also needs a working Kubernetes context:

```bash
kubectl cluster-info
kubectl get nodes
```

The deployment script manages the Prometheus Community Helm repository automatically.

Pinned Helm chart versions:

```text
kube-prometheus-stack:        88.5.3
prometheus-blackbox-exporter: 11.17.2
```

---

# 2. Recommended deployment method

Use:

```text
monitoring/deploy-monitoring.sh
```

Do not manually recreate the monitoring stack unless troubleshooting.

The script is idempotent and uses:

```text
helm upgrade --install
kubectl apply
```

so it can be run again to reconcile an existing installation.

Make sure the script is executable:

```bash
chmod +x monitoring/deploy-monitoring.sh
```

Syntax check:

```bash
bash -n monitoring/deploy-monitoring.sh
```

---

# 3. Deployment modes

The script supports two modes.

## Lab mode

Use this on a development cluster where the Liora application namespaces are not deployed.

```bash
./monitoring/deploy-monitoring.sh lab
```

Lab mode uses:

```text
monitoring/blackbox-values.yaml
```

It probes the Grafana health endpoint to verify:

```text
Blackbox Exporter
       ↓
Prometheus
       ↓
Grafana
```

This mode was used to validate the monitoring setup on the EC2 development cluster.

---

## Liora mode

Use this on the Kubernetes cluster where the real Liora environments are deployed.

```bash
./monitoring/deploy-monitoring.sh liora
```

Liora mode uses:

```text
monitoring/blackbox-values-liora.yaml
```

It expects these namespaces to exist:

```text
liora-dev
liora-staging
liora-prod
```

It also expects the NGINX Service to be named:

```text
nginx-service
```

in each Liora namespace.

Blackbox probes these routes through NGINX:

```text
NGINX       /health
PrestaShop  /
WordPress   /wordpress/
```

Examples:

```text
http://nginx-service.liora-dev.svc.cluster.local/health
http://nginx-service.liora-dev.svc.cluster.local/
http://nginx-service.liora-dev.svc.cluster.local/wordpress/
```

The same pattern is used for staging and production.

> Important: deploy the Liora application namespaces before running `liora` mode. If the namespaces or `nginx-service` do not exist yet, the application probes will fail.

---

# 4. CI/CD deployment order

For Jenkins or another CI/CD system, the intended order is:

```text
1. Kubernetes infrastructure is available
2. kubectl context is configured
3. Liora Dev / Staging / Prod are deployed
4. Run monitoring deployment in liora mode
5. Verify monitoring resources
```

Monitoring command:

```bash
./monitoring/deploy-monitoring.sh liora
```

The monitoring script does not provision Proxmox infrastructure and does not deploy the Liora application itself.

It only deploys/reconciles the monitoring stack.

---

# 5. What the deployment script does

`deploy-monitoring.sh` performs the following steps:

```text
1. Adds/updates the Prometheus Community Helm repository
2. Installs/upgrades Prometheus and Grafana
3. Installs/upgrades Blackbox Exporter
4. Applies the custom Prometheus alert rules
5. Creates/updates the Grafana dashboard ConfigMap
6. Labels the dashboard ConfigMap for Grafana discovery
7. Prints monitoring deployment status
```

Monitoring namespace:

```text
monitoring
```

Helm releases:

```text
monitoring
monitoring-blackbox
```

---

# 6. Main Prometheus/Grafana configuration

Main values file:

```text
monitoring/values.yaml
```

The current setup is intentionally lightweight.

Important settings:

```text
Prometheus retention:       1 day
Prometheus retention size:  1 GB
Grafana persistence:        disabled
Prometheus persistence:     disabled
Alertmanager:               disabled
```

K3s-specific control-plane monitors that are not exposed in the same way as a standard Kubernetes installation are disabled.

For the final production environment, persistence and retention can be increased if enough storage and memory are available.

---

# 7. Blackbox labels

The real Liora probes receive labels used by Grafana and Prometheus alerts.

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

Example query:

```promql
probe_success{
  liora_namespace="liora-dev",
  application="nginx"
}
```

The Liora configuration renders:

```text
3 applications × 3 environments = 9 ServiceMonitors
```

---

# 8. Grafana dashboard

Dashboard source of truth:

```text
monitoring/dashboards/liora-overview.json
```

The deployment script creates/updates:

```text
ConfigMap: liora-overview-dashboard
Namespace: monitoring
Label:     grafana_dashboard=1
```

Grafana's dashboard sidecar discovers the ConfigMap and loads the dashboard automatically.

## Important

The provisioned `Liora Overview` dashboard is intentionally read-only in the Grafana UI.

Do not treat manual UI changes to the provisioned dashboard as the source of truth.

Permanent changes should be made to:

```text
monitoring/dashboards/liora-overview.json
```

and redeployed.

---

## Dashboard panels

The dashboard contains 11 panels:

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

Expected Liora values:

```text
liora-dev
liora-staging
liora-prod
```

---

## Availability states

The application panels use:

```text
UP     HTTP probe succeeded
DOWN   HTTP probe failed
N/A    No matching Liora probe exists for the selected namespace
```

Example query:

```promql
probe_success{
  liora_namespace="$namespace",
  application="nginx"
} or on() vector(-1)
```

Mappings:

```text
-1 → N/A
 0 → DOWN
 1 → UP
```

Seeing `N/A` in lab mode is expected because the real Liora probes are not installed there.

---

# 9. Grafana access

Port-forward Grafana:

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

Do not commit or paste the generated password into Git or CI logs.

Rotate credentials before using the stack as a persistent production environment.

---

# 10. Prometheus alert rules

Alert rules:

```text
monitoring/rules/liora-alerts.yaml
```

They are automatically applied by `deploy-monitoring.sh`.

Custom alerts:

```text
LioraEndpointDown
LioraPodRestarting
LioraDeploymentUnavailable
LioraPVCNotBound
NodeHighMemory
```

## LioraEndpointDown

Triggers when a monitored Liora HTTP endpoint fails for more than 2 minutes.

Severity:

```text
critical
```

## LioraPodRestarting

Triggers when a Liora Pod restarts more than twice during a 15-minute window and the condition persists.

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

# 11. Alertmanager

Alertmanager is currently disabled.

Therefore:

```text
Prometheus evaluates alert rules      YES
Alerts can become pending/firing      YES
Notifications are sent               NO
```

The rules can still be inspected in Prometheus and Grafana.

Alertmanager can be enabled later on the final Proxmox infrastructure when a notification destination such as email or Slack has been selected.

---

# 12. Quick validation after deployment

Check monitoring Pods:

```bash
kubectl get pods -n monitoring
```

All Pods should be `Running` and their containers should be ready.

Check Helm releases:

```bash
helm list -n monitoring
```

Expected releases:

```text
monitoring
monitoring-blackbox
```

Check Helm history:

```bash
helm history monitoring -n monitoring
helm history monitoring-blackbox -n monitoring
```

> `helm history monitoring` without `-n monitoring` can report `release: not found`.

Check Services:

```bash
kubectl get svc -n monitoring
```

Check ServiceMonitors:

```bash
kubectl get servicemonitor -n monitoring
```

Lab mode should contain the Grafana health ServiceMonitor.

Liora mode should contain the nine Liora application ServiceMonitors.

Check custom PrometheusRule:

```bash
kubectl get prometheusrule \
  -n monitoring \
  liora-alerts
```

List custom alert names:

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

# 13. Verify Prometheus loaded the rules

Port-forward Prometheus:

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

Healthy rules look like:

```text
LioraEndpointDown             inactive    ok
LioraPodRestarting            inactive    ok
LioraDeploymentUnavailable    inactive    ok
LioraPVCNotBound              inactive    ok
NodeHighMemory                inactive    ok
```

`inactive` means the alert condition is currently false.

`ok` means Prometheus loaded and can evaluate the rule.

---

# 14. Verify dashboard provisioning

Check the ConfigMap label:

```bash
kubectl get configmap \
  liora-overview-dashboard \
  -n monitoring \
  --show-labels
```

Expected:

```text
grafana_dashboard=1
```

When running the deployment script repeatedly, this command may print:

```text
configmap/liora-overview-dashboard not labeled
```

This is not an error if the ConfigMap already has:

```text
grafana_dashboard=1
```

To verify Grafana reloaded the dashboard:

```bash
GRAFANA_POD=$(kubectl get pod \
  -n monitoring \
  -l app.kubernetes.io/name=grafana \
  -o jsonpath='{.items[0].metadata.name}')
```

```bash
kubectl logs \
  -n monitoring \
  "$GRAFANA_POD" \
  -c grafana-sc-dashboard \
  --tail=20
```

Healthy output includes:

```text
Writing /tmp/dashboards/liora-overview.json
200 OK
Dashboards config reloaded
```

---

# 15. Useful Prometheus queries

All Blackbox probes:

```promql
probe_success
```

One Liora environment:

```promql
probe_success{
  liora_namespace="liora-dev"
}
```

NGINX:

```promql
probe_success{
  application="nginx"
}
```

WordPress:

```promql
probe_success{
  application="wordpress"
}
```

PrestaShop:

```promql
probe_success{
  application="prestashop"
}
```

Container restarts during the last 15 minutes:

```promql
sum(
  increase(
    kube_pod_container_status_restarts_total[15m]
  )
)
```

Available node memory:

```promql
node_memory_MemAvailable_bytes
```

Ready Pods:

```promql
sum(
  kube_pod_status_ready{
    condition="true"
  }
)
```

---

# 16. Validate the Liora Blackbox configuration without installing it

This is useful before changing the real probe configuration.

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

Count ServiceMonitors:

```bash
grep '^kind: ServiceMonitor$' \
  /tmp/blackbox-liora-rendered.yaml \
| wc -l
```

Expected:

```text
9
```

---

# 17. Troubleshooting

## `helm history monitoring` says `release: not found`

Use the monitoring namespace:

```bash
helm history monitoring -n monitoring
```

For Blackbox:

```bash
helm history monitoring-blackbox -n monitoring
```

---

## Grafana dashboard is read-only

Expected behavior.

The dashboard is provisioned from a Kubernetes ConfigMap.

Update the JSON in Git and redeploy instead of saving directly in the provisioned Grafana dashboard.

---

## Availability panels show `N/A`

Expected in lab mode.

In Liora mode, verify the namespaces exist:

```bash
kubectl get ns
```

Verify the NGINX Services:

```bash
kubectl get svc -n liora-dev
kubectl get svc -n liora-staging
kubectl get svc -n liora-prod
```

Each namespace must contain:

```text
nginx-service
```

---

## Availability panels show `DOWN`

Check the Blackbox ServiceMonitors:

```bash
kubectl get servicemonitor -n monitoring
```

Check Blackbox metrics:

```promql
probe_success
```

Check the expected NGINX route manually from inside the cluster if necessary.

---

## Custom alerts are missing

Verify:

```bash
kubectl get prometheusrule -n monitoring liora-alerts
```

The rule object must contain:

```text
release=monitoring
```

Check labels:

```bash
kubectl get prometheusrule \
  -n monitoring \
  liora-alerts \
  --show-labels
```

---

# 18. Production handoff notes

The EC2 cluster was used only for development and validation.

The final target is the Proxmox-hosted Kubernetes environment.

Before production use:

```text
1. Ensure sufficient RAM/storage for Prometheus and Grafana
2. Deploy Liora namespaces before monitoring in liora mode
3. Confirm the NGINX Service name is nginx-service
4. Run ./monitoring/deploy-monitoring.sh liora
5. Verify all monitoring Pods
6. Verify nine Liora Blackbox ServiceMonitors
7. Verify the Liora Overview dashboard
8. Verify the five custom alert rules
9. Rotate Grafana credentials
10. Decide whether Alertmanager notifications should be enabled
```

The current monitoring setup intentionally avoids hard-coding EC2-specific addresses or credentials, so it can be reused on Proxmox.

---

# Current status

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
Reproducible deployment script DONE
Monitoring documentation      DONE
```

Optional / future work:

```text
Alertmanager notifications
Persistent Prometheus storage
Persistent Grafana storage
Production credential rotation
Additional security hardening
Backup / restore for monitoring data
```
