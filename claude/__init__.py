# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Claude plugin — DRAFT against SlideMage's planned 3a/3c route registrations."""
from __future__ import annotations

from claude.host import Host


def activate(host: Host) -> None:
    # Keep activation cheap: no providers, Qt, terminal, auth probes or keychain lookup.
    from claude.api.route import AnthropicApiRoute
    from claude.code.route import ClaudeCodeRoute
    from claude.code import hook
    from claude.credentials import ApiCredentials
    from claude.settings import build

    credentials = ApiCredentials(host)

    def section():
        return build(host, credentials)

    host.add_ai_route(AnthropicApiRoute(host, credentials, section))
    host.add_ai_route(ClaudeCodeRoute(host, section))
    host.add_settings_section("ai", "Claude", section)
    host.add_entry_point("hook", hook.main)
