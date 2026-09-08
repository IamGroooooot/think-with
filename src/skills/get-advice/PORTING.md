# Port verification

Source: `IamGroooooot/skills`, revision
`edcb31d52f7a6b1cfff5860073659ccd3d7a089b`, path `get-advice`.
The source skill had no working-tree changes when inspected.

## Content and behavior

- Preserved name, purpose, automatic invocation policy, and Codex UI metadata.
- Copied discovery, expert briefing, and fact-checking references unchanged.
- Added host-specific question, delegation, and resource-resolution instructions.
- Set expert defaults to Astra low / Fable 5.1 low as requested; the source
  inherited the expert model. Preserved Luna xhigh checking and mapped it to
  Opus 5 medium. The coordinator retains its session model.
- Bundled Claude agent definitions, registered them in the Claude plugin, and
  documented standalone project registration. Expert/checker definitions deny
  nested Agent calls. A delegated Claude coordinator that cannot spawn workers
  hands prepared work back to its parent instead of claiming completion.
- No scripts required conversion. No evaluation-only files or caches existed in
  the input skill. No original legal notices were present or removed; no new
  license was assigned. No other skill or source repository is a runtime dependency.

## Checks run

Validated with Claude Code 2.1.263 and Codex CLI 0.153.4.

- `mise install`, `mise run inspect -- <source>`, and `mise run build` passed.
- `mise run check`: 42 tests passed; 45 generated files matched their sources.
  New packaging tests cover agent registration, platform separation, stale
  output detection, name collisions, malformed definitions, and invalid paths.
- A temporary Git snapshot of the final source/package changes was cloned into
  a fresh directory. `mise run check` passed without building first and left the
  clone clean. No commit was created in the working repository.
- `claude plugin validate . --json` and validation of the generated Claude
  plugin passed with no warnings. Their empty component inventories alone do
  not establish skill loading.
- Codex `debug prompt-input` discovered the generated skill alone under a
  temporary project's `.agents/skills`, with an isolated configuration directory.
  This checks discovery, not a model-driven invocation or consultation.
- Claude loaded `/think-with:get-advice` from a relocated generated plugin.
  A local mock API supplied synthetic Agent calls, and the real host sent expert
  requests using `claude-fable-5-1` / `low` and checker requests using
  `claude-opus-5` / `medium`. Workers had no Agent tool. The parent retained
  its separate Sonnet / high setting, confirming the worker settings override it.
- The same synthetic claim check passed with only the generated Claude skill
  copied into a temporary project's `.claude/skills`, and its bundled agent
  definitions registered in that project's `.claude/agents` before startup.
  Both relocation checks used paths containing spaces and temporary host
  configuration; no global plugin installation was performed.

The mock probes above check loading and request construction. Subsequent live
smoke tests used one retrieval-practice research question in temporary projects:

- `claude -p` completed research, Fable expert consultation, Opus checking, and
  a final answer in 184 seconds (exit 0). It also made one unnecessary checker
  call with a placeholder prompt before the substantive consultation and check.
- `codex exec` completed a final answer in 194 seconds (exit 0), reporting Astra
  low expert consultation and Luna xhigh independent checking. The container's
  `bwrap` permissions blocked local file reads in workspace-write mode; the
  successful retry used danger-full-access in the temporary test project.
- Temporary credential copies, configuration, workspaces, and logs were removed
  after testing. The existing repository changes were preserved.

These are limited smoke tests, not a broad evaluation of research or advice
quality. Remote marketplace installation was not exercised.

## Host contract sources

- [Claude subagent definitions and effort](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields)
- [Claude model configuration](https://code.claude.com/docs/en/model-config)
- Codex spawn arguments were checked against the native tool schema exposed in
  the porting session; installed loader behavior was checked separately above.
