# Claude plugin handover

The plugin now imports `Host`, `Route` and the other public types from `slidemage.plugin_api`; the drafted `claude/host.py` has been removed. `claude/__init__.py` registers both real `AiRoute` implementations, one shared settings section and the hook entry point. The cloud API route returns `None` from the backend methods that core wraps; Claude Code returns a task runner, image backends, slide translator and assistant widget. The widget uses the host terminal, watch, tool and background services. Cancellation and `span` are forwarded through the task runner; cancellation is also forwarded into image backends.

Core currently auto-registers Claude's built-in IDs before loading plugins, and the loader rejects duplicate IDs. Therefore this checkout cannot load this plugin normally, even though activation against a host succeeds. Do not publish it as integrated until core resolves route ownership. The assistant's present constructor and other private dependencies are listed in [PLAN.md](PLAN.md#remaining-private-imports-and-missing-public-calls); the checker correctly rejects them. The real host credentials do not expose legacy Anthropic key migration, so that private fallback remains in place, with the saved/cleared marker preventing a legacy key from reappearing. `requires_slidemage` remains `>=10.0`.

The route methods return `None` from `settings_section()` because the single shared builder is registered with `add_settings_section`. The terminal surface currently constructs the core GUI workspace and uses `DiskSync._apply` for the host watch's change callback. These are explicit gaps, not public API guarantees. Tests substitute the plugin route into the registry when exercising the GUI because normal loading is blocked by the duplicate IDs. `FakeHost` records the registrations, host services and secrets and leaves unrelated methods unimplemented.

## Checks

Use the test support from the same worktree as the application:

```sh
SLIDEMAGE_TESTS=/home/juergen/github/SlideMage/.worktrees/ai-routes/tests \
PYTHONPATH=/home/juergen/github/SlideMage/.worktrees/ai-routes/src:. \
QT_QPA_PLATFORM=offscreen XDG_CONFIG_HOME=$(mktemp -d) \
/home/juergen/github/SlideMage/.venv/bin/python -m pytest -q
python3 build.py --check
```

Tests use local fake HTTP/MCP servers, not Anthropic's service. A sandbox that forbids sockets raises `PermissionError` for those tests and prevents a Claude terminal session from starting. The checker is expected to fail until the gaps in PLAN are resolved; do not hide them by weakening it. On 2026-10-28 the full run against the worktree yielded **123 passed, 14 failed, 29 errors**. Of the failures, 13 and all 29 errors were denied local sockets: 19 provider fixture errors, 10 MCP fixture errors, 3 direct MCP failures and 10 terminal GUI failures. The remaining failure, `test_a_process_that_cannot_start_is_shown_in_the_terminal_not_raised`, is a real startup-display mismatch: on MCP startup failure there is no terminal widget in which to print the error. The public terminal service currently cannot create a widget separately. The checker reported **24 private-import violations**. `git diff --check` passed. The worktree changed during testing; one earlier run encountered transient merge-conflict markers in core's registry. Re-run after the core worktree is stable, and run socket-dependent tests where loopback is permitted.
