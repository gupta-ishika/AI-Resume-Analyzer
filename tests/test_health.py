from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Verify health endpoint returns healthy status and service info."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "environment" in data


def test_error_response_format(client: TestClient):
    """Verify 404 error adheres to API contract error schema."""
    response = client.get("/api/nonexistent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "error" in data
