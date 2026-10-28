# Claude plugin: handover

Where the plugin stands after step 6a of [PLAN.md](PLAN.md), and what to know before step 6b.

## Where it is

- **Local repository** `~/github/slidemage-plugin-claude`, branch `plugin-claude`, no remote yet (it becomes
  `JuergenFleiss/slidemage-plugin-claude` in step 6c). Its history was filtered with git-filter-repo from SlideMage's `feature/anthropic-stdlib`
  (the Claude files only); it has nothing in common with SlideMage's branches: never merge it into them.
- Step 6a is in the working tree and, until the commits are made, uncommitted.

## What is in it

```
plugin.toml              id claude, version 1.0.0, api_version 1, requires_slidemage >=10.0
claude/                  the plugin
  __init__.py            activate(host), empty
  credentials.py         the Anthropic key
  api/provider.py        the Anthropic API client, standard library only
  code/                  launch, runner, images, hook, scope, mcp_server
  code/terminal/         session, view, draft
tools/claude_task_benchmark.py
tests/                   conftest.py borrows SlideMage's test support (see below)
build.py, .github/       from the template
website/icon.svg         still the template's placeholder
```

The code is SlideMage `feature/anthropic-stdlib` at `04de23d`, with only the imports changed (and the files moved).

## What does not work yet

- **The plugin does not run on its own.** Every module still imports `slidemage.*` (42 imports, listed with their 6b replacement in PLAN.md),
  and `credentials` imports `keyring`. `python build.py --check` fails on exactly these; it is deliberately not weakened. No `bridge/`
  (see PLAN.md for why).
- `claude/code/launch.py` still builds the hook command as `python -m slidemage.ai.claude_hook` and imports `slidemage.cli.CLAUDE_HOOK_FLAG`; it
  works only while SlideMage still has that module (6b: `add_entry_point`).
- The package name `claude` is the plugin id with the template's rule (folder = id).

## Running the tests

```
SLIDEMAGE_TESTS=<SlideMage>/tests PYTHONPATH=<SlideMage>/src:. <SlideMage>/.venv/bin/python -m pytest -q
```

Needs a SlideMage that has the standard-library Anthropic client (`ai/anthropic_provider.py`, v8.65.1 and later). `tests/conftest.py` loads
SlideMage's `tests/conftest.py` (example project, `qapp`, the isolating fixtures) and puts its tests folder on the path for `fake_http`
and `agent_fakes`. The tests import the plugin's modules, and SlideMage's, from the same process; the moved modules are the only copies the tests
use (the old ones in SlideMage's `src` are not imported by them, except through `slidemage.*` code that still names them).

Results (2026-10-28, SlideMage `feature/ai-routes` worktree): **143 passed, 12 failed**, 3 min 40 s. All 12 failures are the move, not
the worktree's state:

- 11 in `test_claude_code_gui.py`: the tests build SlideMage's `WorkspaceWindow`, which creates *its own* `slidemage.ui.workspace.terminal.view.ClaudeCodeView`
  from core's copies of session and launch, while the tests patch the plugin's modules. They pass again once the window gets its chat surface
  from the plugin's route (6b); until then they cannot test the plugin's view.
- 1 in `test_claude_launch.py` (`test_the_hook_finds_this_slidemage_even_when_it_is_not_installed`): `launch.py` finds SlideMage's `src` folder as
  `Path(__file__).parents[2]`; the plugin sits elsewhere. It goes with `entry_point_command` (6b).

Everything else passes: the API client, runner, images, hook, scope, MCP server, draft reader, and the session tests of `test_claude_scope`.
