"""Integration tests for T58's `POST /api/v1/auth/login`, against the real
mounted FastAPI app and real Postgres.

`tests/conftest.py`'s `client` fixture and `db_session` fixture use
independent `AsyncSession`s -- a user created via `db_session` (flush-only,
rolled back at teardown, never committed) would be invisible to a request
made through that fixture, since its own `get_db()` opens an unrelated
session/transaction. Overriding `get_db` on the real `app` to yield
`db_session` instead (test-infrastructure only, undone in fixture teardown,
production `get_db()` untouched) fixes that -- but only works with an
async-native HTTP client in the same event loop as `db_session` itself.
`fastapi.testclient.TestClient` (confirmed by directly trying it) runs the
ASGI app on a separate thread/event loop via anyio's blocking portal, so a
`db_session`-backed override raises `RuntimeError: ... attached to a
different loop` the moment a request touches the database. `httpx.AsyncClient`
against an `ASGITransport` wrapping the same `app` makes the same kind of
genuine, real-routing-and-middleware HTTP request against the real app, in
the current (pytest-asyncio) event loop, so the override actually works.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.security.password_hasher import hash_password
from app.main import app

_PASSWORD = "correct horse battery staple"


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _make_user(db_session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": f"{uuid4()}@example.com",
        "full_name": "Test Advocate",
        "password_hash": hash_password(_PASSWORD),
        "is_active": True,
    }
    user = User(**{**defaults, **overrides})
    db_session.add(user)
    await db_session.flush()
    return user


class TestLogin:
    async def test_valid_credentials_returns_tokens(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"}
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_unknown_email_returns_401_with_the_same_generic_message(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The message must not let a caller distinguish "wrong password"
        from "no such account" -- `AuthService.authenticate()` already
        collapses both, this just proves the route doesn't undo that."""
        user = await _make_user(db_session)

        wrong_password_response = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"}
        )
        unknown_email_response = await client.post(
            "/api/v1/auth/login",
            json={"email": f"{uuid4()}@example.com", "password": _PASSWORD},
        )

        assert unknown_email_response.status_code == 401
        assert unknown_email_response.json()["error"]["code"] == "unauthorized"
        assert isinstance(unknown_email_response.json()["error"]["message"], str)
        assert (
            unknown_email_response.json()["error"]["message"]
            == wrong_password_response.json()["error"]["message"]
        )

    async def test_inactive_user_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, is_active=False)

        response = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_malformed_request_body_returns_422(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login", json={"email": "missing-password@example.com"}
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert isinstance(response.json()["error"]["message"], str)


class TestLoginAuditing:
    """T65: `POST /auth/login` wires through to `AuthService.authenticate()`'s
    new `AuditLogger` calls -- `LoggingAuditLogger` (the real, container-
    registered implementation, unmocked here) writes each event as a
    structured `logger.info(...)` call on the `app.audit` channel, captured
    via `caplog` directly attached to that logger (`app`'s own logger has
    `propagate=False`, so a plain root-level `caplog` capture would miss
    these -- `logger="app.audit"` attaches the capturing handler directly to
    the channel that actually emits them, independent of that setting).
    """

    async def test_successful_login_records_exactly_one_login_success_event(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        user = await _make_user(db_session)

        with caplog.at_level(logging.INFO, logger="app.audit"):
            response = await client.post(
                "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
            )

        assert response.status_code == 200
        audit_records = [record for record in caplog.records if record.name == "app.audit"]
        assert len(audit_records) == 1
        record = audit_records[0]
        assert record.action == "login_success"
        assert record.resource_type == "auth"
        assert record.actor_id == str(user.id)
        assert _PASSWORD not in record.getMessage()
        assert _PASSWORD not in repr(record.metadata)
        assert _PASSWORD not in repr(record.__dict__)

    async def test_wrong_password_records_exactly_one_login_failure_event(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        user = await _make_user(db_session)

        with caplog.at_level(logging.INFO, logger="app.audit"):
            response = await client.post(
                "/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"}
            )

        assert response.status_code == 401
        audit_records = [record for record in caplog.records if record.name == "app.audit"]
        assert len(audit_records) == 1
        record = audit_records[0]
        assert record.action == "login_failure"
        assert record.resource_type == "auth"
        assert record.metadata == {"email": user.email, "reason": "wrong_password"}
        assert "wrong-password" not in repr(record.__dict__)

    async def test_unknown_email_records_exactly_one_login_failure_event(
        self, client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        email = f"{uuid4()}@example.com"

        with caplog.at_level(logging.INFO, logger="app.audit"):
            response = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
            )

        assert response.status_code == 401
        audit_records = [record for record in caplog.records if record.name == "app.audit"]
        assert len(audit_records) == 1
        record = audit_records[0]
        assert record.action == "login_failure"
        assert record.resource_type == "auth"
        assert record.metadata == {"email": email, "reason": "unknown_user"}

    async def test_inactive_account_records_exactly_one_login_failure_event(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        user = await _make_user(db_session, is_active=False)

        with caplog.at_level(logging.INFO, logger="app.audit"):
            response = await client.post(
                "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
            )

        assert response.status_code == 401
        audit_records = [record for record in caplog.records if record.name == "app.audit"]
        assert len(audit_records) == 1
        record = audit_records[0]
        assert record.action == "login_failure"
        assert record.resource_type == "auth"
        assert record.metadata == {"email": user.email, "reason": "inactive_account"}

    async def test_malformed_request_body_records_no_audit_event(
        self, client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """422 validation errors are explicitly excluded from T65's scope --
        the request never reaches `AuthService.authenticate()` at all, since
        FastAPI rejects the malformed body before the route handler runs."""
        with caplog.at_level(logging.INFO, logger="app.audit"):
            response = await client.post(
                "/api/v1/auth/login", json={"email": "missing-password@example.com"}
            )

        assert response.status_code == 422
        assert [record for record in caplog.records if record.name == "app.audit"] == []
