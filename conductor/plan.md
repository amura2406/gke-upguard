# Implementation Plan: GKE Upgrade Risk Agent Enhancements

## Goal
Finish the `gke-upgrade-risk-agent` by implementing features for the subagent to fetch all existing running GKE clusters, pods, deployments, statefulsets, daemonsets, and cronjobs, and compare them against the changelogs of the target GKE version.

## Strategy

We will refactor the agent into a multi-agent orchestrated workflow using ADK's `SequentialAgent` or standard sub-agent delegation. This provides better separation of concerns and improves the LLM's reliability on specific tasks.

### 1. Dependencies Update
- Install `google-cloud-container` to allow the agent to programmatically discover GKE clusters within the GCP project.
- Command: `cd gke-upgrade-risk-agent && uv add google-cloud-container`

### 2. Tools Refactoring (`gke-upgrade-risk-agent/app/tools.py`)
Extract and expand tools into a dedicated file:
- **`discover_gke_clusters(project_id: str, location: str) -> str`**: Uses the `google.cloud.container_v1` API to list all active GKE clusters.
- **`get_cluster_workloads(cluster_name: str, location: str, project_id: str) -> str`**: Authenticates to the specific cluster and uses the `kubernetes` Python client (`AppsV1Api`, `BatchV1Api`, `CoreV1Api`) to fetch running:
  - Pods
  - Deployments
  - StatefulSets
  - DaemonSets
  - CronJobs / Jobs
- **`fetch_changelogs(target_version: str) -> str`**: (Existing) Fetches release notes and extracts breaking changes.

### 3. Agent Architecture Refactoring (`gke-upgrade-risk-agent/app/agent.py`)
Replace the single `root_agent` with a `SequentialAgent` pipeline:
- **`discovery_agent`**: Responsible for listing GKE clusters and fetching their workloads using the new discovery tools. Outputs the infrastructure state.
- **`changelog_agent`**: Responsible for fetching and parsing the Kubernetes changelogs to identify deprecations and breaking changes. Outputs the risk factors.
- **`assessment_agent` (Root Agent)**: Takes the outputs from the `discovery_agent` and `changelog_agent`, compares the workloads' specifications against the breaking changes, and generates the final markdown risk assessment report.

### 4. Testing & Validation
- Update `tests/unit/test_agent_tools.py` with mock responses for the new workload and cluster discovery tools.
- Run `agents-cli eval run` and `uv run pytest` to ensure everything is functioning correctly.

## Next Steps
Once this plan is approved, I will proceed with adding the dependency and implementing the tools and agent orchestration.