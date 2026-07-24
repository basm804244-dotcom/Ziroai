import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/auth-service'))
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register():
    response = client.post("/api/v1/auth/register", json={
        "email": "test@aether.ai",
        "password": "TestPass123!",
        "full_name": "Test User",
        "username": "testuser"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login():
    client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "password": "TestPass123!",
        "full_name": "Login User",
        "username": "loginuser"
    })
    response = client.post("/api/v1/auth/login", json={"email": "login@test.com", "password": "TestPass123!"})
    assert response.status_code == 200
    assert "access_token" in response.json()
