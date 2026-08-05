"""Reads feature flags from `Settings.feature_flags` (env-driven). A flag
not present in the map defaults to disabled — flags must be explicitly
turned on, never implicitly on by omission.
"""

from __future__ import annotations

from app.application.interfaces.feature_flags import FeatureFlagProvider
from app.infrastructure.config.settings import Settings


class SettingsFeatureFlagProvider(FeatureFlagProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_enabled(self, flag_name: str) -> bool:
        return self._settings.feature_flags.get(flag_name, False)
