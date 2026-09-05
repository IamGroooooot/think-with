---
name: port-skill
description: Port an external skill into think-with for Claude Code and Codex, bundling
  runtime resources and converting helpers to Python uv.
---

# Port a skill into think-with

Accept a local skill directory or a Git repository URL with a skill path and
optional revision. Work in the repository containing `catalog.toml`. Read
[the porting procedure](references/porting.md) before copying or rewriting.
Use the project-local `manage-skills` skill for the authoring format and build.

Inspect the source's SKILL.md and trace required references, scripts, assets,
other skills, and external tools. Run `mise run inspect -- <source-directory>`
to collect candidates; this tool does not establish which files are necessary.

Preserve the skill name, purpose, and invocation policy. Bundle everything
needed to use it without the original repository or another installed skill.
Keep user-facing examples, templates, legal notices, and necessary source
material. Exclude evaluation-only content, development tooling, and caches.
Rewrite executable helpers as Python uv scripts, preserving observable behavior.

When a material decision or clarification is needed, use `AskUserQuestion`
with concise questions and meaningful options matching its current tool schema.
Use the returned answer, including free text, to guide the next step.
If the tool is unavailable, ask the question in chat and wait for the answer.
Do not interpret silence or a tool timeout as permission for a consequential action.

Resolve decisions that change purpose, dependencies, or platform behavior with
the user. Reuse existing authorization; do not ask again just because a
routine copy or adaptation is necessary. If the target skill already exists,
compare it before merging the requested changes. Do not overwrite unrelated work.

Create the common source in `src/skills/<name>`, list the runtime files in
`skill.toml`, and add it to the chosen plugin (default: think-with). Build both
platforms, run checks, and test a representative task with only the generated
skill in an isolated location. Do not call the port complete while essential
files, script behavior, or platform-dependent steps remain unresolved.

Report the source revision, included and excluded content, behavior changes,
remaining external tools, and checks actually run. Do not automatically commit,
push, or install the port into global agent configuration.
