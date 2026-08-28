# Kubernetes Secrets

The Kubernetes workloads require database credentials that must **not be stored directly in the repository**.

The application expects a Kubernetes Secret named:

```text
liora-db-secrets
```

inside the namespace:

```text
liora-dev
```

The Secret is created manually for the current development environment.

---

## Required Secret Keys

The Secret must contain the following eight keys:

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

These keys are referenced by the WordPress, PrestaShop and MySQL Kubernetes workloads.

---

## Create the Secret

Create the namespace first:

```bash
kubectl apply \
  -f kubernetes/base/namespace/
```

Then create the Secret:

```bash
kubectl create secret generic liora-db-secrets \
  --namespace liora-dev \
  --from-literal=WORDPRESS_DB_NAME='<wordpress-db-name>' \
  --from-literal=WORDPRESS_DB_USER='<wordpress-db-user>' \
  --from-literal=WORDPRESS_DB_PASSWORD='<wordpress-db-password>' \
  --from-literal=WORDPRESS_DB_ROOT_PASSWORD='<wordpress-root-password>' \
  --from-literal=PRESTASHOP_DB_NAME='<prestashop-db-name>' \
  --from-literal=PRESTASHOP_DB_USER='<prestashop-db-user>' \
  --from-literal=PRESTASHOP_DB_PASSWORD='<prestashop-db-password>' \
  --from-literal=PRESTASHOP_DB_ROOT_PASSWORD='<prestashop-root-password>'
```

Replace all placeholder values before executing the command.

---

## Development Example

For a local or disposable development environment, the database names and users could for example be:

```text
WORDPRESS_DB_NAME=wordpress
WORDPRESS_DB_USER=wordpress

PRESTASHOP_DB_NAME=prestashop
PRESTASHOP_DB_USER=prestashop
```

Passwords should still be supplied separately and must not be committed to Git.

---

## Verify the Secret

Check that the Secret exists:

```bash
kubectl get secret \
  liora-db-secrets \
  -n liora-dev
```

The `DATA` column should show:

```text
8
```

To verify the available keys without printing their values:

```bash
kubectl describe secret \
  liora-db-secrets \
  -n liora-dev
```

Expected keys:

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

---

## Updating the Secret

If the Secret already exists, `kubectl create secret` will fail because the resource already exists.

For the current manual development workflow, recreate it with:

```bash
kubectl delete secret \
  liora-db-secrets \
  -n liora-dev
```

and then run the creation command again.

After changing database credentials, affected workloads may need to be restarted because environment variables from Secrets are injected when containers start.

For example:

```bash
kubectl rollout restart \
  deployment/wordpress-app \
  -n liora-dev
```

```bash
kubectl rollout restart \
  deployment/prestashop-app \
  -n liora-dev
```

Database credential changes require additional care when persistent MySQL data already exists. Changing the Kubernetes Secret does not automatically change users or passwords already stored inside an initialized MySQL database.

---

## Security Rules

Never commit files containing real database credentials.

Do not commit:

```text
.env
.env.*
secret.yaml
secrets.yaml
passwords.txt
```

unless the files contain placeholders only and are explicitly intended as templates.

The repository should contain only this documentation describing which Secret must exist.

For CI/CD and later deployment stages, credentials should be injected from the CI/CD secret store instead of being hard-coded into Kubernetes or Helm manifests.
