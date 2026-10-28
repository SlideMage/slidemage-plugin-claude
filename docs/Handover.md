# Claude plugin handover

The plugin is adapted to the API 1 additions in `/home/juergen/github/SlideMage/.worktrees/ai-routes`. Its packaged code imports SlideMage only through `slidemage.plugin_api`, and `python3 build.py --check` passes. The shared Claude settings section reads old API keys through the public legacy reader, preserves the cleared-key marker and notifies the host when the key changes.

Claude Code creates its surface with `ChatSurfaceContext`: it uses the context for route selection, focus details, tools, attachments, editor synchronization and translation. The terminal widget is created before MCP/process startup so startup errors can be displayed in it. Session cancellation uses `CancelToken`; task and image backends use the exported task, image, translation and outcome definitions. The hook uses `hook_context_from_environment` for snapshots, review and file operations. Core owns the route leases for tasks it starts; the plugin has no additional long-running route job. See [PLAN.md](PLAN.md) for the remaining project-helper contract mismatch, route ownership decision and development-only imports.

Core still auto-registers the two Claude route IDs, so normal plugin loading fails with duplicate IDs. The GUI tests substitute the plugin route into the registry and provide the real host UI; they do not establish that normal loading works. Do not publish as integrated until core resolves route ownership and the unreleased API compatibility range.

## Checks

Use the test support from the same worktree as the application:

```sh
SLIDEMAGE_TESTS=/home/juergen/github/SlideMage/.worktrees/ai-routes/tests \
PYTHONPATH=/home/juergen/github/SlideMage/.worktrees/ai-routes/src:. \
QT_QPA_PLATFORM=offscreen XDG_CONFIG_HOME=$(mktemp -d) \
/home/juergen/github/SlideMage/.venv/bin/python -m pytest -q
python3 build.py --check
```

Tests use local fake HTTP/MCP servers, not Anthropic's service. This sandbox denies sockets and can trap when Qt/WebEngine starts the terminal; the orchestrator must rerun the full suite where loopback sockets and WebEngine are available. The first full run after the migration passed 123 tests, with 13 failures and 29 errors due to denied sockets and one stale test reference; that reference was corrected. A subsequent full run hit a `Trace/breakpoint trap` in the terminal startup-display test before completing. With the trapping test deselected, the run completed with 125 passed, 13 socket-denied failures and 29 socket-denied errors; one test was deselected. The failures are 10 terminal GUI tests and three MCP tests; the errors are 19 provider and 10 MCP fixture errors. Focused route, hook, scope, image and runner tests passed (70 tests). Do not interpret the interrupted full run as a pass.
