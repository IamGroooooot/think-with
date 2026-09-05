---
name: manage-skills
description: Maintain think-with skill sources, platform adapters, plugin catalogs,
  and generated packages. Use for repository skill changes.
---

# Manage think-with skills

Work from this repository's root, identified by `catalog.toml` and `mise.toml`.
Read [the authoring contract](references/authoring.md) before changing sources
or build behavior. Read [platform guidance](references/platforms.md) when a
change depends on a host's metadata, tools, or installation behavior.

## Change the source

- Edit distributable skills under `src/skills/<name>` and project-only skills
  under `src/internal/<name>`. Never place internal skills in a plugin's list.
- Edit common Markdown and `skill.toml`, not files listed in `.generated.json`.
  Preserve the skill's purpose, name, invocation policy, and required resources.
- Use the `port-skill` project skill when bringing a skill from elsewhere.
- Use the smallest platform block that preserves the intended behavior. Do
  not globally replace tool names or assume two tools accept the same inputs.
- Add a public skill to its plugin's `skills` array in `catalog.toml`. A new
  plugin needs a new table there; the generator builds both platform packages.
  Update the README's skill list.
- Keep scripts as Python uv scripts. Resolve bundled data relative to the
  script's `__file__`; keep user input/output paths independent of that location.

When a material decision or clarification is needed, use `AskUserQuestion`
with concise questions and meaningful options matching its current tool schema.
Use the returned answer, including free text, to guide the next step.
If the tool is unavailable, ask the question in chat and wait for the answer.
Do not interpret silence or a tool timeout as permission for a consequential action.

## Verify the result

Run `mise install` when the pinned tool is missing, then `mise run build` and
`mise run check`. If mise requests trust for this checkout, follow the host's
authorization rules for trusting the repository. Inspect the source diff and
generated diff together. Commit generated files alongside their sources when
the user requests a commit; do not publish or install into a user's global
configuration merely to validate a change.

For changes to host behavior, validate with the installed Claude validator and
Codex loader as described in the platform reference. A YAML check alone does
not prove discovery, invocation, or behavior. State which checks actually ran.

For a release, update the affected plugin's version once in `catalog.toml` and
regenerate. Keep versions out of the Claude marketplace entries; plugin
manifests own the generated versions. Internal-only changes do not require a
public plugin version bump. Do not invent a release or push authorization.

Report changed behavior, validation, and any portability limits that remain.
