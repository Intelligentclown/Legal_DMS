"""Plugin/module registry: lets a future feature module (Sale Deed,
Agreement, Mutation, Demat, Legal Notice, TDS, ...) register itself with the
app without the core needing to know about it in advance. Each module
mounts its own routes (and registers its own container services) through
`register()`.

Deliberately lives in `infrastructure`, not `application/interfaces`:
`AppModule` references FastAPI directly (it mounts routes), and the
application layer's ports stay framework-agnostic — this is a
composition-root concern, not a domain/application port.

The global `registry` starts empty and stays that way in Stage 1 — no
business modules exist. `main.py` calls `registry.mount_all()`
unconditionally (a no-op today) so a future module only needs to register
itself; the core app never needs editing again to pick it up.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI

from app.infrastructure.di.container import Container


class AppModule(Protocol):
    """A self-contained feature module that registers itself with the app."""

    name: str

    def register(self, app: FastAPI, container: Container) -> None: ...


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, AppModule] = {}

    def register(self, module: AppModule) -> None:
        self._modules[module.name] = module

    def get(self, name: str) -> AppModule:
        if name not in self._modules:
            raise KeyError(f"No module registered with name {name!r}")
        return self._modules[name]

    @property
    def modules(self) -> list[AppModule]:
        return list(self._modules.values())

    def mount_all(self, app: FastAPI, container: Container) -> None:
        """Mount every registered module's routes onto `app`."""
        for module in self._modules.values():
            module.register(app, container)


registry = ModuleRegistry()
