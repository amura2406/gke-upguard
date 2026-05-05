import json
from unittest.mock import patch, MagicMock
import pytest
from app.agent import get_cluster_specs, fetch_changelogs

def test_get_cluster_specs_fallback():
    # We test fallback first because it doesn't depend on kubernetes being installed
    # and we patch the import or the call to fail.
    with patch('kubernetes.config.load_kube_config', side_effect=Exception("No config")):
        result = get_cluster_specs()
        data = json.loads(result)
        
        assert data["cluster_version"] == "1.27.3-gke.100"
        assert len(data["pods"]) == 3
        assert data["pods"][0]["name"] == "nginx-pod"

def test_fetch_changelogs_success():
    from unittest.mock import patch, MagicMock
    with patch('requests.get') as mock_get, \
         patch('google.genai.Client') as mock_genai:
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "# v1.28.0\nSome content about deprecations"
        
        mock_llm_response = MagicMock()
        mock_llm_response.text = "Extracted content"
        mock_genai.return_value.models.generate_content.return_value = mock_llm_response
        
        result = fetch_changelogs("1.28.3")
        assert "Extracted Upgrade Risks for 1.28" in result
        assert "Extracted content" in result

def test_fetch_changelogs_failure():
    from unittest.mock import patch
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 404
        
        result = fetch_changelogs("1.28.3")
        assert "Failed to fetch changelog" in result
