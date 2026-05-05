resource "time_sleep" "wait_for_cluster" {
  create_duration = "180s"

  depends_on = [
    google_container_node_pool.primary_nodes
  ]
}

resource "kubernetes_namespace" "mock_env" {
  metadata {
    name = "mock-env"
  }

  depends_on = [time_sleep.wait_for_cluster]
}

# 1. Nginx Deployment (Stateless)
resource "kubernetes_deployment" "nginx" {
  metadata {
    name      = "nginx-deployment"
    namespace = kubernetes_namespace.mock_env.metadata[0].name
  }
  spec {
    replicas = 2
    selector {
      match_labels = {
        app = "nginx"
      }
    }
    template {
      metadata {
        labels = {
          app = "nginx"
        }
      }
      spec {
        container {
          name  = "nginx"
          image = "nginx:latest"
          port {
            container_port = 80
          }
        }
      }
    }
  }
}

# 2. Redis StatefulSet (Stateful)
resource "kubernetes_stateful_set" "redis" {
  metadata {
    name      = "redis"
    namespace = kubernetes_namespace.mock_env.metadata[0].name
  }
  spec {
    replicas     = 1
    service_name = "redis"
    selector {
      match_labels = {
        app = "redis"
      }
    }
    template {
      metadata {
        labels = {
          app = "redis"
        }
      }
      spec {
        container {
          name  = "redis"
          image = "redis:alpine"
          port {
            container_port = 6379
          }
        }
      }
    }
  }
}

# 3. Mock Log Forwarder DaemonSet
resource "kubernetes_daemonset" "logger" {
  metadata {
    name      = "mock-logger"
    namespace = kubernetes_namespace.mock_env.metadata[0].name
  }
  spec {
    selector {
      match_labels = {
        app = "logger"
      }
    }
    template {
      metadata {
        labels = {
          app = "logger"
        }
      }
      spec {
        container {
          name  = "logger"
          image = "alpine:latest"
          command = ["sh", "-c", "while true; do echo 'Logging data...'; sleep 10; done"]
        }
      }
    }
  }
}



# 5. Java 8 Workload
resource "kubernetes_deployment" "java8" {
  metadata {
    name      = "java8-app"
    namespace = kubernetes_namespace.mock_env.metadata[0].name
  }
  spec {
    replicas = 1
    selector {
      match_labels = {
        app = "java8"
      }
    }
    template {
      metadata {
        labels = {
          app = "java8"
        }
      }
      spec {
        container {
          name  = "java8"
          image = "eclipse-temurin:8-jre"
          command = ["sleep", "3600"]
        }
      }
    }
  }
}

# 6. Java 11 Workload
resource "kubernetes_deployment" "java11" {
  metadata {
    name      = "java11-app"
    namespace = kubernetes_namespace.mock_env.metadata[0].name
  }
  spec {
    replicas = 1
    selector {
      match_labels = {
        app = "java11"
      }
    }
    template {
      metadata {
        labels = {
          app = "java11"
        }
      }
      spec {
        container {
          name  = "java11"
          image = "eclipse-temurin:11-jre"
          command = ["sleep", "3600"]
        }
      }
    }
  }
}
