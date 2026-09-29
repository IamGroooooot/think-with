---
name: lay-out
description: Show a topic with the smallest useful view; avoid unneeded artifacts.
---

Show the current topic so the reader gets the key relationship from the diagrams alone. Prose adds at most a one-line takeaway and caveats that change a decision.

Before drawing, choose:
- the one relationship the user must see (a change, comparison, decision, dependency, or flow) and its most consequential fact, which the view shows first and sets apart instead of burying it among routine details
- the level that shows it: components, layers, states, or steps; drop to a code line only when that line alone carries the behavior
- the form that fits the relationship
- only supported edges; label relevant inference or dispute, and mark an unknown only where it changes the answer

Choose forms first; read only their selected links:
- condition or algorithm → pseudocode
- one ordered path, or how a failure unfolds → trace or timeline
- messages or handoffs between participants over time → horizontal [sequence](references/sequence.md)
- data movement and storage → horizontal [data flow](references/dfd.md)
- dependencies between modules or packages → [layered dependencies](references/dependencies.md)
- call reachability → call tree
- hierarchy or UI → shallow tree
- state transition → state diagram that shows terminal states; a state table when exact guards matter
- the same properties compared across parallel items, such as options or each route's guard before and after → aligned table, one row per item; when the answer is a path or what depends on what, draw it instead
- spatial layout → wireframe
- exact implementation → focused code

Use one main view. Add a second only for a different relationship the question needs. When the user names several concerns, give each its own view; in a whole-system view, collapse parts off the relevant path into one box and mark the change in place.

Prefer text fences and fit the terminal; if width is unknown, target 60 columns. Never wrap a connector. In a diff fence, reserve column 1 for +, -, or space and align unchanged context. Use Mermaid only if text loses a required relationship. Create HTML only if explicitly requested or necessary interaction cannot be provided inline.

For a diff or PR, start with the changed files as a short tree, one line each, so the reader knows where the change lives before how it behaves, and say whether it is proposed or applied. Then show the behavior change in the form the change takes. When the same property changes across parallel items, such as each route's auth or each client's timeout, use a before/after table with one row per item so each pair reads across one row. When wiring or order changes, mark + for added and - for removed on one shared structure. Either way, lead with the change that alters behavior most, such as newly exposed or newly protected data, and group the routine deltas. For any other question, go straight to the view.

Read [structural-diff](references/structural-diff.md) only when changed diagram branches or connectors need realignment, not for ordinary file summaries or code patches.

Treat diffs as evidence claims: separate file edits from behavior changes, mark only supported deltas, and leave preserved steps unmarked. Preserve guards and qualifiers. If the user asks what changed but gives no comparison data, say so in one line instead of inventing a comparison. Do not turn unprovided facts into settled claims. For a change, end with at most three short lines on what else it could break.
