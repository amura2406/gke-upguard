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
