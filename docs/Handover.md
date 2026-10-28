# Claude plugin: handover

Step 6b of [PLAN.md](PLAN.md) is implemented as a **DRAFT** against the planned SlideMage AI route API.
The host-service adaptation is real; route registration and settings-section registration remain planned APIs.
Do not release/install it against `feature/ai-host-services` alone.

## Repository and contract sources

- Work only in `/home/juergen/github/slidemage-plugin-claude`, branch `plugin-claude`; no remote/push, branch switch or stash.
  SlideMage and all its worktrees remain read-only. The plugin history is independent; never merge it into SlideMage.
- Plan: SlideMage `feature/ai-routes` at `38ea44c`, `docs/PLUGINS_REMAINING_PLAN.md` §3a–3d.
- Implemented services: `feature/ai-host-services` at `387467d`, including `plugin_api`, host, credentials, migration,
  entry-point dispatch and terminal/watch services. Draft-host precedent: CampusOnline `9d5a6b9`.
- Local `.git` is read-only in this environment. `git add` failed on `.git/index.lock`, so the working files are updated
  but no commits can be installed in this repository. Logical commits with the requested co-author trailer are prepared
  in a writable temporary Git copy and exported in `/tmp/claude-6b-commits/`. The original branch/history are unchanged.

## What changed in 6b

```
claude/host.py                minimal Host Protocol: exact existing 3d signatures + DRAFT AiRoute/ChatSurface/registrations
claude/__init__.py            two routes, one combined AI settings section, hook entry point
claude/api/route.py           anthropic_api / Anthropic API (cloud), static choices, missing-key problem
claude/code/route.py          claude_code / Claude Code (cloud), claude -p task runner, host terminal session
claude/settings.py            lazy key editor/Save + install/auth status (auth check on a host background worker)
claude/credentials.py         host secrets, lazy core migration fallback, persisted suppression after Save/clear
claude/api/provider.py        neutral types from plugin_api; route injects the host key
claude/api/_http.py           copied unexported HTTP/socket/media/error helpers, provenance comment
claude/_files.py              small atomic JSON helper (scope publication)
claude/_processes.py          Windows no-console subprocess helper
claude/code/launch.py         host.entry_point_command('hook'), no legacy hook flag/module or guessed PYTHONPATH
claude/code/hook.py           entry-point argv signature; protected_spans from plugin_api
claude/code/mcp_server.py     neutral ToolCall/ToolBox from plugin_api
claude/code/runner.py         plugin-owned subprocess helper; task/style types still wait for public exports
claude/code/scope.py          plugin-owned atomic JSON writer
claude/code/terminal/session.py host terminal, edit watch, focus, toolbox, stop/restart/shutdown
claude/code/terminal/view.py  retained DRAFT UI using host terminal/background work; core UI integration waits for 3b
tests/fake_host.py           registrations, secrets/settings, terminal/watch/toolbox fakes
tests/test_activate.py       registration/no-network/import/signature/settings/credentials/task/session checks
tests/test_claude_{launch,scope,hook}.py  adapted to moved hook and host services
tests/test_claude_code_gui.py  direct-session toolbox test uses host + injected GUI workspace
```

`activate()` obtains a credential/settings handle and registers callbacks. It does not read a keychain, construct widgets,
load providers/runners, start a terminal or run `claude auth status`. Legacy key lookup happens on first use through core's
existing `legacy_anthropic_key(ctx)`, which reads the original places without modifying them. The helper has no public
host/plugin_api entry yet, so it is an explicit remaining private dependency. Host secret storage takes precedence; after
an explicit Save/clear the plugin settings marker prevents an old built-in key from reappearing. Environment keys still win.

The Claude Code route returns a session with `stop()` and `restart(choice, continue_conversation)`; construction does not
start Claude. `start()` creates the terminal and `widget`; restart replaces that widget and only resumes an existing
transcript. The core must attach the widget and supply edit handling and (for live editor tools) a GUI-aware workspace.
The host watch reports changes; it does not itself reload buffers or resolve conflicts. Stop invalidates late callbacks,
ends the process and takes the watch's last look; shutdown also releases MCP and the temporary focus file.

