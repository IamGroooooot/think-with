---
name: get-advice
description: Find relevant research, consult evidence-grounded experts, and verify
  advice for the user's situation.
---

# Get advice

Find useful research distinctions and checked learning resources.

## Discover

Use existing context; ask via question tools only when answers would change the search. Separate observations from explanations. On explicit invocation, research related work even when the cause is settled; preserve the requested artifact and scope without rediagnosing it.
Use `AskUserQuestion` when available, following its current schema; otherwise ask briefly in chat.

Read [discovery](references/discovery.md) when starting research. Select fields for relevance and accumulated evidence, not familiar labels or a fixed list; drop generic or redundant contributions.

## Consult and synthesize

The coordinator owns discovery through final delivery, including when delegated the entire consultation. Consult the fewest useful, distinct perspectives with fresh native subagents and parallelize independent work.

Use fresh `Agent` calls with the bundled `get-advice-expert` type: Claude Fable 5.1, low effort. Pass each expert only its self-contained brief.
Read [briefing and synthesis](references/expert-briefing.md) when delegating. Experts investigate independently, may reject an unsuitable field, and must not delegate.
Explain what the advice changes, with evidence, applicability limits, and checked learning resources. Separate findings, user facts, and inference. Detail implementation only on request; label small tests as proposals without promised effects.

## Verify before delivery

Read [fact-checking](references/fact-check.md) to prepare the evidence handoff. Group material claims, sources, and context by dependency; send independent bundles in parallel to fresh checkers. One suffices for a short answer.

Use fresh `Agent` calls with the bundled `get-advice-checker` type: Claude Opus 5, medium effort. Pass each checker only its assigned evidence bundle.
Correct errors, exaggeration, and leaps from the checks; recheck only new material claims or unresolved conflicts. Disclose unavailable or unfinished research, delegation, or checking; never invent completion.

## Runtime

Read [host execution](references/execution.md) before delegating. Use the host's web search and source-reading tools; no external research CLI or other skill
is required. Resolve bundled references from this skill's installed directory.
If research or native delegation is unavailable, continue only with the work
that remains possible and disclose the resulting evidence or independence limit.
