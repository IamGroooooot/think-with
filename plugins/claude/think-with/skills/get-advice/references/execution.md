# Host execution

The coordinator retains the current session's model. The worker defaults below
apply unless the user explicitly selects another model or effort level. Include
the expert or checker instructions from the linked briefing and fact-checking
references in each self-contained message; a file path alone is insufficient
unless the recipient can read it. Experts and checkers must not delegate.

The plugin registers `think-with:get-advice-expert` (model
`claude-fable-5-1`, effort `low`) and `think-with:get-advice-checker`
(model `claude-opus-5`, effort `medium`). Use the registered type in
`Agent.subagent_type`, with a short `description` and a self-contained `prompt`.
The definitions set model and effort; do not override them with a floating model
alias or pass Codex's `reasoning_effort` or `fork_turns` fields to `Agent`.
Never use the `fork` type for experts or checkers: it inherits the conversation.

For a standalone skill installation, the same definitions are bundled as
[expert](../assets/agents/get-advice-expert.md) and
[checker](../assets/agents/get-advice-checker.md). If their types are absent,
register those files in the current project's `.claude/agents/`, subject to
the host's write permissions. Preserve any existing definitions; do not
overwrite conflicts. Use the unprefixed type names once loaded. If a newly
created agents directory is not detected, tell the user to restart the session.
Do not modify global configuration. Use the fallback below if registration is
unavailable or conflicts cannot be resolved within the user's request.

Use only the brief and assigned sources as task evidence. Non-fork agents may
still receive host project instructions; do not count that as independent
research or read unrelated local material. If this consultation was delegated
to a coordinator without permission to spawn agents, return the prepared
briefs and draft to the parent to run the consultation and final check, then
resume synthesis from the actual results. Report any unfinished stage.


Parallelize only independent briefs or claim bundles. Wait for their results,
preserve unassessed claim IDs, and resolve corrections before final delivery.
Never treat an empty response or a still-running agent as completed checking.

If the requested model or effort is unavailable, disclose the actual substitute
and its limitation. If native agents are unavailable, do the possible research
and factual checking in-session and explicitly state that independent
consultation or verification did not run. Do not silently change the user's
model preference or claim that prompt wording enforces a runtime effort level.
