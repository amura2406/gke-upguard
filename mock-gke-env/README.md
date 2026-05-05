# mock-gke-env: Mock Environment for Upgrade Simulation

This directory contains a Terraform configuration to deploy a test GKE cluster with diverse workloads. It acts as the "target" environment for the `gke-upgrade-risk-agent` to analyze.

## 🏗️ What is Deployed?

1. **Private VPC & Subnetworks:** A dedicated network structure for the cluster.
2. **Private GKE Cluster:** A 2-node GKE cluster where the Kubernetes API is private (`enable_private_endpoint = false` for local kubectl access, but worker nodes are private).
3. **Simulated Workloads:**
   - Stateless `nginx` Deployment
   - Stateful `redis` StatefulSet
   - A mock `logger` DaemonSet
   - Legacy `java8` and `java11` Deployments 

## 🚀 1-Click Deployment

Run the following commands from this directory:

```bash
terraform init
terraform apply
```

Terraform will automatically use your default GCP project. It will output important variables (like the VPC Network Name) that the `gke-upgrade-risk-agent` relies on for VPC Direct Egress.

## 🔑 Crucial: RBAC Configuration

Once the cluster is up, the `gke-upgrade-risk-agent` (running in Cloud Run) needs explicit permission to read the workloads *inside* the cluster.

After deploying this cluster AND deploying the Agent, run the following:

```bash
# 1. Authenticate your local kubectl to the new cluster
gcloud container clusters get-credentials mock-upgrade-cluster --zone us-central1-a

# 2. Grant the Cloud Run service account 'view' permissions
kubectl create clusterrolebinding agent-viewer \
  --clusterrole=view \
  --user="$(gcloud config get-value project_number)-compute@developer.gserviceaccount.com"
```

## 🧹 Clean Up

To destroy the environment and avoid ongoing costs:

```bash
terraform destroy
```