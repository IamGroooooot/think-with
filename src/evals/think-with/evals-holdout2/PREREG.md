# lay-out revision 2: pre-registration

Written 2026-09-29. The four cases in this suite were written before revision 2 of the skill was drafted. Nobody has run them, and no answer to them has been seen.

## Why a second holdout
Revision 1 (the candidate in `evals-holdout/PREREG.md`) met all five pre-registered hypotheses, yet lost the user's blind comparison against 0.1.4: 0 wins, 2 losses (h1, h3), 3 ties. The automated graders passed both losing answers. h1 and h3 were inspected to diagnose the losses, so they are now development cases.

## Revision 2 (the candidate)
Revision 1, plus these changes, which come from the get-advice consultation (GPT-6 Astra and Claude Opus 5.5 experts, Sonnet 5.5 fact-checks):
- Diffs: the form follows the change. Use a before/after table with one row per item when the same property changes across parallel items. Mark +/- on one structure when wiring or order changes. Lead with the change that alters behavior most. This replaces "one shared structure rather than separate before and after drawings".
- Tables: allowed for the same properties compared across parallel items, including before/after per item.
- Dependencies: keep every edge as adjacency lists in layer rows. Mark violations in place, draw a cycle as a loop, and add what a violation drags in. This replaces "draw only the edges that break the order".
- The key relationship's most consequential fact goes first and is set apart.

## Frozen
- Cases: `f1-diff-retry-policy`, `f2-deps-ports-adapters`, `f3-flow-pii-phone`, `f4-timeline-duplicate-email`, with the grader texts at the time of writing.
- Arms: revision 2 with the plugin, and release 0.1.4 with the plugin, 3 runs each. Judge model for the plugin-eval graders: `sonnet`.
- Blind pairs for the user: run 1 of each arm for each case (the next run if that one errored), shown with labels hidden in random order. Add h1 and h3 run 1 (revision 2 vs 0.1.4) as development regression checks. That makes 6 pairs.

## Decision rule (primary: the user's blind grades)
Ship revision 2 only if all hold:
1. On the four fresh pairs, revision 2 wins more pairs than it loses.
2. No revision 2 answer is graded X where the paired 0.1.4 answer is O.
3. Revision 2 does not lose h1 or h3.

Otherwise keep 0.1.4, plus only the boilerplate change, which lost nothing in `calibration/evals-holdout-r1-vs-0.1.4`.

## Secondary (triage, not a ship criterion)
- A pairwise judge compares diagrams only, runs in both orders, and counts a win only when both orders agree. Its model is chosen from its agreement with the user's 10 graded pairs in `calibration/`, before any answer here is seen. It flags pairs for the user. It does not decide.
- Regex checks and `ink-prose` must not drop by more than 1 of 3 runs per case against 0.1.4.
- `sight-insight` is reported but not trusted. It passed both answers the user rejected in `evals-holdout-r1-vs-0.1.4`.

## Amendments
- 2026-09-29, before any answer in this suite was seen: the user already graded 0.1.4's h3 run 1 in `evals-holdout-r1-vs-0.1.4`. For h3, both arms use run 2 so the user sees no answer twice. h1 keeps run 1, which they have not seen. "Run n" is the 0-based index, as in `calibration/*/blind-key.json`.
- 2026-09-29, before any answer in this suite was seen: pairwise-judge calibration on the 10 graded pairs came out at 3/10 for both Sonnet and Opus (diagrams only, both orders). A layout-flattening check shows the text judge does perceive alignment (5/5). So the disagreement is about criteria, not perception. A variant also saw the full answers plus the user's taste notes, taken from memos written before `evals-holdout-r1-vs-0.1.4`. Tested on that round, it matched 0 of the 3 pairs where the user preferred one answer, and it again preferred the compressed candidate answers. The pairwise judge is reported only as exploratory and does not select pairs.

## Result (2026-09-29)
The user graded the six pairs blind (`calibration/evals-holdout2-r2-vs-0.1.4/user-grades.txt`). Unblinded:

| Pair | Case | Revision 2 (relation, waste) | 0.1.4 (relation, waste) | Preferred |
|---|---|---|---|---|
| 01 | f1 | O, 0 | O, 1 | revision 2 |
| 02 | f2 | △, 1 | △, 1 | tie |
| 03 | f3 | O, 0 | O, 1 | revision 2 |
| 04 | f4 | O, 0 | O, 1 | 0.1.4 |
| 05 | h1 (dev) | O, 1 | △, 2 | revision 2 |
| 06 | h3 (dev) | O, 0 | O, 1 | revision 2 |

1. Fresh pairs: 2 wins, 1 loss, 1 tie. Holds.
2. No answer was graded X. Holds.
3. Revision 2 won h1 and h3. Holds.

Decision: ship revision 2, released as 0.1.5.

Exploratory, run after grading: the Sonnet pairwise judge (diagrams only, both orders) agreed with the user's preference on 5 of 6 pairs. It picked revision 2 on f2, where the user called a tie. With the earlier 3/10, that makes 8 of 16. This round's winners were also the more compressed answers, which the judge already favored, so this is not evidence that the judge tracks the user.

The user's notes point to the next revision; revision 2 was not changed after grading:
- f2: the user found 0.1.4's drawn layer graph more intuitive than revision 2's adjacency lists. In revision 2's reach paths such as `api → services → domain → infra/sql ✗`, they wanted the violating edge itself marked, not just the end of the path.
- f4: 0.1.4's answer "visualizes better". It had a four-participant sequence plus a hold-versus-work bar chart. Revision 2 had a three-participant sequence and a short busy-time strip.
- h1: in the file tree, use common status letters such as `M` and `A` in place of Korean words.

The f1–f4 answers have now been seen, so these cases are development cases too. The next candidate needs a new holdout suite.
