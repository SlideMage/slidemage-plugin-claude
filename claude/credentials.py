# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""The host owns secret storage and legacy-key lookup; activation only obtains a handle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from slidemage.plugin_api import Credentials
    from slidemage.plugin_api import Host

ENV_VAR = "ANTHROPIC_API_KEY"
SOURCE_ENV, SOURCE_KEYCHAIN, SOURCE_FILE = "environment", "keychain", "file"


@dataclass(frozen=True)
class ApiKey:
    value: str
    source: str


class ApiCredentials:
    def __init__(self, host: Host) -> None:
        self.host = host
        self.store: Credentials = host.credentials(env_var=ENV_VAR)
        self.settings = host.settings()

    def get(self, ctx: Any = None) -> ApiKey | None:
        value = self.store.get()
        if value:
            return ApiKey(value, self.store.where())
        return None if self.settings.get("legacy_key_replaced", False) else _legacy_key(ctx or self.host)

    def set(self, key: str) -> str:
        where = self.store.set(key.strip())
        # A clear must not resurrect the old built-in key at the next start.
        self.settings.set("legacy_key_replaced", True)
        self.settings.save()
        return where


def _legacy_key(ctx: Any = None) -> ApiKey | None:
    value = ctx.legacy_secret("anthropic_api_key")
    return ApiKey(value, "legacy SlideMage storage") if value else None


def get_api_key(ctx: Any) -> ApiKey | None:
    """Compatibility for for_project(); registered routes use their own host credentials handle."""
    return _legacy_key(ctx)
