# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""DRAFT 3a: the cloud Anthropic route, with lazy provider/backend imports."""
from __future__ import annotations

from typing import Any, Callable

from claude.credentials import ApiCredentials
from claude.host import Host, Widget

TASKS = frozenset({"chat", "image_description", "translation", "fixes_notes_transcripts"})
NO_KEY = "No Anthropic API key yet. Add one under Settings → AI → Claude."


class AnthropicApiRoute:
    id = "anthropic_api"
    service = "Anthropic API"
    is_local = False
    tasks = TASKS
    slide_translator = None  # core wraps provider (3a)
    task_runner = None       # core's provider_tasks (3a/3b)
    chat_surface = None      # core's chat view

    def __init__(self, host: Host, credentials: ApiCredentials, settings_section: Callable[[], Widget]) -> None:
        self.host, self.credentials, self.settings_section = host, credentials, settings_section

    def problem(self, ctx: Any, task: str) -> str:
        return "" if self.credentials.get(ctx) else NO_KEY

    def model_choices(self, ctx: Any, task: str) -> list[str]:
        # Same static fallback list as today; opening a picker never queries /v1/models.
        if not self.credentials.get(ctx):
            return []
        from claude.api.provider import ANTHROPIC_FALLBACK_MODELS
        return list(ANTHROPIC_FALLBACK_MODELS)

    def default_choice(self, task: str) -> str:
        return "claude-sonnet-5-5"

    def choice_label(self, choice: str) -> str:
        return choice

    def provider(self, ctx: Any, route: Any):
        from slidemage.plugin_api import ProviderError
        from claude.api.provider import AnthropicProvider
        key = self.credentials.get(ctx)
        if key is None:
            raise ProviderError(NO_KEY)
        return AnthropicProvider(route.model or self.default_choice(route.task), key.value)

    def draft_backend(self, ctx: Any, route: Any):
        # DRAFT: image backend protocols/wrappers are not exported yet (3a).
        from slidemage.alt_draft import ModelBackend
        return ModelBackend(ctx, self.provider(ctx, route))

    def translation_backend(self, ctx: Any, route: Any):
        from slidemage.alt_draft import ModelTranslationBackend
        return ModelTranslationBackend(ctx, self.provider(ctx, route))
