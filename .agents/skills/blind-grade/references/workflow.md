# Blind-grade workflow

## Names

- Arm labels: a release by its version (`0.1.4`), a candidate as `r1`, `r2`,
  and so on, counted across the plugin's rounds, and `none` for no plugin.
  Once a candidate ships, its label stays and the release version is noted
  next to it in `calibration/README.md`.
- Run output: `plugins/claude/<plugin>/<suite>/results/<arm>/`. A repeated run
  of the same arm gets a suffix, such as `0.1.4-pilot1`. A `with-without` run
  also holds the `none` arm.
- Round folder: `src/evals/<plugin>/calibration/<suite>-<candidate>-vs-<baseline>/`,
  named after the suite that supplies the fresh cases.
- Pair ids are `01`, `02`, ... in pack order. Run indexes are 0-based.

## Run the arms

Freeze the cases and PREREG first. Then run the candidate from the working
tree, after `mise run build`:

```sh
claude plugin eval plugins/claude/<plugin> --eval-dir <suite> --ablation none \
  --judge-model sonnet --no-scaffold --no-publish -j 4 --max-cost-usd <usd> \
  --output-dir plugins/claude/<plugin>/<suite>/results/<arm>
```

For a released baseline, extract its package and add the current suite, which
may be newer than the release:

```sh
tmp=$(mktemp -d)
git archive <release commit> plugins/claude/<plugin> | tar -x -C "$tmp"
cp -R plugins/claude/<plugin>/<suite> "$tmp/plugins/claude/<plugin>/"
rm -rf "$tmp/plugins/claude/<plugin>/<suite>/results"
claude plugin eval "$tmp/plugins/claude/<plugin>" --eval-dir <suite> ... \
  --output-dir plugins/claude/<plugin>/<suite>/results/<version>
```

Use `--ablation with-without` only when one arm is `none`.

## pack.toml

```toml
package = "plugins/claude/think-with"
seed = 20260929
intro = "One paragraph shown above the pairs. Name both arms without saying which side is which."

# label = result folder under <suite>/results/; add ":without" for the none arm of a with-without run.
[arms]
r3 = "r3"
"0.1.5" = "0.1.5"

[[pairs]]
case = "g1-some-case"
suite = "evals-holdout3"
run = 1
summary = "One line telling the user what the question was"
```

The arms are shuffled per pair with `seed`. When the chosen run errored,
`build` takes the next run that did not, and `blind-key.json` records the run
it used.

## Files in a round

- `pack.toml`: the input above.
- `outputs-blind.md`: `# 블라인드 출력: <round>`, the intro, then per pair a
  `# NN · <case>` heading, a `질문:` line, and answers `NNA` and `NNB` between
  `┏━ NNA ━┓` and `┗━ NNA 끝 ━┛` lines, unchanged.
- `blind-key.json`: `{"NN": {"case", "A": arm, "B": arm, "run": {arm: index}}}`.
- `user-grades.txt`: per answer
  `NNA 관계=O|△|X 낭비=0|1|2 형태=O|X| 메모=<one line>`, per pair
  `NN 더나음=A|B|같음`. 관계 is whether the key relationship is visible:
  O exactly, △ with effort, X wrong or not visible. 낭비 is unneeded material:
  0 none, 1 some, 2 clear. 형태 and 메모 are optional.
- The grading page saves each pair to collection `grades`, document `NN`:
  `{"A": {"rel", "waste", "form", "memo"}, "B": {...}, "better", "updatedAt"}`.
  `blind_round.py record` accepts the `ArtifactData` listing with one
  `{"id", "data"}` object per line, or a JSON array of them, and rejects
  values outside the grade scales.

## Ship rule template

Ship the candidate only if all hold:

1. On the fresh pairs, the candidate wins more pairs than it loses.
2. No candidate answer is graded X where the paired baseline answer is O.
3. The candidate does not lose any development regression pair.

State in advance what ships otherwise, such as the baseline plus only a
change that lost nothing.

## Evidence behind the rules

- The user's per-answer grades come before the pair preference, so the
  preference does not color the grades.
- In `evals-holdout-r1-vs-0.1.4`, candidate r1 met all five pre-registered
  automated hypotheses and still lost 0 wins, 2 losses, 3 ties. The
  `sight-insight` judge had passed both losing answers.
- A pairwise LLM judge on diagrams only, run in both orders, agreed with the
  user on 3 of 10 pairs, then 5 of 6: 8 of 16 overall. It prefers compressed
  answers that the user often grades worse.
- Checklist rubrics in which every item must hold fail almost every answer
  and carry no signal. Keep an LLM grader to one holistic question, and trust
  it only after it matches held-out user grades.
- After an answer to a case has been seen, the case can shape the next
  candidate, so it cannot test that candidate.
