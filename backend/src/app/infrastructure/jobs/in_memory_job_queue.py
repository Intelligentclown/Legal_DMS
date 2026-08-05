"""In-process background job queue: runs each job as an asyncio task and
tracks its status/result in memory. A real queue-backed implementation
(Redis/Celery/arq/...) can satisfy the same `JobQueue` port later without
touching any caller — this is deliberately the framework, not a real queue.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from app.application.interfaces.job_queue import Job, JobQueue, JobRecord, JobStatus
from app.infrastructure.logging.logger import get_logger

logger = get_logger("jobs")


class InMemoryJobQueue(JobQueue):
    def __init__(self, jobs: dict[str, Job]) -> None:
        self._jobs = jobs
        self._records: dict[UUID, JobRecord] = {}
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def enqueue(self, job_name: str, payload: dict[str, Any] | None = None) -> UUID:
        if job_name not in self._jobs:
            raise KeyError(f"No job registered with name {job_name!r}")

        job_id = uuid4()
        self._records[job_id] = JobRecord(job_id=job_id, name=job_name, status=JobStatus.PENDING)
        self._tasks[job_id] = asyncio.create_task(self._run(job_id, job_name, payload or {}))
        return job_id

    async def get_record(self, job_id: UUID) -> JobRecord | None:
        return self._records.get(job_id)

    async def wait(self, job_id: UUID) -> JobRecord:
        """Wait for a job to finish and return its final record. Not part of
        the `JobQueue` port (a real distributed queue may not support
        in-process awaiting) — useful in tests and anywhere synchronous
        completion is actually needed.
        """
        task = self._tasks.get(job_id)
        if task is not None:
            await task

        record = self._records.get(job_id)
        if record is None:
            raise KeyError(f"No job record found for {job_id!r}")
        return record

    async def _run(self, job_id: UUID, job_name: str, payload: dict[str, Any]) -> None:
        record = self._records[job_id]
        record.status = JobStatus.RUNNING
        try:
            result = await self._jobs[job_name].run(payload)
        except Exception as exc:
            logger.error(
                "Job failed",
                exc_info=exc,
                extra={"job_id": str(job_id), "job_name": job_name},
            )
            record.status = JobStatus.FAILED
            record.error = str(exc)
        else:
            record.status = JobStatus.SUCCEEDED
            record.result = result
