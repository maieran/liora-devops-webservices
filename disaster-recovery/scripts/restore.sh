#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${1:-}"
DATABASE="${2:-}"
BACKUP="${3:-latest}"

if [[ -z "$NAMESPACE" || -z "$DATABASE" ]]; then
  echo "Usage:"
  echo "  $0 <namespace> <wordpress|prestashop> [backup-directory|latest]"
  echo
  echo "Examples:"
  echo "  $0 liora-prod wordpress"
  echo "  $0 liora-prod prestashop latest"
  echo "  $0 liora-prod wordpress 2026-09-02_20-15-00"
  exit 1
fi

case "$DATABASE" in
  wordpress)
    DB_POD="wordpress-db-0"
    BACKUP_FILE="wordpress.sql.gz"
    ;;

  prestashop)
    DB_POD="prestashop-db-0"
    BACKUP_FILE="prestashop.sql.gz"
    ;;

  *)
    echo "ERROR: Database must be 'wordpress' or 'prestashop'."
    exit 1
    ;;
esac

INSPECTOR_POD="liora-restore-reader-$(date +%s)"

cleanup() {
  kubectl delete pod \
    "$INSPECTOR_POD" \
    -n "$NAMESPACE" \
    --ignore-not-found \
    >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "========================================"
echo " Liora Database Restore"
echo "========================================"
echo "Namespace: $NAMESPACE"
echo "Database:  $DATABASE"
echo

echo "[1/5] Creating temporary backup reader..."

kubectl run "$INSPECTOR_POD" \
  -n "$NAMESPACE" \
  --image=mysql:8.0.42 \
  --restart=Never \
  --overrides='
{
  "spec": {
    "containers": [
      {
        "name": "backup-reader",
        "image": "mysql:8.0.42",
        "command": ["sh", "-c", "sleep 3600"],
        "volumeMounts": [
          {
            "name": "backup-storage",
            "mountPath": "/backups"
          }
        ]
      }
    ],
    "volumes": [
      {
        "name": "backup-storage",
        "persistentVolumeClaim": {
          "claimName": "liora-db-backups"
        }
      }
    ]
  }
}'

kubectl wait \
  -n "$NAMESPACE" \
  --for=condition=Ready \
  "pod/$INSPECTOR_POD" \
  --timeout=2m

echo
echo "[2/5] Selecting backup..."

if [[ "$BACKUP" == "latest" ]]; then
  BACKUP_DIR=$(kubectl exec \
    -n "$NAMESPACE" \
    "$INSPECTOR_POD" \
    -- sh -c \
    'find /backups -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1')
else
  BACKUP_DIR="/backups/$BACKUP"
fi

if [[ -z "$BACKUP_DIR" ]]; then
  echo "ERROR: No backup directory found."
  exit 1
fi

BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

echo "Backup: $BACKUP_PATH"

echo
echo "[3/5] Validating backup..."

kubectl exec \
  -n "$NAMESPACE" \
  "$INSPECTOR_POD" \
  -- test -f "$BACKUP_PATH"

kubectl exec \
  -n "$NAMESPACE" \
  "$INSPECTOR_POD" \
  -- gzip -t "$BACKUP_PATH"

echo "Backup file is valid."

echo
echo "WARNING:"
echo "This operation will overwrite the current $DATABASE database"
echo "with the selected backup."
echo

read -r -p "Type RESTORE to continue: " CONFIRM

if [[ "$CONFIRM" != "RESTORE" ]]; then
  echo "Restore cancelled."
  exit 0
fi

echo
echo "[4/5] Restoring database..."

kubectl exec \
  -n "$NAMESPACE" \
  "$INSPECTOR_POD" \
  -- gzip -dc "$BACKUP_PATH" \
| kubectl exec \
    -i \
    -n "$NAMESPACE" \
    "$DB_POD" \
    -- sh -c \
    'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'

echo
echo "[5/5] Restore completed."

echo
echo "========================================"
echo " Database restore successful"
echo "========================================"

