import httpx
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from apps.gateway.main import app, generate_signature, verify_token


def test_verify_token_invalid():
    with pytest.raises(Exception):
        verify_token("invalid_token")


def test_generate_signature():
    sig = generate_signature("user1", "admin", "12345")
    assert sig is not None


def test_proxy_requests_no_auth():
    with TestClient(app) as client:
        response = client.get("/api/v1/studies/study_1")
        assert response.status_code == 401


def test_proxy_requests_invalid_auth():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/studies/study_1", headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401


def test_proxy_requests_valid_auth(monkeypatch):
    monkeypatch.setenv("JWT_TEST_SECRET", "test_secret")
    token = jwt.encode(
        {"sub": "user1", "roles": ["admin"]}, "test_secret", algorithm="HS256"
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/studies/study_1", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [200, 502, 500]


@pytest.mark.asyncio
async def test_get_openapi_json(monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "openapi": "3.1.0",
                "paths": {"/test": {}},
                "components": {"schemas": {"TestModel": {"type": "string"}}},
            }

    async def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "/designer/test" in data["paths"]
        assert "/execution/test" in data["paths"]
        assert "Designer_TestModel" in data["components"]["schemas"]
        assert "Execution_TestModel" in data["components"]["schemas"]


def test_get_openapi_json_error(monkeypatch):
    async def mock_get(*args, **kwargs):
        raise Exception("Connection error")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["paths"] == {}
        assert data["components"]["schemas"] == {}


def test_get_swagger_ui():
    with TestClient(app) as client:
        response = client.get("/docs")
        assert response.status_code == 200
        assert "Cadence Clinical - Unified API Docs" in response.text
