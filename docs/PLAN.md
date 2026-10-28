# Claude plugin integration plan

The plugin targets the real `slidemage.plugin_api` in SlideMage's `feature/ai-routes` worktree. Its manifest continues to require SlideMage `>=10.0`. `activate` registers `anthropic_api`, `claude_code`, one shared AI settings section and the hook entry point. Registration is cheap: no Qt widgets, key reads, process launch or network access. The route methods follow `AiRoute` and the checked-out built-in route behaviours; core wraps the API provider for image and slide work. Claude Code passes cancellation through to its process backends and exposes a widget to the assistant.

The routes' `settings_section()` methods return `None`: the shared Claude builder is registered once with `add_settings_section`. The terminal uses `Host.terminal`, `watch_external_edits`, `focus`, `ai_tools` and `entry_point_command`. `tests/fake_host.py` is a structural Host fake; services outside this plugin's tests deliberately raise `NotImplementedError`.

## Remaining private imports and missing public calls

`python3 build.py --check` remains strict. It currently reports 24 imports outside `slidemage.plugin_api`; these are retained because the API does not provide the needed operations. In particular:

| Plugin files | Missing public API/call |
|---|---|
| `credentials.py` | Read the old built-in Anthropic key (`legacy_anthropic_key`) and obtain the project context for settings without a passed context. Host credentials cover new secret storage but do not migrate the old key. |
| `code/hook.py` | Project context from hook environment; classify a slide; read/write exact text and JSON snapshots; identify image sidecar stores and flag edited sources; record AI review events and inserted slides; optional timing events. `protected_spans` is already public. |
| `code/launch.py` | Image-description instructions and names of Claude Code pre-approved tools. |
| `code/runner.py` | Task schema/definitions and validation, answer note and repair/translation request builders; project translation address and glossary. `Outcome` is not exported either. |
| `code/images.py` | Image description schema, prompts, result factories and source hash, translation prompts and image entry/result types; task definition constructor. |
| `code/terminal/session.py` | A cancellation token compatible with the host's tool operations, including terminating a running process. |
| `code/route.py`, `code/terminal/view.py` | GUI-aware tool workspace and a callback to apply external edits to open buffers/decks; selected route/model lookup, task bubbles and translation action; UI kit widgets and styles, attachment placement/image saving. The assistant currently passes application, workspace state, scope control and task runner as untyped implementation objects; no stable public surface-construction contract supplies these capabilities. |

`WorkspaceState` and `ProjectContext` are also not exported as public types. Avoiding a type-only import does not supply a typed context contract. The developer benchmark in `tools/` is not part of the plugin package and intentionally uses core internals.

## Needs a decision

- **Duplicate route IDs:** the checked-out loader rejects plugin `claude_code` and `anthropic_api` because `ai.routes` automatically registers built-in routes first. Recommend completing the planned removal of built-in Claude routes (or an explicit replacement mechanism with migration semantics) in core before loading this plugin. Renaming IDs here would change stored settings and user-visible routes.
- **Public integration boundary:** the private calls above include core-owned review, editor, task and image responsibilities. Recommend agreeing on host services and a typed chat-surface contract in core rather than copying these subsystems into the plugin or making their private modules de facto API.
- **Terminal startup errors:** `Host.terminal().start()` creates the widget together with the process, so an MCP startup failure occurs before a terminal exists. The current plugin shows a status and notice; the built-in view also writes the failure into an already-created terminal. Recommend exposing terminal widget creation/lifecycle separately or agreeing on the changed error display. The corresponding GUI test currently fails.
- **Settings ownership:** both route-level builders and `add_settings_section` are available; the plugin uses one shared section to avoid duplication. Recommend confirming this shared-section convention when the built-in Claude sections are removed.

Release remains blocked on those decisions and on an environment that can run the HTTP/MCP and terminal tests. Keep the existing manifest version requirement until the release compatibility policy is decided.
