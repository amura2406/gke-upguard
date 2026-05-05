import json
import os
import google.auth
from google.cloud import container_v1
from kubernetes import client, config


def discover_gke_clusters() -> str:
    """Discovers all active GKE clusters in the current GCP project.
    Returns a JSON string containing cluster details (name, location, version).
    """
    try:
        credentials, project_id = google.auth.default()
        if not project_id:
            return json.dumps({"error": "Could not determine GCP project_id."})

        gke_client = container_v1.ClusterManagerClient(credentials=credentials)
        parent = f"projects/{project_id}/locations/-"
        request = container_v1.ListClustersRequest(parent=parent)
        response = gke_client.list_clusters(request=request)

        clusters = []
        for cluster in response.clusters:
            clusters.append(
                {
                    "name": cluster.name,
                    "location": cluster.location,
                    "version": cluster.current_master_version,
                    "status": cluster.status.name,
                    # Using private_endpoint for private clusters. For public ones, it might use endpoint.
                    "endpoint": cluster.private_cluster_config.private_endpoint
                    if cluster.private_cluster_config.enable_private_endpoint
                    else cluster.endpoint,
                }
            )

        return json.dumps({"project_id": project_id, "clusters": clusters})
    except Exception as e:
        return json.dumps(
            {
                "warning": f"Failed to list clusters: {e}. Using mock data.",
                "project_id": "mock-project-123",
                "clusters": [
                    {
                        "name": "primary",
                        "location": "us-central1-c",
                        "version": "1.27.3-gke.100",
                        "status": "RUNNING",
                    }
                ],
            }
        )


def _get_kubernetes_client_for_cluster(
    cluster_name: str, location: str, project_id: str
):
    """Internal helper to get a Kubernetes client for a specific cluster."""
    # 1. Try local kubeconfig first (e.g., localhost dev, or VPN with kubeconfig)
    try:
        config.load_kube_config(context=f"gke_{project_id}_{location}_{cluster_name}")
        return client.CoreV1Api(), client.AppsV1Api(), client.BatchV1Api()
    except Exception:
        # Fall back to try the current default context (might be the one we want)
        try:
            config.load_kube_config()
            return client.CoreV1Api(), client.AppsV1Api(), client.BatchV1Api()
        except Exception:
            pass

    # 2. Dynamic authentication for Cloud Run (Agent Engine / Cloud Run environment)
    import base64
    from kubernetes.client import Configuration
    from kubernetes.client.api_client import ApiClient

    # Get credentials for GCP API
    credentials, _ = google.auth.default()
    gke_client = container_v1.ClusterManagerClient(credentials=credentials)

    name = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"
    response = gke_client.get_cluster(name=name)

    # Refresh GCP credentials to get a fresh access token
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)

    # Configure the Kubernetes Python client
    configuration = Configuration()

    # Use private endpoint if enabled, otherwise public endpoint
    if response.private_cluster_config.enable_private_endpoint:
        configuration.host = (
            f"https://{response.private_cluster_config.private_endpoint}"
        )
    else:
        configuration.host = f"https://{response.endpoint}"

    configuration.verify_ssl = True
    # The master_auth.cluster_ca_certificate is base64 encoded
    ca_cert_data = base64.b64decode(response.master_auth.cluster_ca_certificate)

    # We must write the CA cert to a temporary file for the kubernetes client to use
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as ca_file:
        ca_file.write(ca_cert_data)
        configuration.ssl_ca_cert = ca_file.name

    configuration.api_key = {"authorization": "Bearer " + credentials.token}

    api_client = ApiClient(configuration)
    return (
        client.CoreV1Api(api_client),
        client.AppsV1Api(api_client),
        client.BatchV1Api(api_client),
    )


