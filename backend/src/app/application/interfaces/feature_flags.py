"""Feature flag port: lets future modules be enabled or disabled through
configuration, without an if/else scattered through business code. Concrete
implementation reads from `Settings` — see
`infrastructure/config/feature_flags.py`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class FeatureFlagProvider(ABC):
    @abstractmethod
    def is_enabled(self, flag_name: str) -> bool: ...
