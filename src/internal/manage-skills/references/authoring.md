# Authoring contract

The repository maintains one common source and commits ordinary host-native
files. Consumers do not run the generator or need mise. Authors run:

```sh
mise install
mise run build
mise run check
mise run inspect -- /path/to/source-skill
```

`check` renders expected bytes in memory, compares them with the checkout, and
runs tests in temporary directories. It never repairs a stale checkout before
checking it. `.generated.json` records owned files. A build refuses to overwrite
an existing unowned file or package an unexpected file inside a generated plugin.

## Sources

Public sources live in `src/skills/<name>`. Project-only sources live in
`src/internal/<name>` and are automatically generated into `.claude/skills`
and `.agents/skills`. The source folder and frontmatter name must match, using
lowercase kebab case with at most 64 characters.

`SKILL.md` begins with common YAML frontmatter. Supported common fields are
`name`, `description`, `license`, `compatibility`, and `metadata`. Name and
description are required. Keep descriptions short and specific; do not treat a
historical description-length limit as a current platform guarantee.

`skill.toml` is optional for an instruction-only skill. It is an authoring
file and is not shipped. Example:

```toml
invocation = "explicit" # auto (default) or explicit
files = ["references/guide.md", "scripts/analyze.py", "assets/template.txt"]

[origin]
repository = "https://github.com/example/skills"
revision = "full-source-commit-sha"
path = "skills/analyze"

[claude.frontmatter]
argument-hint = "[input-file]"

[claude.blocks]
input = "Read the input file path supplied with this skill invocation."

[codex.blocks]
input = "Read the input file path from the user's request."

[codex.openai.interface]
display_name = "Analyze"
short_description = "Analyze an input file and report findings"
default_prompt = "Use $analyze to inspect this input file."
```

`files` lists individual runtime files under `references/`, `scripts/`, or
`assets/`; there are no glob patterns or directory-copy rules. Top-level legal
notices such as LICENSE, NOTICE, and COPYING are included automatically.
Development directories such as evals, .git, and node_modules cannot be bundled.
Use assets for user-facing output templates, including code templates. Use
scripts only for executable Python helpers; every helper has uv metadata.
Optional Codex UI and MCP dependency metadata belongs in `codex.openai`;
invocation policy belongs only in `invocation`. Never silently discard an
existing host-specific field: adapt it deliberately or resolve the difference.

## Platform blocks

Write a marker on a line by itself:

```text
{ {tw:input} }
```

Remove the space between each pair of braces when authoring a real marker.
The matching platform's `blocks` table supplies that paragraph. Shared blocks
come from `adapters/<platform>/<key>.md`; a per-skill block of the same name
overrides the shared block. `ask-user` is the initial shared block.

Markers are expanded only in SKILL.md and Markdown under references. There
are no loops, conditionals, nested markers, or build-time command execution.
Unknown markers fail the build. To show a marker literally in a reference,
write the braces separated, for example `{ {tw:input} }`; even code-fenced
markers in source Markdown are otherwise expanded.

Use actual Markdown links for bundled resources so the checker can verify
them. Scripts resolve runtime dependencies themselves and need behavioral
tests; static Markdown checks cannot discover arbitrary file accesses.

## Packaging and releases

`catalog.toml` holds marketplace identity and one `[plugins.<name>]` table per
plugin, containing `version`, `description`, and `skills`. Keep the same skill
name on both hosts. List distributable skills explicitly. Do not add a
demonstration skill just to fill a plugin.

Build outputs are ordinary files below `plugins/claude/<plugin>` and
`plugins/codex/<plugin>`, plus the two root marketplace manifests and internal
skill directories. Each skill contains its own runtime dependencies. Neither
the repository root nor another installed skill is a runtime resource path.

Use a numeric MAJOR.MINOR.PATCH release version in the catalog. Both generated
plugin manifests receive that value; the Claude marketplace does not repeat
it. Add new plugin tables to extend the catalog rather than adding special
cases to the generator. Review output before committing. A commit or release
is a separate user-directed action from editing or validating a skill.
