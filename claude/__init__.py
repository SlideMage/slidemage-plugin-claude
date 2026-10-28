# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Claude Code and the Anthropic API as SlideMage's cloud AI: a SlideMage plugin. SlideMage imports this package and calls activate() once at start."""


def activate(host) -> None:
    """Register the plugin's routes, settings section and entry point with SlideMage through host (step 6b of docs/PLAN.md)."""
