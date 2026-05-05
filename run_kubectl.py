import os
import subprocess
from google.cloud import container_v1
import google.auth
from kubernetes import client, config

credentials, project_id = google.auth.default()

gke_client = container_v1.ClusterManagerClient(credentials=credentials)
name = f"projects/{project_id}/locations/us-central1-a/clusters/mock-upgrade-cluster"
response = gke_client.get_cluster(name=name)

# Refresh GCP credentials to get a fresh access token
auth_req = google.auth.transport.requests.Request()
credentials.refresh(auth_req)

import base64
from kubernetes.client import Configuration
from kubernetes.client.api_client import ApiClient

configuration = Configuration()
configuration.host = f"https://{response.endpoint}"
configuration.verify_ssl = False

configuration.api_key = {"authorization": "Bearer " + credentials.token}
api_client = ApiClient(configuration)

rbac = client.RbacAuthorizationV1Api(api_client)

binding = client.V1ClusterRoleBinding(
    metadata=client.V1ObjectMeta(name="agent-viewer-compute"),
    role_ref=client.V1RoleRef(
        api_group="rbac.authorization.k8s.io",
        kind="ClusterRole",
        name="view"
    ),
    subjects=[
        client.RbacV1Subject(
            kind="User",
            name="575433586038-compute@developer.gserviceaccount.com"
        )
    ]
)

try:
    rbac.create_cluster_role_binding(body=binding)
    print("Binding created successfully")
except Exception as e:
    print(f"Failed or already exists: {e}")
