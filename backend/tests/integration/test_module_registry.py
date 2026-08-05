"""Tests for the plugin/module registry, proving a dummy module can
register itself and have its route reachable — via a throwaway FastAPI app,
never the real shipped app (`main.py` only ever mounts `/health`/`/version`
plus whatever the global registry holds, which stays empty in Stage 1).
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.infrastructure.di.container import Container
from app.infrastructure.modules.registry import AppModule, ModuleRegistry, registry


class _PingModule:
    name = "ping"

    def register(self, app: FastAPI, container: Container) -> None:
        router = APIRouter()

        @router.get("/ping")
        async def ping() -> dict[str, str]:
            return {"message": "pong"}

        app.include_router(router)


class TestModuleRegistry:
    def test_register_then_get_returns_the_module(self) -> None:
        module_registry = ModuleRegistry()
        module = _PingModule()

        module_registry.register(module)

        assert module_registry.get("ping") is module

    def test_get_unregistered_name_raises(self) -> None:
        module_registry = ModuleRegistry()

        with pytest.raises(KeyError):
            module_registry.get("nope")

    def test_modules_lists_every_registered_module(self) -> None:
        module_registry = ModuleRegistry()
        module_registry.register(_PingModule())

        assert len(module_registry.modules) == 1

    def test_mount_all_wires_a_dummy_modules_route_onto_a_throwaway_app(self) -> None:
        module_registry = ModuleRegistry()
        module_registry.register(_PingModule())
        test_app = FastAPI()

        module_registry.mount_all(test_app, Container())

        client = TestClient(test_app)
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.json() == {"message": "pong"}


class TestGlobalRegistryStaysEmptyInStageOne:
    def test_no_business_modules_are_registered(self) -> None:
        assert registry.modules == []

    def test_appmodule_protocol_accepts_a_structurally_matching_object(self) -> None:
        module: AppModule = _PingModule()

        assert module.name == "ping"
