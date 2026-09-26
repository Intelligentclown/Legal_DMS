from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.transaction_outcome import (
    TransactionOutcome,
    TransactionOutcomeContext,
)


@pytest.mark.asyncio
async def test_definitive_non_commit_runs_compensations_lifo_and_continues() -> None:
    context = TransactionOutcomeContext()
    calls: list[str] = []

    async def first() -> None:
        calls.append("first")

    async def failing() -> None:
        calls.append("failing")
        raise RuntimeError("cleanup failure")

    async def last() -> None:
        calls.append("last")

    context.register(first)
    context.register(failing)
    context.register(last)
    await context.finalize(TransactionOutcome.DEFINITIVE_NON_COMMIT)
    assert calls == ["last", "failing", "first"]
    with pytest.raises(RuntimeError):
        context.register(first)


@pytest.mark.asyncio
async def test_commit_and_uncertainty_discard_compensation() -> None:
    for outcome in (
        TransactionOutcome.CONFIRMED_COMMIT,
        TransactionOutcome.COMMIT_OUTCOME_UNCERTAIN,
    ):
        calls: list[str] = []
        context = TransactionOutcomeContext()

        async def action(current_calls: list[str] = calls) -> None:
            current_calls.append("called")

        context.register(action)
        await context.finalize(outcome)
        assert calls == []


@pytest.mark.asyncio
async def test_fastapi_yield_dependency_failure_prevents_success_response() -> None:
    app = FastAPI()

    async def finalizer() -> None:
        yield
        raise RuntimeError("finalization failed")

    @app.get("/")
    async def route(_: None = Depends(finalizer, scope="function")) -> dict[str, bool]:
        return {"committed": True}

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.get("/")
    assert response.status_code == 500
    assert response.text != '{"committed":true}'
