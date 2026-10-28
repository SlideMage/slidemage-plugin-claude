# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Claude's MCP server, focus file and host terminal/watch lifecycle.

DRAFT 3a/3b: core supplies ctx, a GUI-aware workspace and on_change to apply edits
(reload/conflicts/deck rescans). 3d's watch reports changes; it does not apply them.
The host terminal owns the pty, widget, thread delivery and stale-output guard.
"""
from __future__ import annotations

import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QTimer, Signal

from slidemage import compiler  # DRAFT: CancelToken is not exported yet (3a).
from slidemage.plugin_api import ExternalEdits, ToolBox
from claude.host import Host
from claude.code import launch, scope
from claude.code.mcp_server import McpServer


class ClaudeCodeSession(QObject):
    output = Signal(bytes)
    exited = Signal(int)
    focus_changed = Signal()

    def __init__(self, host: Host, ctx: Any, claude: Path, *, on_change: Callable[[ExternalEdits], None],
                 choice: str = "", workspace: Any = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.host, self.ctx, self.claude = host, ctx, claude
        self.choice, self.workspace = choice, workspace
        self.scope = host.focus().scope
        self._scope_override = None
        self.model, _, effort = choice.partition(":")
        self.effort = effort or None
        self.session_id = ""
        self._focus_file: Path | None = None
        self._published: tuple | None = None
        self._box: ToolBox | None = None
        self._server: McpServer | None = None
        self._terminal = None
        self._generation = 0
        self._lock = threading.Lock()
        self._cancel = compiler.CancelToken()
        self._sync = host.watch_external_edits(on_change)
        self._timer = QTimer(self)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self.publish_focus)

    @property
    def widget(self):
        return self._terminal.widget if self._terminal is not None else None

    @property
    def running(self) -> bool:
        return self._terminal is not None and self._terminal.running

    @property
    def mcp_url(self) -> str:
        return self._server.url if self._server is not None else ""

    def start(self, cols: int = 80, rows: int = 24, *, resume: bool = False, with_widget: bool = True) -> None:
        self.stop()
        if self._terminal is not None:
            self._terminal.close()
            self._terminal = None
        with self._lock:
            self._cancel = compiler.CancelToken()
        if self._server is None:
            server = McpServer(self._toolbox)
            server.start()
            self._server = server
        if self._focus_file is None:
            fd, name = tempfile.mkstemp(prefix="slidemage-focus-", suffix=".json")
            os.close(fd)
            self._focus_file = Path(name)
        self.publish_focus(force=True)
        resume = resume and launch.has_transcript(self.session_id)
        if not resume:
            self.session_id = str(uuid.uuid4())
        self.model, _, effort = self.choice.partition(":")
        self.effort = effort or None
        command = launch.build_command(self.claude, self._server.url, host=self.host, model=self.model,
                                       effort=self.effort, session_id=self.session_id, resume=resume)
        env = launch.environment(self._server.token, self.ctx.root, self.claude, focus_file=self._focus_file)
        generation = self._generation
        try:
            self._sync.start()
            self._terminal = self.host.terminal().start(
                command, env, self.ctx.root, on_output=lambda data: self._on_output(generation, data),
                on_exit=lambda code: self._on_exit(generation, code), with_widget=with_widget, cols=cols, rows=rows)
            self._timer.start()
        except Exception:
            self.stop()
            raise

    def restart(self, choice: str, continue_conversation: bool) -> None:
        """DRAFT chat_surface lifecycle; core reattaches widget after restart (3b)."""
        self.choice = choice
        self.start(resume=continue_conversation)

    def set_scope(self, value: str) -> None:
        if value not in (scope.SLIDE, scope.DECK):
            raise ValueError(value)
        self._scope_override = value
        self.scope = value
        self.publish_focus()

    def publish_focus(self, force: bool = False) -> None:
        if self._focus_file is None:
            return
        focus = self.host.focus()
        self.scope = self._scope_override or focus.scope
        slide = scope.slide_focus(self.ctx.root, focus.slide)
        # 3d Focus exposes deck/slide/scope only. Buffer dirty state, view and
        # language must be supplied by the future chat-surface contract (3b).
        values = (self.scope, None, slide, focus.deck, "", "", False)
        if values == self._published and not force:
            return
        try:
            scope.publish(self._focus_file, values[0], self.ctx.root, *values[1:])
        except OSError:
            return  # do not cache a failed write: retry at the next poll
        if self.workspace is None:
            self._box = self.host.ai_tools(self.scope, focus_slide=slide, mode="auto", cancel=self._cancel)
        self._published = values
        self.focus_changed.emit()

    def write(self, data: bytes) -> None:
        if self._terminal is not None:
            self._terminal.write(data)

    def resize(self, cols: int, rows: int) -> None:
        if self._terminal is not None:
            self._terminal.resize(cols, rows)

    def stop(self, *, last_look: bool = True) -> None:
        with self._lock:
            self._generation += 1
            cancel = self._cancel
        cancel.request_stop()
        self._timer.stop()
        # End the writer before the final poll, so its last changes are seen.
        if self._terminal is not None:
            self._terminal.stop()
        self._sync.stop(last_look=last_look)

    def shutdown(self) -> None:
        self.stop(last_look=False)
        if self._terminal is not None:
            self._terminal.close()
            self._terminal = None
        if self._server is not None:
            self._server.stop()
            self._server = None
        if self._focus_file is not None:
            self._focus_file.unlink(missing_ok=True)
            self._focus_file = None

    def _toolbox(self) -> ToolBox:
        with self._lock:
            cancel = self._cancel

        def build():
            self.workspace.begin_request()
            path = self.workspace.context().path
            return self.host.ai_tools(self.scope, focus_slide=scope.slide_focus(self.ctx.root, path),
                                      mode="auto", cancel=cancel, workspace=self.workspace)

        # MCP workers must read focus and construct the toolbox on the GUI thread.
        # Core supplies this workspace in 3b, as today's embedded terminal does.
        if self.workspace is not None:
            return self.workspace.on_gui(build, None)
        if self._box is None:
            raise RuntimeError("Start the Claude Code surface before using its tools")
        return self._box

    def _on_output(self, generation: int, data: bytes) -> None:
        if generation == self._generation:
            self.output.emit(data)

    def _on_exit(self, generation: int, code: int) -> None:
        if generation == self._generation:
            self._timer.stop()
            self._sync.stop()
            self.exited.emit(code)
