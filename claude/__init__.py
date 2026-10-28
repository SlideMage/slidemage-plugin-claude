# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Claude plugin registration."""
from __future__ import annotations

from slidemage.plugin_api import AiRoute, Host


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

    api_route: AiRoute = AnthropicApiRoute(host, credentials)
    code_route: AiRoute = ClaudeCodeRoute(host)
    host.add_ai_route(api_route)
    host.add_ai_route(code_route)
    host.add_settings_section("ai", "Claude", section)
    host.add_entry_point("hook", hook.main)
