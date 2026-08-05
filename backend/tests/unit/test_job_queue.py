"""Tests for the background job framework: JobRegistry, InMemoryJobQueue,
and the container wiring.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from app.application.interfaces.job_queue import Job, JobQueue, JobStatus
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.jobs.in_memory_job_queue import InMemoryJobQueue
from app.workers.registry import JobRegistry, NoOpJob, registry


class _EchoJob(Job):
    name = "echo"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"received": payload}


class _FailingJob(Job):
    name = "failing"

    async def run(self, payload: dict[str, Any]) -> Any:
        raise RuntimeError("job blew up")


class TestJobRegistry:
    def test_register_then_get_returns_the_job(self) -> None:
        reg = JobRegistry()
        job = _EchoJob()

        reg.register(job)

        assert reg.get("echo") is job

    def test_get_unregistered_name_raises(self) -> None:
        reg = JobRegistry()

        with pytest.raises(KeyError):
            reg.get("nope")

    def test_default_registry_has_the_noop_job(self) -> None:
        job = registry.get("noop")

        assert isinstance(job, NoOpJob)


class TestInMemoryJobQueue:
    async def test_enqueue_then_wait_returns_succeeded_record_with_result(self) -> None:
        queue = InMemoryJobQueue({"echo": _EchoJob()})

        job_id = await queue.enqueue("echo", {"x": 1})
        record = await queue.wait(job_id)

        assert record.status == JobStatus.SUCCEEDED
        assert record.result == {"received": {"x": 1}}
        assert record.error is None

    async def test_enqueue_with_no_payload_defaults_to_empty_dict(self) -> None:
        queue = InMemoryJobQueue({"echo": _EchoJob()})

        job_id = await queue.enqueue("echo")
        record = await queue.wait(job_id)

        assert record.result == {"received": {}}

    async def test_failed_job_is_recorded_not_raised(self) -> None:
        queue = InMemoryJobQueue({"failing": _FailingJob()})

        job_id = await queue.enqueue("failing")
        record = await queue.wait(job_id)

        assert record.status == JobStatus.FAILED
        assert record.error == "job blew up"

    async def test_enqueue_unknown_job_name_raises(self) -> None:
        queue = InMemoryJobQueue({})

        with pytest.raises(KeyError):
            await queue.enqueue("does-not-exist")

    async def test_get_record_before_completion_can_be_pending_or_running(self) -> None:
        queue = InMemoryJobQueue({"echo": _EchoJob()})

        job_id = await queue.enqueue("echo", {})
        record = await queue.get_record(job_id)

        assert record is not None
        assert record.status in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.SUCCEEDED)

    async def test_get_record_for_unknown_id_returns_none(self) -> None:
        queue = InMemoryJobQueue({})

        assert await queue.get_record(uuid4()) is None


class TestConfigureContainer:
    async def test_registers_job_queue_seeded_with_the_default_registry(self) -> None:
        configure_container()

        resolved = container.resolve(JobQueue)

        assert isinstance(resolved, InMemoryJobQueue)
        job_id = await resolved.enqueue("noop", {"hello": "world"})
        record = await resolved.wait(job_id)
        assert record.status == JobStatus.SUCCEEDED
        assert record.result == {"echo": {"hello": "world"}}
