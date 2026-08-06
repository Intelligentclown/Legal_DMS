"""Tests for the feature flag framework: Settings.feature_flags parsing +
SettingsFeatureFlagProvider.
"""

from __future__ import annotations

import pytest

from app.application.interfaces.feature_flags import FeatureFlagProvider
from app.infrastructure.config.feature_flags import SettingsFeatureFlagProvider
from app.infrastructure.config.settings import Settings
from app.infrastructure.di.container import configure_container, container


class TestSettingsFeatureFlagsParsing:
    def test_defaults_to_empty(self) -> None:
        settings = Settings(_env_file=None, jwt_secret_key="test-secret")

        assert settings.feature_flags == {}

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("beta:true", {"beta": True}),
            ("beta:false", {"beta": False}),
            ("beta:true,other:false", {"beta": True, "other": False}),
            ("beta:TRUE, other:No", {"beta": True, "other": False}),
            ("beta:1,other:0", {"beta": True, "other": False}),
        ],
    )
    def test_parses_comma_separated_name_value_pairs(
        self, raw: str, expected: dict[str, bool]
    ) -> None:
        settings = Settings(_env_file=None, jwt_secret_key="test-secret", feature_flags=raw)

        assert settings.feature_flags == expected

    def test_accepts_a_dict_directly(self) -> None:
        settings = Settings(
            _env_file=None, jwt_secret_key="test-secret", feature_flags={"beta": True}
        )

        assert settings.feature_flags == {"beta": True}


class TestSettingsFeatureFlagProvider:
    def test_returns_true_for_an_enabled_flag(self) -> None:
        settings = Settings(_env_file=None, jwt_secret_key="test-secret", feature_flags="beta:true")
        provider = SettingsFeatureFlagProvider(settings)

        assert provider.is_enabled("beta") is True

    def test_returns_false_for_a_disabled_flag(self) -> None:
        settings = Settings(
            _env_file=None, jwt_secret_key="test-secret", feature_flags="beta:false"
        )
        provider = SettingsFeatureFlagProvider(settings)

        assert provider.is_enabled("beta") is False

    def test_unknown_flag_defaults_to_disabled(self) -> None:
        settings = Settings(_env_file=None, jwt_secret_key="test-secret")
        provider = SettingsFeatureFlagProvider(settings)

        assert provider.is_enabled("does-not-exist") is False


class TestConfigureContainer:
    def test_registers_feature_flag_provider(self) -> None:
        configure_container()

        assert isinstance(container.resolve(FeatureFlagProvider), SettingsFeatureFlagProvider)
