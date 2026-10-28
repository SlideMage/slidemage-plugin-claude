# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Anthropic's API route; the host supplies credentials and core wraps the provider."""
from __future__ import annotations

from typing import Any

from slidemage.plugin_api import Host, Route
from claude.credentials import ApiCredentials

TASKS = frozenset({"chat", "image_description", "translation", "fixes_notes_transcripts"})
NO_KEY = "No Anthropic API key yet. Add one under Settings → AI → Claude."


class AnthropicApiRoute:
    id = "anthropic_api"
    service = "Anthropic API"
    is_local = False
    tasks = TASKS

    def __init__(self, host: Host, credentials: ApiCredentials) -> None:
        self.host, self.credentials = host, credentials

    def problem(self, ctx: Any, route: Route) -> str:
        return "" if self.credentials.get(ctx) else NO_KEY

    def model_choices(self, ctx: Any, task: str) -> list[str]:
        if not self.credentials.get(ctx):
            return []
        from claude.api.provider import ANTHROPIC_FALLBACK_MODELS
        return list(ANTHROPIC_FALLBACK_MODELS)

    def default_choice(self, task: str) -> str:
        return "claude-sonnet-5-5"

    def choice_label(self, choice: str) -> str:
        return choice

    def split_choice(self, choice: str) -> tuple[str, str | None]:
        return choice, None

    def valid_choice(self, ctx: Any, choice: str) -> bool:
        return bool(choice)

    def work_label(self, route: Route) -> str:
        return f"{route.model or 'no model chosen'} · API"

    def provider(self, ctx: Any, route: Route):
        from slidemage.plugin_api import ProviderError
        from claude.api.provider import AnthropicProvider
        key = self.credentials.get(ctx)
        if key is None:
            raise ProviderError(NO_KEY)
        return AnthropicProvider(route.model or self.default_choice(route.task), key.value)

    def draft_backend(self, ctx: Any, route: Route, cancel=None):
        return None

    def translation_backend(self, ctx: Any, route: Route, cancel=None):
        return None

    def slide_translator(self, ctx: Any, route: Route):
        return None

    def task_runner(self, ctx: Any, route: Route):
        return None

    def chat_surface(self, *args: Any, **kwargs: Any):
        return None

    def settings_section(self):
        return None  # registered once for both routes with add_settings_section
