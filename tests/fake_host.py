# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recorded DRAFT registrations and 3d services; no network, Qt, keychain or CLI."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace


class FakeSettings:
    def __init__(self):
        self.data = {}
        self.saved = 0

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        self.saved += 1


class FakeCredentials:
    def __init__(self):
        self.env_var = None
        self.values = {}
        self.reads = 0

    def get(self, name="key"):
        self.reads += 1
        value = os.environ.get(self.env_var, "").strip() if self.env_var and name == "key" else ""
        return value or self.values.get(name)

    def where(self, name="key"):
        if self.env_var and name == "key" and os.environ.get(self.env_var, "").strip():
            return "environment"
        return "file" if self.values.get(name) else ""

    def set(self, value, name="key"):
        if value.strip():
            self.values[name] = value.strip()
            return "file"
        self.values.pop(name, None)
        return ""

    def clear(self, name="key"):
        self.set("", name)


class FakeWatch:
    def __init__(self, on_change):
        self.on_change = on_change
        self.running = False
        self.stops = []

    def start(self):
        self.running = True

    def stop(self, *, last_look=True):
        self.stops.append(last_look)
        self.running = False

    def emit(self, **changes):
        self.on_change(SimpleNamespace(**{"added": (), "removed": (), "modified": (), **changes}))


class FakeTerminal:
    def __init__(self, argv, env, cwd, **options):
        self.argv, self.env, self.cwd, self.options = argv, env, cwd, options
        self.running = True
        self.widget = object() if options.get("with_widget", True) else None
        self.writes = []
        self.closed = False

    def write(self, data):
        self.writes.append(data)

    def resize(self, cols, rows):
        self.size = (cols, rows)

    def stop(self):
        self.running = False

    def close(self):
        self.stop()
        self.closed, self.widget = True, None


class FakeHost:
    def __init__(self, root: Path):
        self.root = root
        self.routes, self.sections, self.entry_points = {}, [], {}
        self.secret = FakeCredentials()
        self.store = FakeSettings()
        self.terminals, self.watches, self.tool_calls = [], [], []
        self.current_focus = SimpleNamespace(deck=None, slide=None, scope="slide")
        self.active = True
        self.argv = [sys.executable, "-m", "slidemage", "--plugin", "claude:hook"]

    def _register(self):
        if not self.active:
            raise RuntimeError("registrations are only allowed in activate()")

    def add_ai_route(self, route):
        self._register()
        if route.id in self.routes:
            raise ValueError(route.id)
        self.routes[route.id] = route

    def add_settings_section(self, page, title, build):
        self._register()
        self.sections.append((page, title, build))

    def add_entry_point(self, name, fn):
        self._register()
        if name in self.entry_points:
            raise ValueError(name)
        self.entry_points[name] = fn

    def entry_point_command(self, name):
        assert name == "hook"
        return list(self.argv)

    def credentials(self, env_var=None):
        self.secret.env_var = env_var
        return self.secret

    def settings(self):
        return self.store

    def terminal(self):
        return self

    def start(self, argv, env=None, cwd=None, *, on_output=None, on_exit=None,
              with_widget=True, cols=80, rows=24):
        terminal = FakeTerminal(argv, env, cwd, on_output=on_output, on_exit=on_exit,
                                with_widget=with_widget, cols=cols, rows=rows)
        self.terminals.append(terminal)
        return terminal

    def watch_external_edits(self, on_change):
        watch = FakeWatch(on_change)
        self.watches.append(watch)
        return watch

    def ai_tools(self, scope="slide", *, focus_slide=None, mode="auto", cancel=None, workspace=None):
        self.tool_calls.append((scope, focus_slide, mode, cancel, workspace))
        return SimpleNamespace(specs=[], execute=lambda call: None)

    def focus(self):
        return self.current_focus

    def run_in_background(self, work, done):
        try:
            result = work()
        except BaseException as error:
            done(None, error)
        else:
            done(result, None)

    def Page(self):
        from PySide6.QtCore import Signal
        from PySide6.QtWidgets import QWidget, QVBoxLayout

        class Page(QWidget):
            changed = Signal()

            def __init__(self):
                super().__init__()
                self.body = QVBoxLayout(self)
        return Page()

    def Field(self, label, widget):
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
        field = QWidget()
        layout = QVBoxLayout(field)
        layout.addWidget(QLabel(label))
        layout.addWidget(widget)
        return field

    def caption(self, text, tone=""):
        from PySide6.QtWidgets import QLabel
        return QLabel(text)
