import json
from unittest.mock import patch, MagicMock
import pytest
from app.tools import discover_gke_clusters, get_cluster_workloads, fetch_changelogs


def test_discover_gke_clusters_fallback():
    with patch("google.auth.default", side_effect=Exception("No credentials")):
        result = discover_gke_clusters()
        data = json.loads(result)

        assert "warning" in data
        assert data["project_id"] == "mock-project-123"
        assert len(data["clusters"]) == 1
        assert data["clusters"][0]["name"] == "primary"


def test_get_cluster_workloads_fallback():
    with patch(
        "kubernetes.config.load_kube_config", side_effect=Exception("No config")
    ):
        result = get_cluster_workloads("primary", "us-central1-c")
        data = json.loads(result)

        assert "warning" in data
        assert data["cluster_name"] == "primary"
        assert len(data["workloads"]["deployments"]) == 3
        assert data["workloads"]["deployments"][0]["name"] == "nginx-deployment"


def test_fetch_changelogs_success():
    with patch("requests.get") as mock_get, patch("google.genai.Client") as mock_genai:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "# v1.28.0\nSome content about deprecations"

        mock_llm_response = MagicMock()
        mock_llm_response.text = "Extracted content"
        mock_genai.return_value.models.generate_content.return_value = mock_llm_response

        result = fetch_changelogs("1.28.3")
        assert "Extracted Upgrade Risks for 1.28" in result
        assert "Extracted content" in result


def test_fetch_changelogs_failure():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 404

        result = fetch_changelogs("1.28.3")
        assert "Failed to fetch changelog" in result
