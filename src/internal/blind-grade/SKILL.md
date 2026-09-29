---
name: blind-grade
description: Compare a candidate version of a think-with skill against a baseline through the user's blind grades. Use to pre-register, run, pack, grade, and unblind a calibration round.
---

# Blind-grade a skill candidate

Work from the repository root. The user's blind grades decide whether a
candidate ships. Automated graders and LLM judges only triage: in past rounds
they passed answers the user rejected and matched the user's preference in
half the pairs. Read [the workflow reference](references/workflow.md) for
names, commands, file formats, and the evidence behind each rule.

## Before anyone sees an answer

1. Use cases whose answers nobody has seen. Once answers to a case are graded
   or inspected, that case is a development case. A new candidate needs a new
   holdout suite, written before the candidate.
2. Write `src/evals/<plugin>/<suite>/PREREG.md`: the candidate's changes, the
   frozen arms and runs, which run index each blind pair uses, and the ship
   rule. Record any later change under Amendments with its date and whether an
   answer had been seen.

{{tw:ask-user}}

Confirm the arms, suites, blind pairs, and ship rule with the user before
spending on eval runs.

## Run and pack

3. Run each arm with `claude plugin eval`, writing to
   `plugins/claude/<plugin>/<suite>/results/<arm>/`. Run a released baseline
   from a `git archive` of its commit.
4. Write `pack.toml` in the round folder
   `src/evals/<plugin>/calibration/<suite>-<candidate>-vs-<baseline>/`, then
   run [blind_round.py](scripts/blind_round.py) `build <round dir>`. It writes
   `outputs-blind.md`, `blind-key.json`, and an empty `user-grades.txt`, and
   refuses to overwrite them.

## Grade with the user

Until every pair is graded, do not open `blind-key.json`, the result
folders, or grader verdicts for these cases. Do not comment on the answers,
hint at arms, or report automated scores while the user grades.

{{tw:grade}}

## Unblind and record

5. Run [blind_round.py](scripts/blind_round.py) `unblind <round dir>`. It
   refuses while any grade is missing, then prints each pair's arms, the
   preferred arm, per-arm wins, relation and waste totals, and any answer
   graded X against an O.
6. Apply the pre-registered rule exactly as written. Add a Result section to
   the suite's PREREG, a row for the round to
   `src/evals/<plugin>/calibration/README.md`, and the user's notes as
   candidates for the next revision. Do not change the graded candidate after
   the fact.
7. Optionally run [judge_agreement.py](scripts/judge_agreement.py) to see how
   an LLM judge agrees with the new grades. Report it as exploratory.

Then run `mise run build` and `mise run check`. Commit or release only when
the user asks.
