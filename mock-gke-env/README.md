# Mock GKE Environment for Upgrade Simulation

This directory contains a Terraform configuration to deploy a test GKE cluster with diverse workloads to simulate a GKE environment for upgrades.

## Prerequisites

- Terraform installed.
- `gcloud` CLI installed and authenticated.
- Active GCP project selected.

## 1-Click Deployment

Run the following commands from this directory:

```bash
terraform init
terraform apply
```

Terraform will automatically use the project ID `anggar-gke-upgrade-risk-agent` as detected during setup.

## Verifying Workloads

Once the deployment is complete, you can verify the workloads are running by getting credentials for the cluster and listing pods:

```bash
gcloud container clusters get-credentials mock-upgrade-cluster --zone us-central1-a
kubectl get pods -n mock-env
```

## Clean Up

To destroy the environment and avoid ongoing costs:

```bash
terraform destroy
```
