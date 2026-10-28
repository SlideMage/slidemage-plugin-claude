# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""The plugin tests need SlideMage's own test
support: the example project, the Qt application, the fixtures that isolate settings and caches, and the helpers
`fake_http` and `agent_fakes`. They come from SlideMage's tests folder: $SLIDEMAGE_TESTS, or ../SlideMage/tests."""
import importlib.util
import os
import sys
from pathlib import Path

_CORE_TESTS = Path(os.environ.get("SLIDEMAGE_TESTS") or Path(__file__).resolve().parents[2] / "SlideMage" / "tests")
sys.path.append(str(_CORE_TESTS))        # last, so this folder's own modules win

_spec = importlib.util.spec_from_file_location("slidemage_core_conftest", _CORE_TESTS / "conftest.py")
_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)
# pytest finds fixtures and hooks as attributes of the conftest module; the tests import helpers from it too
globals().update({name: value for name, value in vars(_core).items() if not name.startswith("__")})