def get_cluster_workloads(cluster_name: str, location: str) -> str:
    """Fetches all existing running Pods, Deployments, StatefulSets, DaemonSets, and CronJobs for a given cluster.
    Requires the cluster_name and location.
    Returns a JSON string with the workloads specs.
    """
    try:
        credentials, project_id = google.auth.default()
        if not project_id:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-123")

        core_v1, apps_v1, batch_v1 = _get_kubernetes_client_for_cluster(
            cluster_name, location, project_id
        )

        # Pods
        pods = core_v1.list_pod_for_all_namespaces()
        pod_specs = [
            {
                "name": p.metadata.name,
                "namespace": p.metadata.namespace,
                "images": [c.image for c in p.spec.containers],
            }
            for p in pods.items
        ]

        # Deployments
        deps = apps_v1.list_deployment_for_all_namespaces()
        dep_specs = [
            {
                "name": d.metadata.name,
                "namespace": d.metadata.namespace,
                "images": [c.image for c in d.spec.template.spec.containers],
            }
            for d in deps.items
        ]

        # StatefulSets
        sts = apps_v1.list_stateful_set_for_all_namespaces()
        sts_specs = [
            {
                "name": s.metadata.name,
                "namespace": s.metadata.namespace,
                "images": [c.image for c in s.spec.template.spec.containers],
            }
            for s in sts.items
        ]

        # DaemonSets
        ds = apps_v1.list_daemon_set_for_all_namespaces()
        ds_specs = [
            {
                "name": d.metadata.name,
                "namespace": d.metadata.namespace,
                "images": [c.image for c in d.spec.template.spec.containers],
            }
            for d in ds.items
        ]

        # CronJobs
        cjs = batch_v1.list_cron_job_for_all_namespaces()
        cj_specs = [
            {
                "name": c.metadata.name,
                "namespace": c.metadata.namespace,
                "images": [
                    co.image for co in c.spec.job_template.spec.template.spec.containers
                ],
            }
            for c in cjs.items
        ]

        return json.dumps(
            {
                "cluster_name": cluster_name,
                "location": location,
                "workloads": {
                    "pods": pod_specs,
                    "deployments": dep_specs,
                    "statefulsets": sts_specs,
                    "daemonsets": ds_specs,
                    "cronjobs": cj_specs,
                },
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "warning": f"Failed to fetch workloads for {cluster_name}: {e}. Using mock data.",
                "cluster_name": cluster_name,
                "location": location,
                "workloads": {
                    "deployments": [
                        {
                            "name": "nginx-deployment",
                            "namespace": "mock-env",
                            "images": ["nginx:latest"],
                        },
                        {
                            "name": "java8-app",
                            "namespace": "mock-env",
                            "images": ["eclipse-temurin:8-jre"],
                        },
                        {
                            "name": "java11-app",
                            "namespace": "mock-env",
                            "images": ["eclipse-temurin:11-jre"],
                        },
                    ],
                    "statefulsets": [
                        {
                            "name": "redis",
                            "namespace": "mock-env",
                            "images": ["redis:alpine"],
                        }
                    ],
                    "daemonsets": [
                        {
                            "name": "mock-logger",
                            "namespace": "mock-env",
                            "images": ["alpine:latest"],
                        }
                    ],
                    "pods": [
                        {
                            "name": "nginx-deployment-abc-123",
                            "namespace": "mock-env",
                            "images": ["nginx:latest"],
                        }
                    ],
                },
            }
        )


def fetch_changelogs(target_version: str) -> str:
    """Fetches changelogs for the target GKE version from Kubernetes GitHub repo
    and extracts breaking changes and deprecations using Gemini.
    """
    import requests
    from google import genai

    try:
        parts = target_version.split(".")
        if len(parts) >= 2:
            version_prefix = f"{parts[0]}.{parts[1]}"
        else:
            version_prefix = target_version

        url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/master/CHANGELOG/CHANGELOG-{version_prefix}.md"

        response = requests.get(url)
        if response.status_code != 200:
            return f"Failed to fetch changelog from {url}. Status code: {response.status_code}"

        content = response.text

        header = f"# v{version_prefix}.0"
        start_idx = content.find(header)
        if start_idx == -1:
            header = f"# {version_prefix}.0"
            start_idx = content.find(header)

        if start_idx != -1:
            next_header_idx = content.find("# ", start_idx + len(header))
            if next_header_idx != -1:
                relevant_content = content[start_idx:next_header_idx]
            else:
                relevant_content = content[start_idx:]
        else:
            relevant_content = content[:50000]

        client = genai.Client()

        prompt = f"""
        You are an expert Kubernetes operator.
        Analyze the attached release notes for Kubernetes {version_prefix} and extract:
        1. **Deprecations**: Any APIs or features that are deprecated in this release.
        2. **Breaking Changes/Removals**: Any APIs or features that are removed or have breaking changes in this release.
        3. **Action Required**: Any specific actions operators need to take before or after upgrade.
        
        Be concise and focus on things that might break running applications.
        """

        model_name = "gemini-3.1-pro-preview"

        llm_response = client.models.generate_content(
            model=model_name,
            contents=[prompt, relevant_content],
        )

        return f"Extracted Upgrade Risks for {version_prefix}:\n{llm_response.text}"

    except Exception as e:
        return f"Error fetching or processing changelogs: {e}"
