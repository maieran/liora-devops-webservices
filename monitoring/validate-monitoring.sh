#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="monitoring"

echo "========================================"
echo " Liora Monitoring Validation"
echo "========================================"

echo
echo "[1/6] Checking monitoring namespace..."

kubectl get namespace "$NAMESPACE" >/dev/null

echo "OK"

echo
echo "[2/6] Checking monitoring Pods..."

NOT_READY=$(kubectl get pods -n "$NAMESPACE" \
  --no-headers \
  | awk '{
      split($2, ready, "/")
      if (ready[1] != ready[2] || $3 != "Running") print
    }')

if [[ -n "$NOT_READY" ]]; then
  echo "ERROR: Some monitoring Pods are not ready:"
  echo "$NOT_READY"
  exit 1
fi

echo "All monitoring Pods are Running."

echo
echo "[3/6] Checking Helm releases..."

helm status monitoring \
  -n "$NAMESPACE" >/dev/null

helm status monitoring-blackbox \
  -n "$NAMESPACE" >/dev/null

echo "Both Helm releases are deployed."

echo
echo "[4/6] Checking Grafana dashboard ConfigMap..."

kubectl get configmap \
  liora-overview-dashboard \
  -n "$NAMESPACE" >/dev/null

DASHBOARD_LABEL=$(kubectl get configmap \
  liora-overview-dashboard \
  -n "$NAMESPACE" \
  -o jsonpath='{.metadata.labels.grafana_dashboard}')

if [[ "$DASHBOARD_LABEL" != "1" ]]; then
  echo "ERROR: Grafana dashboard label is missing."
  exit 1
fi

echo "Grafana dashboard ConfigMap is valid."

echo
echo "[5/6] Checking Prometheus alert rules..."

RULE_COUNT=$(kubectl get prometheusrule \
  liora-alerts \
  -n "$NAMESPACE" \
  -o json \
  | jq '[.spec.groups[].rules[]] | length')

if [[ "$RULE_COUNT" -ne 5 ]]; then
  echo "ERROR: Expected 5 Liora alert rules, found $RULE_COUNT."
  exit 1
fi

echo "Found $RULE_COUNT Liora alert rules."

echo
echo "[6/6] Checking Blackbox ServiceMonitor..."

BLACKBOX_MONITORS=$(kubectl get servicemonitor \
  -n "$NAMESPACE" \
  -o name \
  | grep 'monitoring-blackbox' || true)

if [[ -z "$BLACKBOX_MONITORS" ]]; then
  echo "ERROR: No Blackbox ServiceMonitor found."
  exit 1
fi

echo "Blackbox ServiceMonitor exists."

echo
echo "========================================"
echo " Monitoring validation PASSED"
echo "========================================"