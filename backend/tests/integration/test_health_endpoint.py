"""Integration test exercising the FastAPI app through its HTTP interface,
proving the app boots and the presentation/middleware/config layers are
wired together correctly.
"""

from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_version_endpoint_returns_app_metadata(client: TestClient) -> None:
    response = client.get("/api/v1/version")

    assert response.status_code == 200
    body = response.json()
    assert body["version"]
    assert body["app_name"]


def test_health_response_includes_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert "X-Request-ID" in response.headers


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
