# Terraform – Proxmox Kubernetes VM

## Purpose

Terraform is used in this project only for provisioning the Proxmox infrastructure required for Kubernetes.

It creates the VM `liora-k8s-node`, which will later host the K3s/Kubernetes cluster.

Terraform does not deploy Kubernetes resources, WordPress, PrestaShop, or monitoring components. Application deployment is handled separately by Helm and Jenkins.

## Architecture

```text
Proxmox
│
├── Jenkins VM
│   └── Jenkins CI/CD
│
└── liora-k8s-node
    └── K3s / Kubernetes
        ├── liora-dev
        ├── liora-staging
        ├── liora-prod
        └── monitoring
```

The deployment flow is:

```text
Terraform
    ↓
Proxmox creates liora-k8s-node
    ↓
Ubuntu is installed on the VM
    ↓
K3s is installed
    ↓
Kubernetes API becomes available
    ↓
Jenkins uses kubeconfig
    ↓
Helm deploys DEV / STAGING / PROD
    ↓
Monitoring is deployed
```

## Proxmox Requirements

Before running Terraform, the Proxmox environment must provide:

- A Proxmox node accessible through the API
- Ubuntu Server ISO:
  `local:iso/ubuntu-24.04.4-live-server-amd64.iso`
- Storage configured for the VM disk
- A network bridge configured on the Proxmox host
- A Proxmox API token with permissions to create and manage the VM

## Authentication

Terraform authenticates against Proxmox using an API token.

Copy the example configuration:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Then configure the required Proxmox values in `terraform.tfvars`.

Do not commit API tokens or other credentials to Git.

## VM Resources

The Kubernetes VM is configured with:

```text
CPU:    4 cores
Memory: 8192 MB
Disk:   40 GB
OS:     Linux (l26)
```

The VM will host K3s, the DEV/STAGING/PROD environments, and monitoring components.

## Terraform Usage

Run the following commands from the `terraform/` directory:

```bash
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

Review the Terraform plan before running `terraform apply`.

## Manual Steps After Terraform Apply

Terraform currently provisions the VM and attaches the Ubuntu ISO.

Ubuntu installation is performed manually after the VM has been created.

After Ubuntu is installed:

1. Configure networking and SSH access.
2. Install K3s on `liora-k8s-node`.
3. Verify that the Kubernetes API is reachable.
4. Configure Jenkins with the cluster kubeconfig.
5. Deploy DEV, STAGING and PROD using Helm.
6. Deploy the monitoring stack.

Terraform does not need to run for normal application deployments. It is only required when the underlying Proxmox infrastructure changes.

## Future Improvements

Possible future improvements include:

- Cloud-Init for automated Ubuntu provisioning
- Automated K3s installation
- Remote Terraform state
- Terraform modules
- Multi-node Kubernetes cluster

These improvements are outside the current project scope.