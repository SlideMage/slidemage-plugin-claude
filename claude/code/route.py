# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""DRAFT 3a/3b: Claude Code tasks (-p) and its terminal chat surface."""
from __future__ import annotations

from typing import Any, Callable

from claude.api.route import TASKS
from claude.host import Host, Widget

NO_CLAUDE = "Claude Code is not installed on this computer, so nothing was sent and no other model is used."
MODELS = ("sonnet", "haiku", "opus")
EFFORTS = ("low", "medium", "high")


class ClaudeCodeRoute:
    id = "claude_code"
    service = "Claude Code"
    is_local = False
    tasks = TASKS
    provider = None  # the conversation is a terminal; tasks run through claude -p

    def __init__(self, host: Host, settings_section: Callable[[], Widget]) -> None:
        self.host, self.settings_section = host, settings_section

    def problem(self, ctx: Any, task: str) -> str:
        from claude.code.launch import find_claude
        return "" if find_claude() is not None else NO_CLAUDE

    def model_choices(self, ctx: Any, task: str) -> list[str]:
        return [f"{model}:{effort}" for model in MODELS for effort in EFFORTS]

    def default_choice(self, task: str) -> str:
        return "" if task == "chat" else "haiku:medium"

    def choice_label(self, choice: str) -> str:
        model, _, effort = choice.partition(":")
        return f"{model.capitalize()} · {effort}" if model else "Claude Code default"

    @staticmethod
    def _claude():
        from slidemage.plugin_api import ProviderError
        from claude.code.launch import find_claude
        path = find_claude()
        if path is None:
            raise ProviderError(NO_CLAUDE)
        return path

    def task_runner(self, ctx: Any, route: Any):
        # DRAFT 3a/3b: callable on a worker, with the captured model/effort.
        from functools import partial
        from claude.code.runner import run_task
        return partial(run_task, ctx, self._claude(), model=route.model, effort=route.effort)

    def draft_backend(self, ctx: Any, route: Any):
        from claude.code.images import ClaudeDraftBackend
        return ClaudeDraftBackend(ctx, self._claude(), route.model, route.effort)

    def translation_backend(self, ctx: Any, route: Any):
        from claude.code.images import ClaudeTranslationBackend
        return ClaudeTranslationBackend(ctx, self._claude(), route.model, route.effort)

    def slide_translator(self, ctx: Any, route: Any):
        from claude.code.runner import SlideTranslator
        return SlideTranslator(ctx, self._claude(), route.model, route.effort)

    def chat_surface(self, ctx: Any, route: Any, *, on_change, workspace=None, parent=None):
        """DRAFT: core attaches session.widget, applies edits and owns the task UI (3b).

        Construction does not start the CLI; call start() when the surface is shown.
        """
        from claude.code.terminal.session import ClaudeCodeSession
        choice = f"{route.model}:{route.effort}" if route.model else ""
        return ClaudeCodeSession(self.host, ctx, self._claude(), choice=choice,
                                 on_change=on_change, workspace=workspace, parent=parent)
