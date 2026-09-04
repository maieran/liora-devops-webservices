#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${1:-liora-prod}"

JOB_NAME="liora-db-backup-manual-$(date +%s)"

echo "========================================"
echo " Liora Database Backup"
echo "========================================"
echo "Namespace: $NAMESPACE"
echo "Job:       $JOB_NAME"
echo

echo "[1/3] Creating backup Job..."

kubectl create job \
  --namespace "$NAMESPACE" \
  --from=cronjob/liora-db-backup \
  "$JOB_NAME"

echo
echo "[2/3] Waiting for backup Job to complete..."

if ! kubectl wait \
  --namespace "$NAMESPACE" \
  --for=condition=complete \
  "job/$JOB_NAME" \
  --timeout=10m
then
  echo
  echo "ERROR: Backup Job did not complete successfully."
  echo

  kubectl get pods \
    --namespace "$NAMESPACE" \
    -l job-name="$JOB_NAME"

  echo
  echo "Job logs:"
  kubectl logs \
    --namespace "$NAMESPACE" \
    "job/$JOB_NAME" \
    --all-containers=true || true

  exit 1
fi

echo
echo "[3/3] Backup logs:"
echo

kubectl logs \
  --namespace "$NAMESPACE" \
  "job/$JOB_NAME"

echo
echo "========================================"
echo " Backup completed successfully"
echo "========================================"

