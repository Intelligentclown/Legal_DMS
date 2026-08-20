"""T77: /docs and /redoc are gated behind `settings.is_development`.

Builds an isolated FastAPI app per test via `create_app()`, with
`app.main.get_settings` monkeypatched to a `Settings` instance carrying the
`environment` under test -- the shared `client`/`app` fixture in
`conftest.py` wraps the module-level singleton built once at import time, so
it can't exercise a different environment.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config.settings import Settings
from app.main import create_app


def _build_client(monkeypatch: pytest.MonkeyPatch, environment: str) -> TestClient:
    settings = Settings(_env_file=None, jwt_secret_key="test-secret", environment=environment)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    return TestClient(create_app())


def test_docs_available_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch, "development")

    response = client.get("/docs")

    assert response.status_code == 200


def test_redoc_available_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch, "development")

    response = client.get("/redoc")

    assert response.status_code == 200


def test_docs_not_exposed_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch, "production")

    response = client.get("/docs")

    assert response.status_code == 404


def test_redoc_not_exposed_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch, "production")

    response = client.get("/redoc")

    assert response.status_code == 404


def test_docs_not_exposed_in_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch, "testing")

    response = client.get("/docs")

    assert response.status_code == 404


def test_redoc_not_exposed_in_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch, "testing")

    response = client.get("/redoc")

    assert response.status_code == 404
