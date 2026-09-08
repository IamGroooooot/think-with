# Host execution

The coordinator retains the current session's model. The worker defaults below
apply unless the user explicitly selects another model or effort level. Include
the expert or checker instructions from the linked briefing and fact-checking
references in each self-contained message; a file path alone is insufficient
unless the recipient can read it. Experts and checkers must not delegate.

Use the session's native `spawn_agent` tool with a unique task name and the
prepared brief as its message. Set `fork_turns = "none"` for every expert and
checker. Default experts to `gpt-6-astra` with `reasoning_effort = "low"`;
default checkers to `gpt-5.6-luna` with `reasoning_effort = "xhigh"`.
Use the available native messaging and completion tools to collect actual
results; launching an agent does not establish that its work is complete.
Follow the tool schema exposed in the current session rather than inventing
an alternative CLI or environment variable. Keep bundled resource paths
relative to the loaded SKILL.md location, not the caller's working directory.


Parallelize only independent briefs or claim bundles. Wait for their results,
preserve unassessed claim IDs, and resolve corrections before final delivery.
Never treat an empty response or a still-running agent as completed checking.

If the requested model or effort is unavailable, disclose the actual substitute
and its limitation. If native agents are unavailable, do the possible research
and factual checking in-session and explicitly state that independent
consultation or verification did not run. Do not silently change the user's
model preference or claim that prompt wording enforces a runtime effort level.
