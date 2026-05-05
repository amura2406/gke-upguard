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

import os
import google.auth
from google.adk.agents import Agent, SequentialAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import discover_gke_clusters, get_cluster_workloads, fetch_changelogs

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id if project_id else "mock-project"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


def create_discovery_agent():
    return Agent(
        name="discovery_agent",
        model=Gemini(
            model="gemini-3.1-pro-preview",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction="""You are a Kubernetes Infrastructure Discovery Agent.
Your goal is to discover all GKE clusters in the GCP project and fetch their running workloads (Deployments, StatefulSets, DaemonSets, CronJobs, and Pods).
You will receive a request with a target version to upgrade to.
1. Use `discover_gke_clusters` to find all clusters.
2. For each cluster found, use `get_cluster_workloads(cluster_name, location)` to fetch its workloads.
Compile this information into a structured summary of the infrastructure.
Make sure to pass the target version string clearly to the next agent in your output.
""",
        output_key="infrastructure_state",
        tools=[discover_gke_clusters, get_cluster_workloads],
    )


def create_changelog_agent():
    return Agent(
        name="changelog_agent",
        model=Gemini(
            model="gemini-3.1-pro-preview",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction="""You are a Kubernetes Release Analyzer Agent.
Your input includes the target version for a GKE upgrade (e.g., from the user's initial prompt or passed along by the discovery agent).
Extract the target version and use the `fetch_changelogs(target_version)` tool to get the breaking changes and deprecations for that version.
Output the extracted risk factors and the target version clearly.
""",
        output_key="upgrade_risks",
        tools=[fetch_changelogs],
    )


def create_assessment_agent():
    return Agent(
        name="assessment_agent",
        model=Gemini(
            model="gemini-3.1-pro-preview",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction="""You are a GKE Upgrade Risk Assessment Coordinator.
You receive the discovered infrastructure state from `discovery_agent` (available in the history, and in {infrastructure_state}) and the upgrade risks from `changelog_agent` (available in the history, and in {upgrade_risks}).
Compare the running workloads (images, resource types) against the breaking changes and deprecations.
Generate a final, comprehensive Markdown report detailing the potential risks of the upgrade for the specific clusters and workloads discovered.
Be specific about which workloads might be impacted by which breaking changes.
""",
    )


root_agent = SequentialAgent(
    name="root_agent",
    sub_agents=[
        create_discovery_agent(),
        create_changelog_agent(),
        create_assessment_agent(),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
