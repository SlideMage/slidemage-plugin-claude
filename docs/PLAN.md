# Claude plugin integration plan

The plugin targets the unreleased API 1 additions in SlideMage's `feature/ai-routes` worktree. Activation registers `anthropic_api`, `claude_code`, a shared AI settings section and the hook without creating widgets, reading keys, launching processes or using the network. The package imports only `slidemage.plugin_api` from SlideMage; `python3 build.py --check` enforces this.

Claude Code uses `chat_surface_v2`, the public chat context, terminal service, edit watch and process-aware cancellation token. The hook uses the public hook context for classification, snapshots and review records. The task and image backends use the public definitions and result types. Legacy Anthropic keys are read through the host or route context, with the saved/cleared marker preventing resurrection; saving a key notifies model pickers.

Route tasks, image batches and slide translation are started and leased by core. This plugin has no separate long-running settings job requiring `acquire_route_task` or progress reporting; its sign-in probe uses the ordinary background service. `legacy_ollama_host` is not relevant to the Claude routes.

## Remaining API gap

The exported `check`, `effective_system_prompt` and `get_effective_prompt` still expect a core `ProjectContext`, while route methods receive `RouteContext`. The temporary `claude/code/_project.py` bridge supplies the current project settings and bibliography paths. This matches the checked-out core but relies on its private path conventions. A public helper or wrappers accepting `RouteContext` are needed to remove that dependency; include project-specific prompt overrides and lint/bibliography behaviour.

The packaged plugin has no private SlideMage imports. Integration tests and the developer benchmark still import core internals to construct real application fixtures and compare behaviour; they are outside the package and intentionally remain visible rather than hiding those imports.

## Needs a decision

- **Route ownership:** core still registers the built-in `claude_code` and `anthropic_api` IDs before plugins and rejects duplicates. Recommend removing the built-in registrations as part of the core migration while preserving those IDs and settings. Normal plugin loading remains blocked until then.
- **Project helper contract:** recommend adding public task and prompt wrappers that accept `RouteContext` in core, then removing the temporary path bridge. This needs a core API change outside this repository.
- **Repository-wide import rule:** removing private imports from integration tests and the benchmark too would require replacing their core-specific fixtures and benchmark functionality. Recommend retaining those development-only imports until core supplies equivalent public test and benchmark interfaces; package imports already meet the strict checker.

The manifest continues to require SlideMage `>=10.0`; the API additions are not yet released, so release compatibility must be set when the core release is known.
