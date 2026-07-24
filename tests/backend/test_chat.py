import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/chat-service'))
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_create_conversation():
    response = client.post("/api/v1/chat/conversations", json={"title": "Test Chat", "model_id": "gpt-4o"}, headers={"X-User-ID": "test"})
    assert response.status_code == 200
    assert "id" in response.json()
