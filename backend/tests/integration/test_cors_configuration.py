"""T78: CORS `allow_methods`/`allow_headers` are tightened from wildcards to
an explicit list matching the backend's actual route surface and the
frontend's actual request headers, instead of `["*"]`.

Follows the isolated `create_app()` + `TestClient` pattern established by
`test_docs_redoc_gating.py` -- the shared `client`/`app` fixture wraps the
module-level singleton built once at import time, so a CORS-preflight
`OPTIONS` request needs its own app instance too.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config.settings import Settings
from app.main import create_app

_ORIGIN = "http://localhost:5173"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    settings = Settings(_env_file=None, jwt_secret_key="test-secret", cors_origins=[_ORIGIN])
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    return TestClient(create_app())


def _preflight(client: TestClient, *, method: str, headers: str | None = None) -> httpx.Response:
    request_headers = {"Origin": _ORIGIN, "Access-Control-Request-Method": method}
    if headers is not None:
        request_headers["Access-Control-Request-Headers"] = headers
    return client.options("/api/v1/health", headers=request_headers)


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_permitted_methods_are_accepted_by_cors_preflight(client: TestClient, method: str) -> None:
    response = _preflight(client, method=method)

    assert response.status_code == 200
    assert response.headers["access-control-allow-methods"] == "GET, POST, PUT, DELETE"


@pytest.mark.parametrize("header", ["Content-Type", "Authorization"])
def test_permitted_request_headers_are_accepted_by_cors_preflight(
    client: TestClient, header: str
) -> None:
    response = _preflight(client, method="POST", headers=header)

    assert response.status_code == 200
    allowed = [h.strip() for h in response.headers["access-control-allow-headers"].split(",")]
    assert header in allowed


def test_disallowed_method_is_rejected_by_cors_preflight(client: TestClient) -> None:
    response = _preflight(client, method="TRACE")

    assert response.status_code == 400
    assert response.text == "Disallowed CORS method"


def test_disallowed_request_header_is_rejected_by_cors_preflight(client: TestClient) -> None:
    response = _preflight(client, method="POST", headers="X-Custom-Header")

    assert response.status_code == 400
    assert response.text == "Disallowed CORS headers"


def test_actual_request_still_receives_cors_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": _ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _ORIGIN


def test_actual_request_with_authorization_header_still_succeeds(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"Origin": _ORIGIN, "Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _ORIGIN
