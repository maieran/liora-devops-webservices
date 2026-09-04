# Kubernetes Deployment Validation

This directory contains validation tests for the Liora Kubernetes deployment.

The validation script is intended to verify that a Helm deployment is healthy and accessible after deployment.

## What is validated?

The script checks the following:

- All active Pods are in `Running` state and Ready
- Kubernetes Deployments completed their rollout successfully
- Kubernetes StatefulSets completed their rollout successfully
- PersistentVolumeClaims (PVCs) are `Bound`
- Required Kubernetes Services have active endpoints
- No recent readiness or liveness probe failures are detected
- Nginx and the application routes are reachable

The following application endpoints are tested:

- `/health` – Nginx health endpoint
- `/` – PrestaShop
- `/wordpress/` – WordPress

## Usage

Run the validation script with the Kubernetes namespace and the public application URL:

```bash
./tests/kubernetes/validate-deployment.sh <namespace> <base-url>

Example for the development environment:
./tests/kubernetes/validate-deployment.sh \
  liora-dev \
  http://10.10.10.11:30080

  A successful validation ends with: Kubernetes deployment validation PASSED
  If one of the required checks fails, the script exits with a non-zero exit code.

# Helm Validation
Before deployment, the Helm chart can be validated using:
helm lint ./helm/liora -f helm/liora/values-dev.yaml

The rendered Kubernetes manifests can also be checked with:
helm template liora-dev ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml

# Helm Deployment

The development environment can be deployed or updated with:
helm upgrade --install liora-dev \
  ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost=10.10.10.11 \
  --set networkPolicy.enabled=true \
  --wait \
  --timeout 6m

Running the same helm upgrade --install command again can be used to verify that the deployment remains stable and idempotent.

After the upgrade, run the Kubernetes validation script again.

# Monitoring Validation

The monitoring stack has its own validation script:
bash monitoring/validate-monitoring.sh

It validates:

Monitoring namespace
Monitoring Pods
Helm releases
Grafana dashboard ConfigMap
Liora alert rules
Blackbox ServiceMonitor

A successful monitoring validation ends with: Monitoring validation PASSED

Jenkins CI/CD Integration

The Jenkins pipeline validates the Helm charts during CI.

For the main branch, Jenkins additionally:

Pushes the Docker images
Deploys the application to Kubernetes Dev using Helm
Waits for the Kubernetes Deployments to complete their rollouts
Runs tests/kubernetes/validate-deployment.sh
Validates the monitoring stack

The Kubernetes deployment and monitoring stages are intentionally restricted to the main branch.

Feature branches validate the pipeline, Helm charts, Docker build and development tests without modifying the Kubernetes Dev deployment.