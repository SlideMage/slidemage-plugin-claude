# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""The public route contract, cheap registration and host-owned services."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from types import SimpleNamespace

import pytest

from claude import activate
from claude.code import hook, launch
from claude.credentials import ApiCredentials
from fake_host import FakeHost
from slidemage.plugin_api import Route


@pytest.fixture
def host(tmp_path):
    return FakeHost(tmp_path)


def test_activate_registers_routes_one_combined_section_and_hook(host):
    activate(host)
    host.active = False
    assert list(host.routes) == ["anthropic_api", "claude_code"]
    assert [(p, title) for p, title, _ in host.sections] == [("ai", "Claude")]
    build = host.sections[0][2]
    for route, service in zip(host.routes.values(), ("Anthropic API", "Claude Code")):
        assert route.service == service and route.is_local is False
        assert route.tasks == {"chat", "translation", "image_description", "fixes_notes_transcripts"}
        assert route.settings_section() is None
    assert host.entry_points == {"hook": hook.main}
    assert host.secret.env_var == "ANTHROPIC_API_KEY"
    assert not host.terminals and not host.watches and not host.tool_calls
    assert host.secret.reads == 0


def test_activate_has_no_network_or_slow_work(host, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("activate attempted I/O, a CLI probe, widgets or a heavy host service")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(launch, "find_claude", forbidden)
    monkeypatch.setattr(launch, "signed_in", forbidden)
    monkeypatch.setattr(host.secret, "get", forbidden)
    for name in ("terminal", "ai_tools", "watch_external_edits", "run_in_background", "Page"):
        monkeypatch.setattr(host, name, forbidden)
    activate(host)


def test_activation_in_a_fresh_process_does_not_load_qt_or_providers():
    result = subprocess.run([sys.executable, "-c", """
import sys
from tempfile import TemporaryDirectory
from pathlib import Path
from fake_host import FakeHost
from slidemage.plugin_api import Route
from claude import activate
with TemporaryDirectory() as folder:
    activate(FakeHost(Path(folder)))
assert not any(n.startswith('PySide6') for n in sys.modules)
assert 'claude.api.provider' not in sys.modules
assert 'claude.code.runner' not in sys.modules
assert 'claude.code.terminal.session' not in sys.modules
"""], env={**os.environ, "PYTHONPATH": os.pathsep.join(["tests", ".", os.environ.get("PYTHONPATH", "")])},
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_route_problems_and_static_choices(host, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("claude.credentials._legacy_key", lambda ctx=None: None)
    monkeypatch.setattr(launch, "find_claude", lambda: None)
    activate(host)
    api, code = host.routes.values()
    assert api.problem(None, Route("anthropic_api", "chat")).startswith("No Anthropic API key yet")
    assert api.model_choices(None, "chat") == []
    assert "conversation is the terminal" in code.problem(None, Route("claude_code", "chat"))
    assert code.problem(None, Route("claude_code", "translation")) == ""
    assert code.provider(None, Route("claude_code", "chat")) is None
    assert api.chat_surface() is None and api.task_runner(None, Route("anthropic_api", "chat")) is None
    assert api.draft_backend(None, Route("anthropic_api", "chat")) is None
    assert api.translation_backend(None, Route("anthropic_api", "chat")) is None
    assert api.split_choice("custom") == ("custom", None) and api.valid_choice(None, "custom")
    assert not api.valid_choice(None, "")
    assert api.work_label(Route("anthropic_api", "chat", "custom")) == "custom · API"
    assert code.split_choice("opus:high") == ("opus", "high")
    assert code.valid_choice(None, "opus:high") and not code.valid_choice(None, "opus:invalid")
    assert code.work_label(Route("claude_code", "chat")) == "Claude Code · terminal"
    assert code.work_label(Route("claude_code", "translation", "opus", "high")) == "Claude Code · Opus · effort high"
    assert code.default_choice("chat") == "" and code.default_choice("translation") == "haiku:medium"
    assert code.choice_label("haiku:medium") == "Haiku · medium"
    assert len(code.model_choices(None, "chat")) == 9
    host.secret.set("sk-host")
    assert api.problem(None, Route("anthropic_api", "chat")) == ""
    assert api.default_choice("chat") in api.model_choices(None, "chat")
    provider = api.provider(None, SimpleNamespace(model="chosen-model", task="chat"))
    assert provider.model == "chosen-model" and provider._api_key == "sk-host"
    from slidemage.plugin_api import ProviderError
    with pytest.raises(ProviderError, match="not installed"):
        code.task_runner(None, SimpleNamespace(model="haiku", effort="medium"))


def test_legacy_credentials_use_host_migration_and_clear_never_resurrects(host, monkeypatch):
    from slidemage.plugins import migrate
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = []
    monkeypatch.setattr(migrate, "legacy_anthropic_key", lambda ctx: calls.append(ctx) or "sk-old")
    credentials = ApiCredentials(host)
    ctx = object()
    assert credentials.get(ctx).value == "sk-old" and calls == [ctx]
    host.secret.set("sk-new")
    assert credentials.get(ctx).value == "sk-new" and calls == [ctx]
    credentials.set("")
    assert ApiCredentials(host).get(ctx) is None and calls == [ctx]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    assert credentials.get(ctx).value == "sk-env"


def test_code_task_runner_and_backends_keep_the_selected_model(host, monkeypatch):
    from claude.code import runner, images
    monkeypatch.setattr(launch, "find_claude", lambda: host.root / "claude")
    calls = []
    monkeypatch.setattr(runner, "run_task", lambda *args, **kw: calls.append((args, kw)))
    activate(host)
    code = host.routes["claude_code"]
    ctx = SimpleNamespace(root=host.root)
    route = SimpleNamespace(model="opus", effort="high", task="translation")
    import threading
    cancel = threading.Event()
    span = (2, 9)
    code.task_runner(ctx, route)("task", "captured", "request", cancel, span)
    assert calls == [((ctx, host.root / "claude", "task", "captured", "request", "opus", "high"), {"cancel": cancel, "span": span})]
    assert code.draft_backend(ctx, route, cancel).cancel is cancel
    assert isinstance(code.draft_backend(ctx, route), images.ClaudeDraftBackend)
    assert code.translation_backend(ctx, route, cancel).cancel is cancel
    assert isinstance(code.translation_backend(ctx, route), images.ClaudeTranslationBackend)
    translator = code.slide_translator(ctx, route)
    assert translator.model == "opus" and translator.effort == "high"


def test_terminal_surface_uses_host_services_and_guards_late_callbacks(qapp, host, monkeypatch):
    from claude.code.terminal import session as module
    monkeypatch.setattr(launch, "find_claude", lambda: host.root / "claude")
    monkeypatch.setattr(launch, "has_transcript", lambda _: True)
    class Server:
        url, token = "http://localhost:1/mcp", "secret"
        def __init__(self, toolbox): self.toolbox = toolbox
        def start(self): pass
        def stop(self): pass
    monkeypatch.setattr(module, "McpServer", Server)
    activate(host)
    changes = []
    surface = module.ClaudeCodeSession(host, SimpleNamespace(root=host.root), host.root / "claude",
                                       choice="sonnet:high", on_change=changes.append)
    try:
        assert not host.terminals
        surface.start(with_widget=False)
        first = host.terminals[-1]
        assert first.cwd == host.root and first.env[launch.TOKEN_ENV] == "secret"
        assert host.watches[0].running and host.tool_calls
        event = SimpleNamespace(added=(), modified=(host.root / "slide.tex",), removed=())
        host.watches[0].on_change(event)
        assert changes == [event]
        assert surface._server.toolbox() is surface._box
        host.current_focus.scope = "deck"
        surface.publish_focus()
        from claude.code.scope import load
        assert load(surface._focus_file)["scope"] == "deck"
        assert host.tool_calls[-1][0] == "deck"
        kept = surface.session_id
        surface.restart("opus:medium", True)
        assert first.closed and surface.session_id == kept
        command = host.terminals[-1].argv
        assert command[command.index("--model") + 1] == "opus"
        assert "--resume" in command
        settings = json.loads(command[command.index("--settings") + 1])
        assert "claude:hook" in settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        output = []
        surface.output.connect(output.append)
        first.options["on_output"](b"late")
        first.options["on_exit"](1)
        assert not output and host.watches[0].running
        host.terminals[-1].options["on_output"](b"current")
        assert output == [b"current"]
        surface.stop()
        surface.stop()
        assert not surface.running and not host.watches[0].running
    finally:
        surface.shutdown()
    assert surface._focus_file is None and surface._server is None


def test_settings_builder_saves_key_and_checks_auth_off_activation(qapp, host, monkeypatch):
    from PySide6.QtWidgets import QLineEdit, QPushButton, QLabel
    monkeypatch.setattr("claude.credentials._legacy_key", lambda ctx=None: None)
    monkeypatch.setattr(launch, "find_claude", lambda: None)
    activate(host)
    page = host.sections[0][2]()
    try:
        assert any("not installed" in label.text() for label in page.findChildren(QLabel))
        page.findChild(QLineEdit).setText("sk-saved")
        next(button for button in page.findChildren(QPushButton) if button.text() == "Save key").click()
        assert host.secret.values["key"] == "sk-saved"
    finally:
        page.close()


def test_fake_host_exposes_real_host_methods():
    from inspect import isfunction
    from slidemage.plugin_api import Host
    assert {name for name, value in vars(Host).items() if isfunction(value) and not name.startswith("_")} <= set(dir(FakeHost))


def test_surface_start_failure_stops_watch_and_can_be_retried(qapp, host, monkeypatch):
    from claude.code.terminal import session as module
    class Server:
        url, token = "http://localhost:1/mcp", "t"
        def __init__(self, toolbox): pass
        def start(self): pass
        def stop(self): pass
    monkeypatch.setattr(module, "McpServer", Server)
    surface = module.ClaudeCodeSession(host, SimpleNamespace(root=host.root), host.root / "claude",
                                       on_change=lambda _: None)
    start = host.start
    def fail(*args, **kwargs):
        raise OSError("cannot start")
    monkeypatch.setattr(host, "start", fail)
    try:
        with pytest.raises(OSError, match="cannot start"):
            surface.start(with_widget=False)
        assert not host.watches[0].running and not surface.running
        monkeypatch.setattr(host, "start", start)
        surface.start(with_widget=False)
        assert surface.running and host.watches[0].running
        host.terminals[-1].options["on_exit"](0)
        assert not host.watches[0].running
    finally:
        surface.shutdown()
