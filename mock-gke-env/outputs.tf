output "cluster_name" {
  description = "The name of the GKE cluster"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "The endpoint of the GKE cluster"
  value       = google_container_cluster.primary.endpoint
}

output "kubernetes_namespace" {
  description = "The namespace where workloads are deployed"
  value       = kubernetes_namespace.mock_env.metadata[0].name
}

output "vpc_network_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc_network.name
}

output "vpc_subnetwork_name" {
  description = "The name of the VPC subnetwork"
  value       = google_compute_subnetwork.vpc_subnetwork.name
}

output "region" {
  description = "The region of the VPC subnetwork"
  value       = google_compute_subnetwork.vpc_subnetwork.region
}
