---
name: lay-out
description: Show a topic with the smallest useful view; avoid unneeded artifacts.
---

Show the current topic with the smallest views that preserve the important relationship. Keep prose brief.

Before drawing, choose:
- the fact, comparison, decision, or implementation the user must see
- the lowest sufficient level: concept, mechanism, or exact implementation
- the visual shape that matches the relationship
- only supported edges; label relevant inference or dispute and show an important unknown as a gap

Choose forms first; read only their selected links:
- condition or algorithm → pseudocode
- one ordered path → trace or timeline
- timed messages → horizontal [sequence](references/sequence.md)
- ownership and handoffs → [swimlane](references/swimlane.md)
- data movement and storage → horizontal [DFD](references/dfd.md)
- reachability or dependency → call tree or small graph
- hierarchy or UI → shallow tree
- state transition → state table or diagram
- mapping or comparison → table
- spatial layout → wireframe
- exact implementation → focused code

Prefer text fences and fit the terminal; if width is unknown, target 60 columns. Never wrap a connector. In a diff fence, reserve column 1 for +, -, or space and align unchanged context. Use Mermaid only if text loses a required relationship. Create HTML only if explicitly requested or necessary interaction cannot be provided inline.

Read [structural-diff](references/structural-diff.md) only when changed diagram branches or connectors need realignment, not for ordinary file summaries or code patches.

Treat diffs as evidence claims: separate file edits from behavior changes, mark only supported deltas, and leave preserved steps unmarked. Preserve guards and qualifiers. Missing comparison data is not "no change" or "not applicable"; use the latter only when files are unrelated. Do not turn unprovided facts into settled claims.

First show file changes as a tree or short patch. Distinguish proposed from applied changes; say "not applicable" or "change data unavailable" when appropriate. Then give two fitting archetypes; add another only for a necessary relationship they cannot show. Mark supported changes in each relevant view with +/-. Do not invent a comparison. Expose the chosen purpose or level in at most one line only when it helps interpretation.
