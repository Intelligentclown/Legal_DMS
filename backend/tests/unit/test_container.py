"""Tests for the hand-rolled DI container."""

import pytest

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.di.container import (
    Container,
    ContainerError,
    configure_container,
    container,
)


class _Widget:
    pass


class TestContainer:
    def test_singleton_registration_returns_the_same_instance(self) -> None:
        c = Container()
        c.register(_Widget, _Widget)

        first = c.resolve(_Widget)
        second = c.resolve(_Widget)

        assert first is second

    def test_non_singleton_registration_returns_a_new_instance_each_time(self) -> None:
        c = Container()
        c.register(_Widget, _Widget, singleton=False)

        first = c.resolve(_Widget)
        second = c.resolve(_Widget)

        assert first is not second

    def test_resolving_an_unregistered_type_raises(self) -> None:
        c = Container()

        with pytest.raises(ContainerError):
            c.resolve(_Widget)

    def test_is_registered_reflects_registration_state(self) -> None:
        c = Container()

        assert not c.is_registered(_Widget)
        c.register(_Widget, _Widget)
        assert c.is_registered(_Widget)

    def test_override_forces_a_specific_instance(self) -> None:
        c = Container()
        c.register(_Widget, _Widget)
        fake = _Widget()

        c.override(_Widget, fake)

        assert c.resolve(_Widget) is fake

    def test_reset_clears_all_registrations(self) -> None:
        c = Container()
        c.register(_Widget, _Widget)

        c.reset()

        assert not c.is_registered(_Widget)
        with pytest.raises(ContainerError):
            c.resolve(_Widget)


class TestConfigureContainer:
    def test_registers_settings_resolvable_through_the_global_container(self) -> None:
        configure_container()

        assert container.is_registered(Settings)
        assert container.resolve(Settings) is get_settings()
