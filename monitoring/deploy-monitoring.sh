#!/usr/bin/env bash

set -euo pipefail

MODE="${1:-lab}"

MONITORING_NAMESPACE="monitoring"

PROMETHEUS_VERSION="88.5.3"
BLACKBOX_VERSION="11.17.2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROMETHEUS_VALUES="${SCRIPT_DIR}/values.yaml"
DASHBOARD="${SCRIPT_DIR}/dashboards/liora-overview.json"
ALERT_RULES="${SCRIPT_DIR}/rules/liora-alerts.yaml"

case "$MODE" in
  lab)
    BLACKBOX_VALUES="${SCRIPT_DIR}/blackbox-values.yaml"
    ;;

  liora)
    BLACKBOX_VALUES="${SCRIPT_DIR}/blackbox-values-liora.yaml"
    ;;

  *)
    echo "Usage: $0 [lab|liora]"
    exit 1
    ;;
esac


echo "========================================"
echo " Liora Monitoring Deployment"
echo "========================================"
echo "Mode:      $MODE"
echo "Namespace: $MONITORING_NAMESPACE"
echo


echo "[1/6] Preparing Helm repository..."

helm repo add prometheus-community \
  https://prometheus-community.github.io/helm-charts \
  >/dev/null 2>&1 || true

helm repo update


echo
echo "[2/6] Installing Prometheus and Grafana..."

helm upgrade --install monitoring \
  prometheus-community/kube-prometheus-stack \
  --version "$PROMETHEUS_VERSION" \
  --namespace "$MONITORING_NAMESPACE" \
  --create-namespace \
  -f "$PROMETHEUS_VALUES" \
  --wait \
  --timeout 10m


echo
echo "[3/6] Installing Blackbox Exporter..."

helm upgrade --install monitoring-blackbox \
  prometheus-community/prometheus-blackbox-exporter \
  --version "$BLACKBOX_VERSION" \
  --namespace "$MONITORING_NAMESPACE" \
  -f "$BLACKBOX_VALUES" \
  --wait \
  --timeout 5m


echo
echo "[4/6] Applying Prometheus alert rules..."

kubectl apply \
  -f "$ALERT_RULES"


echo
echo "[5/6] Provisioning Grafana dashboard..."

kubectl create configmap liora-overview-dashboard \
  --namespace "$MONITORING_NAMESPACE" \
  --from-file=liora-overview.json="$DASHBOARD" \
  --dry-run=client \
  -o yaml \
| kubectl apply -f -

kubectl label configmap \
  liora-overview-dashboard \
  --namespace "$MONITORING_NAMESPACE" \
  grafana_dashboard=1 \
  --overwrite


echo
echo "[6/6] Deployment status..."

kubectl get pods \
  --namespace "$MONITORING_NAMESPACE"

echo
kubectl get servicemonitor \
  --namespace "$MONITORING_NAMESPACE"

echo
kubectl get prometheusrule \
  --namespace "$MONITORING_NAMESPACE" \
  liora-alerts


echo
echo "========================================"
echo " Monitoring deployment completed"
echo "========================================"

