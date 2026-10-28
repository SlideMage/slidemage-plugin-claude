# Claude plugin: plan

Turning SlideMage's built-in cloud AI, **Claude Code** and the **Anthropic API**, into the plugin `claude`, released through the SlideMage
plugin catalogue. Started from the Claude handover (`Handover_2026-10-26-Claude-Plugin.md`, not in any repository yet) and phase 6 of SlideMage's
`docs/PLUGINS_REMAINING_PLAN.md`. Where things stand now: [Handover.md](Handover.md).

The plugin is two AI routes (core's `AiRoute`, phase 3a) and what they need:

- `claude_code`: `claude -p` for tasks, the embedded terminal as chat surface, the MCP server that gives Claude Code SlideMage's tools, the
  protected-region hook, the Slide / Deck scope;
- `anthropic_api`: the standard-library client and the key (`credentials`).

Each step is one commit (or a few); work pauses after each one for review.

## Steps

| | Step | Status |
|---|---|---|
| 0 | History: the Claude files filtered out of `feature/anthropic-stdlib` with git-filter-repo | done |
| 6a | Layout `claude/{api,code,code/terminal}`, the template adopted, the `slidemage.*` imports inventoried and made absolute, tests moved | done (uncommitted at the time of writing) |
| 6b | Onto the AI host API (after SlideMage's phase 3d) | waits for SlideMage |
| 6c | Release: public repository, icon and screenshots, 1.0.0 | waits for 6b |

### 6a. Layout (done)

| From (SlideMage `feature/anthropic-stdlib`) | To |
|---|---|
| `ai/anthropic_provider.py` | `claude/api/provider.py` |
| `ai/credentials.py` | `claude/credentials.py` |
| `ai/claude_{launch,runner,images,hook,scope}.py` | `claude/code/{launch,runner,images,hook,scope}.py` |
| `ai/mcp_server.py` | `claude/code/mcp_server.py` |
| `ui/workspace/terminal/{session,view,draft}.py` | `claude/code/terminal/{session,view,draft}.py` |
| `tools/claude_task_benchmark.py`, `tests/*` | same place |

Done with `git mv`, so the history follows. The relative imports (`from .. import x`) are now absolute: the plugin's own modules as `claude.…`, the
rest as `slidemage.…`. Where a module is imported under its old name (`claude_launch`, `claude_runner`, …) it is aliased
(`from claude.code import launch as claude_launch`), so the code and the tests read as before; drop the aliases when convenient.

There is **no `bridge/`**: nearly all of the imports below become host calls or neutral types in 6b, and most of what stays core is imported by
the terminal view, which is rewritten against the host's `terminal()` anyway. A bridge would only move the same absolute imports to another folder.

**`build.py --check` fails on all of these until 6b** (the 42 `slidemage.*` imports and `keyring`). The check is not weakened.

### The `slidemage.*` imports: what each becomes (6b)

`claude_tasks` (`ai/claude_tasks.py`, to become `ai/tasks.py` in SlideMage's phase 3b) is the task definitions; it is core.

| Module | Uses | Becomes |
|---|---|---|
| `api/provider` | `ai.providers`: `ChatReply`, `Message`, `ProviderError`, `Cancelled`, `DEFAULT_ANTHROPIC_MODEL`, `_HttpProvider`, `_image_media_type`, `_error_detail` (**private** ones) | neutral AI types from `plugin_api`; the three private helpers need a public home (or are copied: they are small) |
| | `ai.agent_types`: `AgentMessage`, `AssistantMessage`, `ToolCall`, `ToolResultsMessage`, `ToolSpec` | neutral agent types from `plugin_api` |
| | `project.ProjectContext` | the `ctx` the route is given (`provider(ctx, route)`) |
| `credentials` | `app_settings` (the old key places), `project.ProjectContext` | `host.credentials("claude")`: environment, keychain or file, finds the old places; `keyring` goes with it (the check refuses it) |
| `code/launch` | `cli.CLAUDE_HOOK_FLAG`; the hook command `-m slidemage.ai.claude_hook` | `add_entry_point("hook", main)` and `entry_point_command("hook")`; `--claude-hook` stays an alias in core for one major version |
| | `processes.no_console_kwargs` | stays core, via a `plugin_api` helper (or `subprocess` flags inline: 5 lines) |
| | `ai.image_instructions.IMAGE_DESCRIPTION_RULES`, `ai.tools.CLAUDE_CODE_PRE_APPROVED` | stays core, reached through `ai_tools()` (names the pre-approved tools) and the image task definitions |
| `code/runner` | `ai.claude_tasks`, `ai.translation_style` | task definitions and the translation style: neutral types from `plugin_api` |
| | `processes.no_console_kwargs`, `project.ProjectContext` | as above |
| `code/images` | `alt_draft`, `alt_images`, `translation_prompts`, `ai.claude_tasks`, `project.ProjectContext` | the image backend protocols and the task definitions (neutral types); `alt_*` helpers: whatever the protocols hand over, else protected-region/alt-text readers in `plugin_api` |
| `code/hook` | `ai_review`, `alt_images`, `fileio`, `project`, `timing`, `slide_protection.protected_problem/slide_kind` | `protected_regions` (read) from `plugin_api`; the review marks (`ai_review.mark`) and the alt-text sidecar need a host call; `fileio`/`timing`: small helpers, copy or `plugin_api` |
| `code/scope` | `fileio.write_json` | the focus (deck, slide, scope) from `plugin_api`; `write_json` is an atomic write: copy (10 lines) |
| `code/mcp_server` | `ai.agent_types.ToolCall`, `ai.tools.base.ToolBox` | `ai_tools()` returns the ToolBox; `ToolCall` is a neutral agent type |
| `code/terminal/session` | `ui…terminal.sync.DiskSync` | the external-edit watch host service |
| | `pty_process.PtyProcess`, `ui…terminal.web.TerminalWidget` (view) | `terminal()`: the embedded terminal service |
| | `ai.tools` (`CLAUDE_CODE_TOOLS`, `ToolBox`, `build_toolbox`), `ai.agent_types.EDIT_AUTO`, `ui…chat.gui_workspace.GuiWorkspace` | `ai_tools()` builds the box; the workspace is the host's |
| | `compiler` | stays core: compile after an external edit, through the host (`ai_tools()`' compile tool or a host call) |
| | `ai.ai_profile` (model, effort, policy) | the route's own settings and `AiRoute.model_choices/default_choice`; `restart(choice, continue_conversation)` |
| `code/terminal/view` | `ai.ai_profile`, `ai.claude_tasks`, `ui.background`, `ui.kit` (`kit_qss`, `Button`, `Chip`, `IconButton`, `IconLabel`, `SegmentedControl`, `Surface`, `caption`), `ui…attachments` (`place_file`, `save_image`), `ui…state.WorkspaceState`, `ui…terminal.tasks` (`TaskRunner`, `bubbles`) | `AiRoute.chat_surface(...)` with the host's `terminal()`; the widgets are the host's kit (as CampusOnline's `Host.Page/Field/caption`); the task bubbles and the attachments are core's `chat_surface` contract; `background` is `run_in_background` |
| `tools/claude_task_benchmark.py` | `project`, `slide_*`, `latex_lint`, `ui.workspace.window`, `ui.kit`, `terminal.tasks`, … | a developer tool run from SlideMage's environment; stays on `slidemage.*` |

`code/terminal/draft.py` imports nothing from SlideMage.

From the host API (SlideMage phase 3d) the plugin needs, in order of use: `add_ai_route` (two routes), `ai_tools()`, `terminal()`, the
external-edit watch, `credentials(plugin_id)`, `add_entry_point`, the neutral AI types, `protected_regions`, the focus, `add_settings_section(page="ai", …)`.
Handover §8 (from SlideMage): the `chat_surface` lifecycle `stop()` and `restart(model, continue_conversation)`, effort as part of the model choice,
and a `problem()` that can say "not installed".

### 6b. Onto the AI host API

- `activate(host)`: two `add_ai_route` calls (`claude_code`, `anthropic_api`), the AI settings section (today's Cloud tab with the Claude Code
  status, an API-key field), and `add_entry_point("hook")`.
- Replace every `slidemage.*` import per the table; `build.py --check` passes.
- `claude_launch` builds the hook command from `entry_point_command`.
- The settings and the key are found in their old places (`credentials`, the old `app_settings` keys), so a project that used the built-in Claude
  keeps working; stored route ids `local`→`ollama`, `api`→`anthropic_api` are core's.
- `plugin.toml`: `requires_slidemage` to the first SlideMage with the host (now `>=10.0`).
- Tests: the plugin's own against a fake host, which run anywhere (`credentials`, `api/provider` against `fake_http`, `launch`, `scope`, `hook`,
  `runner`, `mcp_server`, `draft`); the ones that need Qt and SlideMage (`test_claude_code_gui`, `test_claude_scope`'s session tests) in `tests/bridge/`
  or against SlideMage's environment. Check runs both. The tests' dependency on SlideMage's `tests/conftest.py` goes (`tests/conftest.py` here).
- Remove `slidemage.ai.claude_hook` and friends from SlideMage (Stefan's side; phase 7).

### 6c. Release

- Create `JuergenFleiss/slidemage-plugin-claude` (public, issues open) and push this branch to its `main`.
- Replace `website/icon.svg` (still the template's); screenshots in `website/screenshots/`.
- Date the 1.0.0 entry in `CHANGELOG.md`, tag `v1.0.0`; the Release workflow publishes the asset.
- A pull request to `stpalan/slidemage-website` `registry/plugins.toml` (`releases = ["1.0.0"]`).
- The catalogue must list 1.0.0 before the first SlideMage without the built-in routes ships (v10.0, the AI-free core).

## Open questions

- Private helpers of `ai.providers` that the Anthropic client uses (`_HttpProvider`, `_error_detail`, `_image_media_type`): public in `plugin_api`, or copied
  into the plugin?
- `fake_http` and `agent_fakes` (SlideMage's test helpers) are used by `test_agent_claude`; copy them here at 6b?
- Does `terminal/view.py` stay a Qt widget in the plugin (it is built on core's kit), or does core own the view and the plugin supply only a session
  (`terminal()` + launch command)? The second would drop most of the UI imports above.
- `settings.py`: the handover's layout lists it; the AI section's builder goes there at 6b (nothing to put in it at 6a).
