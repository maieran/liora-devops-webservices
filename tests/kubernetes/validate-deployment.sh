#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-}"
BASE_URL="${2:-}"

if [[ -z "$NAMESPACE" || -z "$BASE_URL" ]]; then
    echo "Usage: $0 <namespace> <base-url>"
    echo "Example: $0 liora-dev http://10.10.10.11:30080"
    exit 1
fi

echo "======================================"
echo "Kubernetes deployment validation"
echo "Namespace: $NAMESPACE"
echo "Base URL:  $BASE_URL"
echo "======================================"

echo
echo "1. Checking Pods..."
NOT_READY=$(
    kubectl get pods -n "$NAMESPACE" --no-headers |
    awk '{
        # Ignore old completed pods from previous ReplicaSets.
        if ($3 == "Completed") {
            next
        }

        split($2, ready, "/")

        if (ready[1] != ready[2] || $3 != "Running") {
            print
        }
    }'
)

if [[ -n "$NOT_READY" ]]; then
    echo "ERROR: Pods are not Ready/Running:"
    echo "$NOT_READY"
    exit 1
fi

echo "All active Pods are Ready and Running."

echo
echo "2. Checking Deployment rollouts..."
for DEPLOYMENT in nginx-deployment wordpress-app prestashop-app; do
    kubectl rollout status \
        deployment/"$DEPLOYMENT" \
        -n "$NAMESPACE" \
        --timeout=6m
done

echo
echo "3. Checking StatefulSet rollouts..."
for STATEFULSET in wordpress-db prestashop-db; do
    kubectl rollout status \
        statefulset/"$STATEFULSET" \
        -n "$NAMESPACE" \
        --timeout=6m
done

echo
echo "4. Checking PVCs..."
NOT_BOUND=$(
    kubectl get pvc -n "$NAMESPACE" --no-headers |
    awk '$2 != "Bound" {print}'
)

if [[ -n "$NOT_BOUND" ]]; then
    echo "ERROR: PVCs are not Bound:"
    echo "$NOT_BOUND"
    exit 1
fi

echo "All PVCs are Bound."

echo
echo "5. Checking Service endpoints..."
for SERVICE in \
    nginx-service \
    wordpress-app-service \
    prestashop-app-service \
    wordpress-db-service-headless \
    prestashop-db-service-headless
do
    ENDPOINTS=$(
        kubectl get endpoints "$SERVICE" \
            -n "$NAMESPACE" \
            -o jsonpath='{.subsets[*].addresses[*].ip}' \
            2>/dev/null || true
    )

    if [[ -z "$ENDPOINTS" ]]; then
        echo "ERROR: Service has no endpoints: $SERVICE"
        exit 1
    fi

    echo "$SERVICE -> OK"
done

echo
echo "6. Checking recent probe failures..."
FAILED_PROBES=$(
    kubectl get events \
        -n "$NAMESPACE" \
        --field-selector type=Warning \
        --sort-by=.lastTimestamp |
    grep -Ei \
        'startup probe failed|readiness probe failed|liveness probe failed' |
    tail -20 || true
)

if [[ -n "$FAILED_PROBES" ]]; then
    echo "WARNING: Recent probe failures detected:"
    echo "$FAILED_PROBES"
else
    echo "No recent probe failures detected."
fi

echo
echo "7. Running Nginx smoke tests..."

echo "Testing /health ..."
curl -fsS "$BASE_URL/health" > /dev/null
echo "/health -> OK"

echo "Testing / ..."
curl -fsSL \
  --connect-timeout 5 \
  --max-time 30 \
  --max-redirs 10 \
  "$BASE_URL/" > /dev/null
echo "/ -> OK"

echo "Testing /wordpress/ ..."
curl -fsSL \
  --connect-timeout 5 \
  --max-time 30 \
  --max-redirs 10 \
  "$BASE_URL/wordpress/" > /dev/null
echo "/wordpress/ -> OK"

echo
echo "======================================"
echo "Kubernetes deployment validation PASSED"
echo "======================================"