## What still waits

The exact **27 remaining core-import violations**, grouped by file with their waits, are in
[PLAN.md](PLAN.md#remaining-imports--waits-for-3a3b-and-the-explicit-3d-export-gaps). The checker is unchanged; `keyring` is gone.

- **3a:** actual AiRoute/selection/task/image backend contracts and neutral context/cancellation exports. Route ids and
  old stored-setting aliases are core work.
- **3b:** registry-aware workspace UI, task bubbles, setup/attachment/draft-restoration integration, external-edit callback,
  GUI-aware workspace and rich focus metadata (dirty buffer, view, language). Current core GUI tests still build core's view.
- **3c:** real `add_settings_section` and final builder/save/shared-section semantics. The draft uses an explicit Save key button.
- **3d follow-up:** public legacy-key migration; decide public review/sidecar/classification/permission metadata and the
  other unexported helpers listed in PLAN. They are not silently assumed to have public APIs.
- **7:** SlideMage removes its built-in Claude copies and wires only plugin routes. That repository was not modified here.
- **6c:** release assets, public repository, catalogue, changelog date/tag; `requires_slidemage >=10.0` stays provisional.

`add_ai_route` and `add_settings_section` do not exist in the inspected 3d Host. The draft intentionally calls the plan's
names; it does not hide that gap with `getattr` or register nothing on an older host.

## Running and interpreting the tests

From this repository:

```sh
SLIDEMAGE_TESTS=/home/juergen/github/SlideMage/tests \
PYTHONPATH=/home/juergen/github/SlideMage/.worktrees/ai-host-services/src:. \
QT_QPA_PLATFORM=offscreen \
/home/juergen/github/SlideMage/.venv/bin/python -m pytest -q
python3 build.py --check
```

`tests/conftest.py` still borrows SlideMage's test fixtures and adds its test support for `fake_http`/`agent_fakes`.
The application imports come from the **ai-host-services worktree**, not the main checkout. This is still a draft harness,
not a claim that all tests run without SlideMage. FakeHost starts no network, Qt, keychain or subprocess services by itself.

Results on 2026-10-28 in this restricted sandbox:

| Check | Result |
|---|---|
| Offline selection below | **89 passed** |
| `pytest -q --ignore=tests/test_claude_code_gui.py` | **112 passed, 3 failed, 29 errors**; all 32 non-passes fail creating local HTTP sockets (`PermissionError: Operation not permitted`) |
| Full `pytest -q` | Process exits **133 / Trace/breakpoint trap** at the Qt/WebEngine GUI module, before a pytest report |
| `python3 build.py --check` | Exits **1** with **27 core-import violations** (PLAN inventory) |
| `python3 -m compileall -q claude tests`, `git diff --check` | Pass |

Offline selection: `pytest -q tests/test_activate.py tests/test_claude_launch.py tests/test_claude_scope.py
tests/test_claude_hook.py tests/test_claude_runner.py tests/test_claude_images.py tests/test_terminal_draft.py`, using
that same environment. All new draft-host tests pass, including fresh-process activation without Qt/providers, exact 3d
parameter signatures, legacy-key lookup/clear, selected task models, terminal restart/transcripts, late callback guards,
watch delivery and failed-start cleanup/retry. API streaming and MCP HTTP tests need loopback sockets for their local fakes;
no external Anthropic service is used. Re-run those and GUI integration in an environment that supports them.

Historical baseline (6a, ai-routes worktree): 143 passed / 12 failed, of which 11 GUI failures came from patching plugin
modules while core built its own view, and one launch failure came from the guessed source path. The latter test now checks
host-owned dispatch/environment and passes. The native GUI crash in this run prevents a new GUI failure count.
