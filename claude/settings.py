# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""DRAFT 3c: combined AI settings section, built only when settings is opened.

An explicit Save key button avoids assuming the unfinished section/save contract.
Claude Code auth status is checked on a worker, never during activate().
"""
from __future__ import annotations

from claude.credentials import ApiCredentials
from claude.host import Host


def build(host: Host, credentials: ApiCredentials):
    from PySide6.QtWidgets import QLineEdit, QPushButton
    from claude.code.launch import find_claude, signed_in

    page = host.Page()
    key = QLineEdit()
    key.setEchoMode(QLineEdit.EchoMode.Password)
    key.setPlaceholderText("Anthropic API key")
    # The environment is read-only; don't put its value into a savable field.
    stored = credentials.get()
    if stored and stored.source != "environment":
        key.setText(stored.value)
    page.body.addWidget(host.Field("Anthropic API key", key))
    source = host.caption(f"Key source: {stored.source}" if stored else "No Anthropic API key yet.")
    page.body.addWidget(source)
    save = QPushButton("Save key")
    page.body.addWidget(save)

    def save_key():
        try:
            where = credentials.set(key.text())
        except OSError as exc:
            source.setText(f"Could not save the key: {exc}")
            return
        source.setText(f"Saved in {where}." if where else "Stored key cleared; an environment key still takes precedence.")
        page.changed.emit()
    save.clicked.connect(save_key)

    status = host.caption("")
    page.body.addWidget(status)
    check = QPushButton("Check Claude Code status")
    page.body.addWidget(check)
    closed = [False]
    page.destroyed.connect(lambda: closed.__setitem__(0, True))

    def check_status():
        claude = find_claude()
        if claude is None:
            status.setText("Claude Code is not installed on this computer.")
            return
        status.setText(f"Claude Code found: {claude}. Checking sign-in…")
        check.setEnabled(False)

        def done(answer, error):
            if closed[0]:
                return
            check.setEnabled(True)
            status.setText("Claude Code is signed in." if answer is True else
                           "Claude Code is not signed in. Run claude in a terminal and sign in with /login."
                           if answer is False else "Claude Code sign-in status could not be checked.")
        host.run_in_background(lambda: signed_in(claude), done)
    check.clicked.connect(check_status)
    check_status()
    return page
