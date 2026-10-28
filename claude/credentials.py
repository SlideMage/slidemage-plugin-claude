# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""The host owns secret storage and legacy-key lookup; activation only obtains a handle.

The legacy migration helper is still private in 3d. This import is deferred until
lookup, retained as a DRAFT dependency until core exposes migration through plugin_api.
Old copies are read only, never silently copied or cleared by activation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from slidemage.plugin_api import Credentials
    from claude.host import Host

ENV_VAR = "ANTHROPIC_API_KEY"
SOURCE_ENV, SOURCE_KEYCHAIN, SOURCE_FILE = "environment", "keychain", "file"


@dataclass(frozen=True)
class ApiKey:
    value: str
    source: str


class ApiCredentials:
    def __init__(self, host: Host) -> None:
        self.store: Credentials = host.credentials(env_var=ENV_VAR)
        self.settings = host.settings()

    def get(self, ctx: Any = None) -> ApiKey | None:
        value = self.store.get()
        if value:
            return ApiKey(value, self.store.where())
        return None if self.settings.get("legacy_key_replaced", False) else _legacy_key(ctx)

    def set(self, key: str) -> str:
        where = self.store.set(key.strip())
        # A clear must not resurrect the old built-in key at the next start.
        self.settings.set("legacy_key_replaced", True)
        self.settings.save()
        return where


def _legacy_key(ctx: Any = None) -> ApiKey | None:
    # DRAFT: 3d implements migration, but has no public host/plugin_api entry for it yet.
    from slidemage.plugins.migrate import legacy_anthropic_key
    if ctx is None:
        from slidemage.project import from_environment
        ctx = from_environment()
    value = legacy_anthropic_key(ctx)
    return ApiKey(value, "legacy SlideMage storage") if value else None


def get_api_key(ctx: Any) -> ApiKey | None:
    """Compatibility for for_project(); registered routes use their own host credentials handle."""
    return _legacy_key(ctx)
