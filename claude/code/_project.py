# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bridge until the public task and prompt helpers accept RouteContext directly."""
from pathlib import Path


class ProjectForHelpers:
    def __init__(self, root: Path):
        self.root = root
        self.settings_dir = root / ".slidemage"
        self.bibliography_path = root / "Slidemaster.bib"


def project_for_helpers(ctx):
    # Older callers already have the project object; routes receive RouteContext.
    return ctx if hasattr(ctx, "settings_dir") else ProjectForHelpers(ctx.root)
