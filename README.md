# Claude

Claude as SlideMage's cloud AI, in two ways. Both do the same jobs (the chat, drafting and translating slides, describing images); you choose
which one SlideMage uses, and can switch at any time.

- **Claude Code.** SlideMage opens Claude Code, Anthropic's coding assistant, in a terminal beside the editor and connects it to the open deck.
  Claude Code reads and edits your slides with SlideMage's own tools, and stays inside what you are looking at: the **Slide / Deck** switch above
  the terminal says how far a request may reach. Parts of a slide that are protected (SlideMage's protected regions) are refused, whatever
  Claude Code tries. Tasks that run on their own, such as describing images, use Claude Code too.
- **The Anthropic API.** SlideMage talks to Anthropic directly with your API key, with no Claude Code installed. The chat is SlideMage's own, with
  the same tools; it needs nothing but the Python standard library.

**What leaves your computer.** With either way, the text of the slides you work on, the files and images your requests refer to, and
what you type go to Anthropic (`api.anthropic.com`). Claude Code makes its own further connections, as Anthropic describes for it; SlideMage does not
control them. The plugin sends nothing anywhere else. Your API key is kept in the system's keychain or in a file only you can read, never in a deck.

**What you need.** Either Claude Code, installed and signed in (Anthropic account with a subscription or API credit), or an Anthropic API key.
SlideMage 10.0 or later.

## Development

The plugin follows the [SlideMage plugin template](https://github.com/stpalan/slidemage-plugin-template) and the
[plugin conventions](https://slidemage.org/plugins/submit/). [docs/PLAN.md](docs/PLAN.md) has the steps and
[docs/Handover.md](docs/Handover.md) says where things stand.

```
claude/                  the plugin
  __init__.py            activate(host): two DRAFT routes, combined AI settings, hook entry point
  host.py                exact 3d host subset + DRAFT route/settings contracts
  credentials.py         host-owned Anthropic key + lazy legacy migration
  api/provider.py        the Anthropic API client (standard library only)
  code/                  Claude Code: launch, runner (headless tasks), images, MCP server, hook, scope
  code/terminal/         the embedded terminal: session, view, unsent-prompt reader
tools/                   claude_task_benchmark.py
tests/                   the plugin's tests
docs/                    plan, handover, and the list of slidemage.* imports still to replace
```

**Status: step 6b is a DRAFT.** It uses the implemented AI host services, but route/AI-settings registration and
workspace integration still wait for SlideMage 3a/3b/3c. The unchanged `python3 build.py --check` reports 27 remaining
core imports, inventoried with their waits in [docs/PLAN.md](docs/PLAN.md). This is not a release-ready plugin.

`python build.py --check` checks the plugin against the catalogue's conventions: `plugin.toml`, the package and its `activate(host)`, the imports, no
compiled files, and a `CHANGELOG.md` entry for the version. The **Check** workflow runs it on every push.

`python build.py` checks and then builds `dist/claude-<version>.smplugin` (a zip of `plugin.toml`, `LICENSE` and the package) and its `.sha256`.

### Tests

The tests need SlideMage on the path (its source for the imports, its `tests/` folder for the example project and the Qt fixtures, through
`tests/conftest.py`), using the `feature/ai-host-services` source worktree:

```
SLIDEMAGE_TESTS=../SlideMage/tests PYTHONPATH=../SlideMage/.worktrees/ai-host-services/src:. ../SlideMage/.venv/bin/python -m pytest -q
```

`SLIDEMAGE_TESTS` defaults to `../SlideMage/tests`.

### Releasing a version

1. Raise `version` in `plugin.toml` and add a line to the end of `CHANGELOG.md`:
   `v1.2.0 (2026-11-02, reason): What changed.`
2. Commit, then tag and push: `git tag v1.2.0 && git push origin v1.2.0`.
3. The **Release** workflow checks that the tag matches the version, builds the asset and publishes the GitHub release with it.

A published version never changes: never replace or delete its asset; a fix is a new version.
