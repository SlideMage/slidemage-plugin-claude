# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""The exact host subset Claude uses, drafted against PLUGINS_REMAINING_PLAN §3.

3d service signatures match feature/ai-host-services. Only the route registry,
AiRoute and settings section are DRAFT (3a/3c). No Qt or lazy AI types load here.
Registration happens in activate(); network, subprocesses and widgets wait for use.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeVar

if TYPE_CHECKING:
    from slidemage.plugin_api import Credentials, EditWatch, ExternalEdits, Focus, TerminalService, ToolBox, Settings

T = TypeVar("T")
Widget = Any


class ChatSurface(Protocol):
    """DRAFT 3a/3b: a terminal session with the Switch-now lifecycle and a host widget."""
    widget: Widget | None

    def start(self, cols: int = 80, rows: int = 24, *, resume: bool = False, with_widget: bool = True) -> None: ...
    def shutdown(self) -> None: ...
    def stop(self) -> None: ...
    def restart(self, choice: str, continue_conversation: bool) -> None: ...


class AiRoute(Protocol):
    """DRAFT 3a: names and shape from the plan; ctx/selection/backend types await core.

    A selection is today's captured Route (model, effort). None for provider or
    task_runner selects core's default implementation. Model choices are local,
    fast reads only. chat_surface receives the core's external-edit callback;
    workspace is core's GUI-aware tool workspace (3b), if present.
    """
    id: str
    service: str
    is_local: bool
    tasks: frozenset[str]
    provider: Callable[[Any, Any], Any] | None
    draft_backend: Callable[[Any, Any], Any]
    translation_backend: Callable[[Any, Any], Any]
    slide_translator: Callable[[Any, Any], Any] | None
    task_runner: Callable[[Any, Any], Any] | None
    chat_surface: Callable[..., ChatSurface] | None
    settings_section: Callable[[], Widget]

    def problem(self, ctx: Any, task: str) -> str: ...
    def model_choices(self, ctx: Any, task: str) -> list[str]: ...
    def default_choice(self, task: str) -> str: ...
    def choice_label(self, choice: str) -> str: ...


class Host(Protocol):
    """Only calls this plugin needs. Unmarked calls already exist in 3d."""

    def settings(self) -> Settings: ...

    def add_ai_route(self, route: AiRoute) -> None:
        """DRAFT 3a: register a route during activate()."""
        ...

    def add_settings_section(self, page: Literal["ai"], title: str, build: Callable[[], Widget]) -> None:
        """DRAFT 3c: one combined Claude section; build/save lifecycle awaits 3c."""
        ...

    def add_entry_point(self, name: str, fn: Callable[[list[str]], int]) -> None: ...
    def entry_point_command(self, name: str) -> list[str]: ...
    def terminal(self) -> TerminalService: ...
    def watch_external_edits(self, on_change: Callable[[ExternalEdits], None]) -> EditWatch: ...
    def credentials(self, env_var: str | None = None) -> Credentials: ...

    def ai_tools(
        self, scope: Literal["slide", "deck"] = "slide", *, focus_slide: Path | None = None,
        mode: Literal["ask", "auto"] = "auto", cancel: Any = None, workspace: Any = None,
    ) -> ToolBox: ...

    def focus(self) -> Focus: ...
    def run_in_background(self, work: Callable[[], T], done: Callable[[T | None, BaseException | None], None]) -> None: ...
    def Page(self) -> Widget: ...
    def Field(self, label: str, widget: Widget) -> Widget: ...
    def caption(self, text: str, tone: Literal["", "error"] = "") -> Widget: ...
