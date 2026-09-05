# Platform guidance

Official documentation checked 2026-09-05. Local implementation baseline:
Claude Code 2.1.260, Codex CLI 0.147.0, mise 2026.8.9, uv 0.11.16.
These are tested versions, not claimed minimum supported versions.

## Skills

- Claude project skills: `.claude/skills/<name>/SKILL.md`.
- Codex project skills: `.agents/skills/<name>/SKILL.md`.
- Explicit-only invocation maps from Claude `disable-model-invocation: true`
  to Codex `agents/openai.yaml` containing `policy.allow_implicit_invocation:
  false`. Auto is the default for new skills; preserve policy on imports.
- Claude `AskUserQuestion` and Codex `request_user_input` are distinct tools.
  Follow the current session's schema and availability. Do not copy a Claude
  argument object into a Codex tool call. When forms are unavailable, ask in
  ordinary chat and wait for the user's response.
- Claude-specific context forks, tool preapproval rules, model settings,
  hooks, argument substitutions, and dynamic shell injection are not portable
  by spelling changes. Adapt the workflow or ask about a meaningful change.
- Claude supports `${CLAUDE_SKILL_DIR}` for installed skill paths. Codex
  instructions should resolve resources relative to the loaded SKILL.md path;
  do not invent a `${CODEX_SKILL_DIR}` environment variable. Python resource
  lookups use `Path(__file__)`; user data paths retain their own meaning.

Sources: [Claude skills](https://code.claude.com/docs/en/skills),
[Claude question tool](https://code.claude.com/docs/en/tools-reference#askuserquestion-tool-behavior),
[Codex skills](https://learn.chatgpt.com/docs/build-skills).

## Plugins and installation

Both marketplace paths resolve plugin sources from the marketplace root, not
the JSON file's immediate directory. Use `./` paths that stay inside that root.
Generated Codex entries use AVAILABLE, ON_INSTALL, and Productivity. Codex's
other authentication policy spelling is ON_USE, not ON_FIRST_USE. No external
authentication is introduced by this skills-only scaffold.

Codex plugin display metadata belongs inside `interface`; `author` is an
object. Omit apps, MCP servers, hooks, and asset paths unless they are actually
part of the package. The project uses only the small subset it needs; it does
not attempt to implement every current plugin feature.

```sh
claude plugin marketplace add IamGroooooot/think-with
claude plugin install think-with@think-with
codex plugin marketplace add IamGroooooot/think-with
codex plugin add think-with@think-with
```

Start a new session after installation. In an existing Claude session,
`/reload-plugins` can apply plugin changes. Do not assume that Claude slash
commands are Codex commands.

Sources: [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces),
[Claude installation](https://code.claude.com/docs/en/discover-plugins),
[Codex packaging](https://developers.openai.com/plugins/build/plugins),
[Codex CLI](https://learn.chatgpt.com/docs/developer-commands?surface=cli),
[Codex marketplace policy names](https://learn.chatgpt.com/docs/enterprise/plugin-management).

## Verification

Run `claude plugin validate .` for the marketplace and validate each generated
Claude plugin. In the tested CLI, passing a standalone skill directory returns
an empty contents array, so that result does not prove skill validation.
Use the repository's frontmatter/resource checks for these files, and inspect
the actual skills in a host session or a temporary plugin's component inventory.
For Codex, use
`codex debug prompt-input` from the checkout to inspect model-visible skill
discovery. Capture output privately or filter for just the tested skill names;
the complete prompt may include unrelated local information.
This debug command does not exercise the full skill invocation pipeline;
appending a dollar-prefixed skill name alone is not an explicit-invocation test.

For installation tests, use temporary CLI configuration directories and a
temporary Git repository containing only this project's committed-equivalent
files. Register that local Git source and install by marketplace name. Verify
which platform package was cached and compare its bytes with the generated
package. Never use the user's global plugin configuration as a test fixture.

Structural validation, loader discovery, live model behavior, and remote
GitHub installation are different checks. Report each honestly. Recheck the
official documentation and current CLI help before changing host contracts.

Build tools: [mise tasks](https://mise.jdx.dev/tasks/),
[uv scripts and inline dependencies](https://docs.astral.sh/uv/guides/scripts/).
