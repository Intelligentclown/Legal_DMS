"""Background job port: a queue that accepts named jobs with a payload,
executes them asynchronously, and reports status/result. Concrete
implementations live in `infrastructure/jobs/`. Which job a name maps to is
resolved through `workers/registry.py`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class JobRecord:
    job_id: UUID
    name: str
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None


class Job(ABC):
    """A named unit of background work. Subclass and implement `run`."""

    name: str

    @abstractmethod
    async def run(self, payload: dict[str, Any]) -> Any: ...


class JobQueue(ABC):
    @abstractmethod
    async def enqueue(self, job_name: str, payload: dict[str, Any] | None = None) -> UUID: ...

    @abstractmethod
    async def get_record(self, job_id: UUID) -> JobRecord | None: ...
