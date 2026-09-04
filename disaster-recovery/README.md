# Liora Disaster Recovery

Database backup and restore solution for the Liora Kubernetes environments.

This implementation protects the two MySQL databases used by:

- WordPress
- PrestaShop

It provides:

- Scheduled daily backups with a Kubernetes `CronJob`
- Manual on-demand backups
- Separate persistent backup storage
- Gzip-compressed SQL dumps
- Seven-day backup retention
- NetworkPolicies for controlled backup access
- Interactive database restore
- Tested end-to-end recovery for WordPress and PrestaShop

---

## Directory structure

```text
disaster-recovery/
├── README.md
├── kubernetes/
│   ├── backup-cronjob.yaml
│   ├── backup-networkpolicy.yaml
│   └── backup-pvc.yaml
└── scripts/
    ├── backup-now.sh
    └── restore.sh
```

---

# 1. Architecture

The Liora application uses two independent MySQL StatefulSets:

```text
WordPress
   ↓
wordpress-db
   ↓
wordpress-db-service-headless:3306

PrestaShop
   ↓
prestashop-db
   ↓
prestashop-db-service-headless:3306
```

The Disaster Recovery flow is:

```text
wordpress-db ──────┐
                   │
                   ├──> liora-db-backup CronJob
                   │       │
prestashop-db ─────┘       ├── mysqldump
                           ├── gzip
                           └── retention cleanup
                                   │
                                   ▼
                          liora-db-backups PVC
                                   │
                                   ▼
                             restore.sh
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
              wordpress-db                 prestashop-db
```

The backup PVC is separate from the database PVCs.

---

# 2. Kubernetes resources

The Disaster Recovery manifests create:

```text
PersistentVolumeClaim:
  liora-db-backups

CronJob:
  liora-db-backup

NetworkPolicies:
  allow-backup-to-databases
  allow-backup-to-wordpress-db
  allow-backup-to-prestashop-db
```

The backup workload uses:

```text
app=liora-db-backup
```

---

# 3. Database resources

Current database resources:

```text
WordPress StatefulSet:
  wordpress-db

WordPress Service:
  wordpress-db-service-headless

PrestaShop StatefulSet:
  prestashop-db

PrestaShop Service:
  prestashop-db-service-headless
```

Both databases currently use:

```text
mysql:8.0.42
```

Database credentials are read from the existing Secret:

```text
liora-db-secrets
```

Required Secret keys:

```text
WORDPRESS_DB_NAME
WORDPRESS_DB_USER
WORDPRESS_DB_PASSWORD
WORDPRESS_DB_ROOT_PASSWORD

PRESTASHOP_DB_NAME
PRESTASHOP_DB_USER
PRESTASHOP_DB_PASSWORD
PRESTASHOP_DB_ROOT_PASSWORD
```

Secret values are never stored in this directory.

---

# 4. Backup storage

Backup PVC:

```text
liora-db-backups
```

Requested size:

```text
5Gi
```

Access mode:

```text
ReadWriteOnce
```

On the current K3s environment, the PVC uses the `local-path` StorageClass.

The StorageClass uses:

```text
WaitForFirstConsumer
```

Therefore the backup PVC may remain `Pending` until the first backup Pod mounts it.

This is expected behavior. Once the first backup Job starts, the PVC should become `Bound`.

---

# 5. Scheduled backups

The backup CronJob is defined in:

```text
disaster-recovery/kubernetes/backup-cronjob.yaml
```

Schedule:

```text
0 2 * * *
```

This runs once per day at approximately 02:00.

The CronJob backs up both databases sequentially.

---

# 6. Backup format

Each backup run creates a timestamped directory:

```text
/backups/YYYY-MM-DD_HH-MM-SS/
```

Example:

```text
/backups/2026-09-02_19-47-03/
├── wordpress.sql.gz
└── prestashop.sql.gz
```

The backup uses:

```text
mysqldump
gzip
```

Important `mysqldump` options:

```text
--single-transaction
--quick
--no-tablespaces
```

These options provide a logical database backup while minimizing disruption to the running database.

---

# 7. Backup retention

Backups older than seven days are automatically removed.

Retention:

```text
7 days
```

Cleanup is performed under:

```text
/backups
```

---

# 8. Deploy Disaster Recovery resources

Example using `liora-prod`:

```bash
kubectl apply   -n liora-prod   -f disaster-recovery/kubernetes/backup-pvc.yaml
```

```bash
kubectl apply   -n liora-prod   -f disaster-recovery/kubernetes/backup-networkpolicy.yaml
```

```bash
kubectl apply   -n liora-prod   -f disaster-recovery/kubernetes/backup-cronjob.yaml
```

Verify:

```bash
kubectl get pvc,cronjob,networkpolicy -n liora-prod
```

---

# 9. Validate manifests

Client-side:

```bash
kubectl apply --dry-run=client   -f disaster-recovery/kubernetes/backup-pvc.yaml
```

