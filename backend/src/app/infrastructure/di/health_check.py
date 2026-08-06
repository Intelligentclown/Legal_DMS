"""Container health check: resolves every interface registered on a
`Container` once, to catch a broken factory (a typo'd env var, a missing
dependency) at boot instead of at first request-time use -- whichever
route happens to need that service first. Resolves
`IMPLEMENTATION_QUEUE.md`'s T15. See ADR-0015.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.di.container import Container


@dataclass(frozen=True, slots=True)
class ContainerHealthCheckFailure:
    interface: type
    error: Exception


class ContainerHealthCheckError(Exception):
    """Raised by `assert_container_healthy` when one or more registered
    interfaces failed to resolve."""

    def __init__(self, failures: list[ContainerHealthCheckFailure]) -> None:
        self.failures = failures
        summary = "; ".join(f"{failure.interface!r}: {failure.error}" for failure in failures)
        super().__init__(f"{len(failures)} registered interface(s) failed to resolve: {summary}")


def check_container_health(container: Container) -> list[ContainerHealthCheckFailure]:
    """Attempt to resolve every interface registered on `container`.

    Returns the list of failures (empty if every registration resolved
    cleanly). Deliberately catches any exception, not just `ContainerError`
    -- a broken factory can raise anything (a `ValueError` from bad config,
    a `TypeError` from a missing constructor argument, ...), and all of
    those count as an unhealthy registration.
    """
    failures: list[ContainerHealthCheckFailure] = []
    for interface in container.registered_interfaces():
        try:
            container.resolve(interface)
        except Exception as exc:
            failures.append(ContainerHealthCheckFailure(interface=interface, error=exc))
    return failures


def assert_container_healthy(container: Container) -> None:
    """Resolve every interface registered on `container`, raising
    `ContainerHealthCheckError` if any failed to resolve. Intended to be
    called once at application startup, immediately after
    `configure_container()`.
    """
    failures = check_container_health(container)
    if failures:
        raise ContainerHealthCheckError(failures)
