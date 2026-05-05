# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth
import json



_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


def get_cluster_specs() -> str:
    """Fetches the current cluster version and running pods specs.
    Returns a JSON string with the data.
    """
    from kubernetes import client, config
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        version_api = client.VersionApi()
        
        cluster_version = version_api.get_code().git_version
        
        pods = v1.list_pod_for_all_namespaces()
        pod_specs = []
        for pod in pods.items:
            pod_specs.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "images": [c.image for c in pod.spec.containers]
            })
            
        return json.dumps({
            "cluster_version": cluster_version,
            "pods": pod_specs
        })
    except Exception as e:
        # Fallback to mock data with a warning
        return json.dumps({
            "warning": f"Failed to fetch real cluster data: {e}. Using mock data for simulation.",
            "cluster_version": "1.27.3-gke.100",
            "pods": [
                {"name": "nginx-pod", "namespace": "default", "images": ["nginx:1.21"]},
                {"name": "legacy-app", "namespace": "prod", "images": ["custom-app:v1"]},
                {"name": "deprecated-api-user", "namespace": "dev", "images": ["my-app:latest"]}
            ]
        })


def fetch_changelogs(target_version: str) -> str:
    """Fetches changelogs for the target GKE version from Kubernetes GitHub repo
    and extracts breaking changes and deprecations using Gemini.
    """
    import requests
    from google import genai
    
    try:
        # Extract major.minor version, e.g., "1.28" from "1.28.3"
        parts = target_version.split('.')
        if len(parts) >= 2:
            version_prefix = f"{parts[0]}.{parts[1]}"
        else:
            version_prefix = target_version
            
        url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/master/CHANGELOG/CHANGELOG-{version_prefix}.md"
        
        response = requests.get(url)
        if response.status_code != 200:
            return f"Failed to fetch changelog from {url}. Status code: {response.status_code}"
            
        content = response.text
        
        # Find the start of v{version_prefix}.0 section
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
            contents=[prompt, content],
        )
        
        return f"Extracted Upgrade Risks for {version_prefix} from GitHub:\n{llm_response.text}"
        
    except Exception as e:
        return f"Error fetching or processing changelogs: {e}"





root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-3.1-pro-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a GKE Upgrade Risk Assessment Agent.
Your goal is to analyze the impact of a GKE upgrade on existing running pods.
You will receive an UpgradeAvailableEvent notification (or details about a target version).
You must:
1. Fetch the current cluster version and running pods specs using `get_cluster_specs`.
2. Fetch the changelogs for the target version using `fetch_changelogs`.
3. Analyze the changelogs for potential breaking changes or removed APIs that might affect the running pods (based on their images or configuration if available).
4. Generate a comprehensive risk assessment report in Markdown format.
""",
    tools=[get_cluster_specs, fetch_changelogs],
)


app = App(
    root_agent=root_agent,
    name="app",
)