```bash
kubectl apply --dry-run=client   -f disaster-recovery/kubernetes/backup-networkpolicy.yaml
```

```bash
kubectl apply --dry-run=client   -f disaster-recovery/kubernetes/backup-cronjob.yaml
```

Server-side:

```bash
kubectl apply --dry-run=server   -n liora-prod   -f disaster-recovery/kubernetes/backup-pvc.yaml
```

```bash
kubectl apply --dry-run=server   -n liora-prod   -f disaster-recovery/kubernetes/backup-networkpolicy.yaml
```

```bash
kubectl apply --dry-run=server   -n liora-prod   -f disaster-recovery/kubernetes/backup-cronjob.yaml
```

---

# 10. Manual backup

Manual backups are started with:

```text
disaster-recovery/scripts/backup-now.sh
```

Make executable:

```bash
chmod +x disaster-recovery/scripts/backup-now.sh
```

Syntax check:

```bash
bash -n disaster-recovery/scripts/backup-now.sh
```

Run:

```bash
./disaster-recovery/scripts/backup-now.sh liora-prod
```

The script:

```text
1. Creates a temporary Job from the backup CronJob
2. Waits for the Job to complete
3. Prints the backup logs
4. Exits with an error if the Job does not complete successfully
```

Expected successful output includes:

```text
Starting WordPress database backup...
WordPress database backup completed.

Starting PrestaShop database backup...
PrestaShop database backup completed.

Backup created:
wordpress.sql.gz
prestashop.sql.gz

Backup completed successfully
```

---

# 11. Verify backup Job

Check Jobs:

```bash
kubectl get jobs -n liora-prod
```

Check backup Pods:

```bash
kubectl get pods   -n liora-prod   -l app=liora-db-backup
```

Check logs:

```bash
kubectl logs   -n liora-prod   -l app=liora-db-backup   --tail=100
```

A successful manual backup should show:

```text
STATUS: Complete
COMPLETIONS: 1/1
```

---

# 12. Verify backup PVC

After the first backup Pod consumes the PVC:

```bash
kubectl get pvc liora-db-backups -n liora-prod
```

Expected:

```text
STATUS: Bound
```

The first manual backup test successfully caused the `local-path` PVC to move from `Pending` to `Bound`, as expected with `WaitForFirstConsumer`.

---

# 13. Verify backup integrity

A temporary inspector Pod can mount the backup PVC.

Example:

```bash
kubectl run backup-inspector   -n liora-prod   --image=mysql:8.0.42   --restart=Never   --overrides='
{
  "spec": {
    "containers": [
      {
        "name": "backup-inspector",
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
```

Wait:

```bash
kubectl wait   --for=condition=Ready   pod/backup-inspector   -n liora-prod   --timeout=2m
```

List files:

```bash
kubectl exec   -n liora-prod   backup-inspector   -- find /backups -maxdepth 2 -type f -ls
```

Validate gzip files:

```bash
kubectl exec   -n liora-prod   backup-inspector   -- sh -c '
    gzip -t /backups/*/wordpress.sql.gz &&
    echo "WordPress backup: OK"

    gzip -t /backups/*/prestashop.sql.gz &&
    echo "PrestaShop backup: OK"
  '
```

Expected:

```text
WordPress backup: OK
PrestaShop backup: OK
```

Remove inspector:

```bash
kubectl delete pod backup-inspector -n liora-prod
```

Deleting the inspector does not delete the backup PVC.

---

# 14. Restore

Restore script:

```text
disaster-recovery/scripts/restore.sh
```

Make executable:

```bash
chmod +x disaster-recovery/scripts/restore.sh
```

Syntax check:

```bash
bash -n disaster-recovery/scripts/restore.sh
```

Usage:

```bash
./disaster-recovery/scripts/restore.sh   <namespace>   <wordpress|prestashop>   [backup-directory|latest]
```

Examples:

```bash
./disaster-recovery/scripts/restore.sh   liora-prod   wordpress
```

```bash
./disaster-recovery/scripts/restore.sh   liora-prod   prestashop
```

Explicit backup:

```bash
./disaster-recovery/scripts/restore.sh   liora-prod   wordpress   2026-09-02_19-47-03
```

If no backup directory is supplied, the script selects the latest backup.

---

# 15. Restore safety

The restore script requires explicit confirmation.

It displays a warning and the operator must type:

```text
RESTORE
```

If the confirmation does not match exactly, the restore is cancelled.

---

# 16. Stop application writes before restoring

The restore script restores the database but does not automatically scale the application Deployment.

Before restoring WordPress:

```bash
kubectl scale deployment wordpress-app   -n liora-prod   --replicas=0
```

Restore:

```bash
./disaster-recovery/scripts/restore.sh   liora-prod   wordpress
```

Bring WordPress back:

```bash
kubectl scale deployment wordpress-app   -n liora-prod   --replicas=1
```

Wait:

```bash
kubectl rollout status deployment/wordpress-app   -n liora-prod   --timeout=10m
```

