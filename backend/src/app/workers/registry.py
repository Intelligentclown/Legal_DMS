"""Registry mapping a job name to the `Job` instance that handles it. A
`JobQueue` implementation looks jobs up here by name when a job is enqueued.
"""

from __future__ import annotations

from typing import Any

from app.application.interfaces.job_queue import Job


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def register(self, job: Job) -> None:
        self._jobs[job.name] = job

    def get(self, name: str) -> Job:
        if name not in self._jobs:
            raise KeyError(f"No job registered with name {name!r}")
        return self._jobs[name]

    @property
    def jobs(self) -> dict[str, Job]:
        return dict(self._jobs)


class NoOpJob(Job):
    """A trivial job proving the framework works end to end. Not a real
    business job — those arrive with the feature that needs them.
    """

    name = "noop"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"echo": payload}


registry = JobRegistry()
registry.register(NoOpJob())
