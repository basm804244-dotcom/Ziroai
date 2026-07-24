import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/agent-service'))
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_list_templates():
    response = client.get("/api/v1/agents/templates")
    assert response.status_code == 200
    assert len(response.json()["templates"]) > 0