For PrestaShop:

```bash
kubectl scale deployment prestashop-app   -n liora-prod   --replicas=0
```

Restore:

```bash
./disaster-recovery/scripts/restore.sh   liora-prod   prestashop
```

Bring PrestaShop back:

```bash
kubectl scale deployment prestashop-app   -n liora-prod   --replicas=1
```

Wait:

```bash
kubectl rollout status deployment/prestashop-app   -n liora-prod   --timeout=10m
```

Stopping the application before restore prevents application writes while the database is being replaced.

---

# 17. Tested recovery procedure

The implementation was tested end-to-end against both databases.

A temporary test table was created:

```sql
CREATE TABLE dr_test (
  id INT PRIMARY KEY,
  test_value VARCHAR(100) NOT NULL
);
```

Initial state:

```text
BEFORE_BACKUP
```

A fresh backup was created.

The database value was then changed to:

```text
AFTER_BACKUP
```

After restoring from the backup, the value returned to:

```text
BEFORE_BACKUP
```

Result:

```text
WordPress   PASS
PrestaShop PASS
```

This proves that the backup files are not only created, but can actually be used to recover the databases.

The temporary `dr_test` table should be removed after testing.

---

# 18. PrestaShop recovery verification

PrestaShop stores its public shop domain in MySQL.

After a PrestaShop restore, verify:

```bash
kubectl exec -n liora-prod prestashop-db-0 --   sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
    SELECT domain, domain_ssl
    FROM ps_shop_url;
  "'
```

The value must match the current valid public host.

During the DR test, the restored PrestaShop database correctly retained the current configured host.

Avoid restoring an old backup from before a public-host/IP change unless that older configuration is intentional.

---

# 19. NetworkPolicy

The cluster uses restrictive NetworkPolicies.

The backup workload therefore requires explicit network access.

The DR policies allow:

```text
liora-db-backup
      │
      ├── DNS
      ├── wordpress-db:3306
      └── prestashop-db:3306
```

The database Pods receive matching ingress access from the backup workload.

Other traffic remains controlled by the existing policies.

---

# 20. Troubleshooting

## Backup PVC remains Pending

Check:

```bash
kubectl describe pvc liora-db-backups   -n liora-prod
```

If the StorageClass uses:

```text
WaitForFirstConsumer
```

and the event says:

```text
waiting for first consumer to be created before binding
```

this is expected.

Trigger a backup:

```bash
./disaster-recovery/scripts/backup-now.sh liora-prod
```

The PVC should bind when the backup Pod is scheduled.

## Backup Job fails

Check:

```bash
kubectl get jobs,pods -n liora-prod
```

Then:

```bash
kubectl logs   -n liora-prod   -l app=liora-db-backup   --tail=100
```

Common failure areas:

```text
PVC provisioning
DNS
NetworkPolicy
MySQL connectivity
MySQL authentication
mysqldump
```

## Verify Secret keys

Do not expose Secret values.

Verify only the keys:

```bash
kubectl get secret liora-db-secrets   -n liora-prod   -o jsonpath='{.data}' | jq 'keys'
```

## Restore uses the wrong backup

By default, the script selects the latest backup.

To avoid ambiguity, supply the timestamp explicitly:

```bash
./disaster-recovery/scripts/restore.sh   liora-prod   wordpress   2026-09-02_19-47-03
```

---

# 21. Limitations

This implementation provides application-level database recovery.

It does not provide full infrastructure-level Disaster Recovery.

The current backup storage uses K3s `local-path`, so the database PVCs and backup PVC may still physically exist on the same Kubernetes node.

The current solution protects against:

```text
Accidental data changes
Logical database corruption
Application-level data loss
Need to restore an earlier database state
```

It does not fully protect against:

```text
Complete Kubernetes node loss
Complete Proxmox host loss
Loss of the local storage disk
Datacenter-level failure
```

For stronger production protection, backups should additionally be copied outside the Kubernetes node, for example to:

```text
NFS
S3-compatible object storage
Dedicated backup server
Remote storage
```

This is outside the current bootcamp project scope.

---

# 22. Production recommendations

For a future production environment:

```text
1. Keep scheduled logical backups
2. Copy backups outside the Kubernetes node
3. Encrypt remote backups
4. Monitor backup Job failures
5. Test restores regularly
6. Define retention according to requirements
7. Define RPO and RTO
8. Rotate database credentials safely
9. Verify PrestaShop public-host configuration after restores
```

---

# 23. CI/CD integration

The backup CronJob should be deployed as part of the platform/application infrastructure.

Normal application deployments do not need to create a database backup every time.

Recommended model:

```text
Jenkins / deployment
        ↓
Deploy Kubernetes resources
        ↓
Deploy Disaster Recovery resources
        ↓
Kubernetes CronJob handles scheduled backups
```

Database restore remains a manual operator action because it is destructive.

`restore.sh` should therefore not run automatically during a normal CI/CD deployment.

