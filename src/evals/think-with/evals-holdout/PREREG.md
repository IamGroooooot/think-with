# lay-out revision: pre-registration

Written 2026-09-29, before the skill is edited or any held-out case is run.

## Frozen
- Judge: `--judge-model sonnet`, 3 votes. Grader texts are the ones in `evals/` and `evals-holdout/` at this commit.
- Baseline: plugin 0.1.4, full run `evals/results/2026-09-29T10-59-42-291Z`.
- Held-out cases: `evals-holdout/h1..h4`. Each is run once on the candidate (with and without the plugin) and once on 0.1.4 (with the plugin only). Nothing is tuned on them.

## Candidate changes
- B: the file-change step becomes conditional on a diff or PR, with a reason. The explicit "not applicable" wording is removed.
- D1: the dependency form becomes aggregate → order by layer or entry point → show only the breaking edges, or a from/to matrix when there are many nodes.
- D2: swimlane is removed, and handoffs go to the sequence form (roles as columns).
- V: one main view by default; one view per named concern; off-path parts are collapsed; changes are marked in place on one shared structure.
- N: the data-flow notation uses plain names, and edge labels say what moves and when.
- G: a governing goal goes first ("the key relationship from the diagrams alone").

## Hypotheses (grader named; decided before results)
1. B: boilerplate regex fires in ≤ 1 of 9 with-plugin runs on 03, 04 and 05 (baseline 5 of 9), and in 0 of 9 on h2, h3 and h4. `ink-prose` on 01 and 02 with the plugin stays at ≥ 5 of 6 (baseline 6 of 6).
2. D1: 05 with the plugin passes `ink-prose` at ≥ 3 of 3 (baseline 2 of 3), and `cycle-found` stays at 3 of 3. On h3, the candidate is not below 0.1.4 on `ink-prose` or `sight-insight`.
3. D2: on h4, the candidate is not below 0.1.4 on `ink-prose` or `sight-insight`.
4. V: `fence-cap` failures with the plugin on 01–05 are ≤ 1 of 15 (baseline 1 of 15).
5. Overall, on the dev cases: the with-plugin `ink-prose` pass rate for the candidate minus 0.1.4, paired per case and clustered by case, has a mean ≥ 0. No case drops by more than 1 of 3.

## Power (planning assumption)
If the per-case SD of the paired difference is similar to the baseline's (≈ 0.53), then with 6 dev cases only differences of ≈ 0.77 are detectable at 80% power. With 4 held-out cases the multiplier is ≈ 4.2 × SE, so it is larger still. The held-out run therefore checks for regressions and generalization. It cannot confirm modest gains. Large-effect regex counts (hypothesis 1) are the primary outcome.

## Also
- The user blind-grades an interleaved sample of held-out outputs, candidate vs 0.1.4, with labels hidden.
- `sight-insight` is exploratory: 7 of 10 agreement with the user's grades.

## Amendments
- 2026-09-29, after the held-out run: the h3 `sight-insight` expected insight named a second violating edge, apps/web → db, that the h3 prompt does not contain. That edge was removed from the grader. The pre-registered h3 `sight-insight` results are invalid for every arm.
