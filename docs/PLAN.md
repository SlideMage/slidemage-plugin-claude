# Claude plugin: plan

Turning SlideMage's built-in cloud AI, **Claude Code** and the **Anthropic API**, into the plugin `claude`, released through the SlideMage
plugin catalogue. Started from the Claude handover (`Handover_2026-10-26-Claude-Plugin.md`, not in any repository yet) and phase 6 of SlideMage's
`docs/PLUGINS_REMAINING_PLAN.md`. Step 6b is now a **DRAFT**, with the implemented 3d services adopted and the unfinished 3a/3c registrations
expressed as a local Protocol. Where things stand now: [Handover.md](Handover.md).

The plugin is two AI routes (core's `AiRoute`, phase 3a) and what they need:

- `claude_code`: `claude -p` for tasks, the embedded terminal as chat surface, the MCP server that gives Claude Code SlideMage's tools, the
  protected-region hook, the Slide / Deck scope;
- `anthropic_api`: the standard-library client and the key (`credentials`).

Changes are grouped into logical commits: host services, draft route registration, and documentation. No release or push is part of 6b.

## Steps

| | Step | Status |
|---|---|---|
| 0 | History: the Claude files filtered out of `feature/anthropic-stdlib` with git-filter-repo | done |
| 6a | Layout `claude/{api,code,code/terminal}`, the template adopted, the `slidemage.*` imports inventoried and made absolute, tests moved | done |
| 6b | Onto the AI host API | DRAFT implemented; integration waits for 3a/3b/3c and the public export gaps below |
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

**Historical 6a inventory:** the checker originally reported 42 `slidemage.*` imports plus `keyring`.
6b removes direct `keyring` use and adopts the available public API; **27 core-import violations remain**
(the exact current inventory is below). The check is not weakened.

### The 6a `slidemage.*` inventory and intended replacements

`claude_tasks` (`ai/claude_tasks.py`, to become `ai/tasks.py` in SlideMage's phase 3b) is the task definitions; it is core.

| Module | Uses | Becomes |
|---|---|---|
| `api/provider` | `ai.providers`: `ChatReply`, `Message`, `ProviderError`, `Cancelled`, `DEFAULT_ANTHROPIC_MODEL`, `_HttpProvider`, `_image_media_type`, `_error_detail` (**private** ones) | neutral AI types from `plugin_api`; the three private helpers need a public home (or are copied: they are small) |
| | `ai.agent_types`: `AgentMessage`, `AssistantMessage`, `ToolCall`, `ToolResultsMessage`, `ToolSpec` | neutral agent types from `plugin_api` |
| | `project.ProjectContext` | the `ctx` the route is given (`provider(ctx, route)`) |
| `credentials` | `app_settings` (the old key places), `project.ProjectContext` | `host.credentials(env_var="ANTHROPIC_API_KEY")`: environment, keychain or file, finds the old places; `keyring` goes with it (the check refuses it) |
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
external-edit watch, `credentials(env_var="ANTHROPIC_API_KEY")` (3d: already scoped to this plugin), `add_entry_point`, the neutral AI types, `protected_regions`, the focus, `add_settings_section(page="ai", …)`.
Handover §8 (from SlideMage): the `chat_surface` lifecycle `stop()` and `restart(model, continue_conversation)`, effort as part of the model choice,
and a `problem()` that can say "not installed".

### 6b. Onto the AI host API — DRAFT implemented

Contract sources inspected read-only on 2026-10-28:

- SlideMage `feature/ai-routes` at `38ea44c`: `docs/PLUGINS_REMAINING_PLAN.md`, steps 3a/3b/3c/3d;
- SlideMage `feature/ai-host-services` at `387467d`: `plugin_api.py`, `plugins/{host,credentials,migrate,entry}.py`,
  `ui/workspace/terminal/service.py` (and the watch/tool implementations);
- CampusOnline `9d5a6b9`: the precedent of a local host Protocol and fake host before core implements the registrations.

Implemented here:

- `claude/host.py` describes exactly the host subset used by this plugin. Implemented 3d signatures are preserved,
  especially `credentials(env_var=None)` (already scoped to the plugin; no plugin-id argument),
  `ai_tools(scope="slide", *, focus_slide=None, mode="auto", cancel=None, workspace=None)`, terminal/watch,
  entry points and focus. `AiRoute`, `ChatSurface`, `add_ai_route` and `add_settings_section` are explicitly **DRAFT**.
- `api/route.py` registers `anthropic_api` / Anthropic API; `code/route.py` registers `claude_code` / Claude Code.
  Both are cloud routes with today's four task groups and static, offline model choices. Claude Code chat inherits
  its own model when unset; tasks default to `haiku:medium`. Missing-key/install problems do not choose another route.
- `activate(host)` registers those two routes, exactly one `("ai", "Claude", build)` settings section and the `hook`
  entry point. Both routes refer to that same combined section builder. No Qt/provider/runner loading, credential
  lookup, CLI probing, terminal creation or network during activation.
- The section builds lazily: a password field, explicit Save key button and Claude Code install/auth status.
  Auth probing uses `run_in_background`; it is never part of activation. Its final settings-save lifecycle waits for 3c.
- Host credentials own all new writes. Legacy lookup delegates lazily to core's `legacy_anthropic_key`, which checks
  the old environment/keychain/machine-settings locations without changing them. Core has **not** exported that helper
  through `plugin_api`; the private import remains visible to the checker. `settings().legacy_key_replaced` suppresses
  fallback after an explicit Save/clear, preventing the old key from reappearing on restart. Environment keys still win.
- `launch.hook_command(host)` quotes `host.entry_point_command("hook")`; no old hook module/flag or guessed source-tree
  PYTHONPATH is used in plugin launch code. `hook.main(args)` accepts the entry point's argv.
- The terminal session uses `host.terminal().start(...)`, `watch_external_edits`, `ai_tools` and `focus`; core owns the pty,
  terminal widget and callback delivery. Stop is idempotent, invalidates late callbacks and polls after the process stops.
  `restart(choice, continue_conversation)` resumes only when a transcript exists. Shutdown closes the terminal/MCP/watch
  and removes the temporary focus file. Tests cover failed-start cleanup and retry.
- Neutral agent types, ToolBox, ChatReply/ProviderError/Cancelled and protected_spans come from `plugin_api`.
  The unexported private `_HttpProvider`, socket cancellation, error/media helpers are copied with provenance into
  `api/_http.py`. Small subprocess and atomic JSON helpers live in `_processes.py` and `_files.py`.
- `tests/fake_host.py` records the draft registrations and host services; `test_activate.py` checks them, verifies 3d
  parameter signatures against the actual host Protocol, and proves activation has no network/slow work. Launch/scope/hook
  tests now exercise the moved plugin code and host interfaces.

This is **not installable against 3d alone**: `PluginHost` there has no `add_ai_route` or `add_settings_section`. Do not add
fallback registrations or publish a release until the real contracts are implemented and integration is checked.

#### Remaining imports — waits for 3a/3b (and the explicit 3d export gaps)

`python3 build.py --check` still exits 1 with **27 violations**, all core imports below. No `keyring` violation remains.
Counts include separate imports of the same module. These are kept, not hidden behind an allowlist or a bridge.

| Plugin file | Count | Remaining imports / wait |
|---|---:|---|
| `api/route.py` | 2 | `alt_draft` provider wrappers: **waits for 3a** public image backend protocols/wrappers |
| `code/hook.py` | 7 | `ai_review`, `alt_images`, `fileio`, `project` (twice), `timing`, `slide_protection.slide_kind`: **waits for 3a** neutral ctx/classification and a **3d follow-up** for review/sidecar writes; file I/O/timing have no promised public service yet |
| `code/images.py` | 5 | `alt_draft`, `alt_images`, `translation_prompts`, `project`, `ai.claude_tasks`: **waits for 3a/3b** image types, prompts and `ai/tasks.py` |
| `code/launch.py` | 2 | `ai.image_instructions`, `ai.tools.CLAUDE_CODE_PRE_APPROVED`: **waits for 3a** task instructions / a **3d follow-up** for permission metadata; `ai_tools()` returns specs, not the pre-approval policy |
| `code/runner.py` | 2 | `project`, `ai.{claude_tasks,translation_style}`: **waits for 3a/3b** neutral context, task definitions and style |
| `code/terminal/session.py` | 1 | `compiler.CancelToken`: **waits for 3a** neutral cancellation type (not exported by 3d) |
| `code/terminal/view.py` | 6 | `ai.{ai_profile,claude_tasks}`, UI kit/style/widgets, attachments, workspace state, `terminal.tasks`: **waits for 3a/3b** registry UI, task bubbles and chat-surface integration |
| `credentials.py` | 2 | `plugins.migrate.legacy_anthropic_key`, `project.from_environment`: implemented privately in 3d; **3d follow-up** must expose migration publicly, then remove these imports |

The plan does not yet promise public equivalents for every review/sidecar, timing or UI helper in this table; they must
be settled during host integration, not assumed to exist. `protected_spans` is already public and adopted.

Additional integration waits:

- **3a:** replace the draft AiRoute Protocol with the real route/selection contract. Keep static model choices and the
  problem messages. Registry ids/settings migration (`local`→`ollama`, `api`→`anthropic_api`) belongs to core.
- **3b:** core must construct the plugin's chat surface, attach/re-attach its widget on start/restart, pass a GUI-aware
  workspace and an external-edit callback that applies reload/conflict/deck-rescan behavior. The 3d watch only reports
  changes. Without a workspace the draft caches a disk-only toolbox on the UI thread; MCP workers never read host focus.
  `Focus` only exposes deck/slide/scope, so dirty-buffer/view/language context still needs the 3b contract. The retained
  view has setup cards, attachments and unsent-draft restoration, but the draft route currently returns the terminal
  session; integrating those view features and task bubbles remains 3b work.
- **3c:** finalize settings builder/save semantics and deduplication of the shared Claude section.
- **3d follow-up:** public legacy-key migration and any missing neutral exports/permission/review services above.
- **7:** remove core's Claude copies/compatibility routes on the SlideMage side. Never edit that repository from here.

#### Validation and commits (2026-10-28)

With `SLIDEMAGE_TESTS=/home/juergen/github/SlideMage/tests` and
`PYTHONPATH=/home/juergen/github/SlideMage/.worktrees/ai-host-services/src:.`:

- Offline selection (activation, launch, scope, hook, runner, images, terminal draft): **89 passed**.
- Suite excluding `test_claude_code_gui.py`: **112 passed, 3 failed, 29 errors**. All 32 non-passes fail creating a local
  HTTP socket with `PermissionError: [Errno 1] Operation not permitted` in this sandbox (19 agent-client tests, 13 MCP tests).
- The full `pytest -q` run exits **133 / Trace/breakpoint trap** on reaching the Qt/WebEngine GUI module, without a pytest
  traceback. Full GUI integration also remains structurally blocked by 3b: the host window still creates its own core view.
- `python3 build.py --check`: the 27 violations listed above. `compileall` and `git diff --check` pass.

The repository's `.git` is mounted read-only: the requested commit attempt failed creating `.git/index.lock`.
Logical commits are therefore prepared in a temporary writable Git copy and exported as patches/bundle under
`/tmp/claude-6b-commits/`; the repository branch/history are untouched. All prepared commit messages end with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No push, branch switch or stash.

### 6c. Release

- Create `JuergenFleiss/slidemage-plugin-claude` (public, issues open) and push this branch to its `main`.
- Replace `website/icon.svg` (still the template's); screenshots in `website/screenshots/`.
- Date the 1.0.0 entry in `CHANGELOG.md`, tag `v1.0.0`; the Release workflow publishes the asset.
- A pull request to `stpalan/slidemage-website` `registry/plugins.toml` (`releases = ["1.0.0"]`).
- The catalogue must list 1.0.0 before the first SlideMage without the built-in routes ships (v10.0, the AI-free core).

## Open questions after the draft

- The public migration/read-only classification/review and sidecar APIs listed above need a host decision.
- The shared settings section and the session/view/task-card contract must be reconciled with 3a/3b/3c before installation.
- Tests still borrow SlideMage's fixtures, example project and fake HTTP helpers through `tests/conftest.py`; removing this
  harness dependency can follow the public API integration. The fake host itself does not load Qt or start services at import.
