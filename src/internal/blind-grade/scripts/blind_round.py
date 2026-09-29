# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Build a blind grading pack from two eval arms, record the user's grades, or unblind a graded round.

  build ROUND_DIR          read ROUND_DIR/pack.toml; write outputs-blind.md, blind-key.json, user-grades.txt
  record ROUND_DIR DOCS    rewrite user-grades.txt from grading-page documents saved to the file DOCS
  unblind ROUND_DIR        read blind-key.json and user-grades.txt; print each pair with its arms and a tally

Paths inside pack.toml are relative to the working directory, normally the repository root.
"""

import argparse
import json
import random
import re
import sys
import tomllib
from pathlib import Path

OUTPUTS = ("outputs-blind.md", "blind-key.json", "user-grades.txt")
ANSWER_LINE = re.compile(r"^(\d\d)([AB]) 관계=(\S*) 낭비=(\S*) 형태=(\S*) 메모=(.*)$")
PAIR_LINE = re.compile(r"^(\d\d) 더나음=(\S*)$")
RELATION = ("O", "△", "X")
ALLOWED = {"rel": {"", *RELATION}, "waste": {"", "0", "1", "2"}, "form": {"", "O", "X"}}
PREFERENCE = {"A": "A", "B": "B", "같음": "tie"}


def load_answer(results: Path, arm: str, case: str, run: int) -> tuple[str, int]:
    """Return the answer to `case` at 0-based `run`, or at the next run without an error."""
    data = json.loads((results / "aggregate-result.json").read_text())
    runs = next((c for c in data["cases"] if c["name"] == case), None)
    if runs is None:
        raise SystemExit(f"{results}: no case named {case}")
    runs = runs["arms"].get(arm, [])
    for index in [*range(run, len(runs)), *range(min(run, len(runs)))]:
        if runs[index].get("error"):
            continue
        for grader in runs[index].get("graders", []):
            if grader.get("evidence"):
                return grader["evidence"].strip(), index
    raise SystemExit(f"{results}: no {arm} answer for {case}")


def grade_lines(pid: str, grade: dict | None = None) -> list[str]:
    grade = grade or {}
    lines = []
    for side in "AB":
        g = grade.get(side, {})
        lines.append(f"{pid}{side} 관계={g.get('rel', '')} 낭비={g.get('waste', '')} "
                     f"형태={g.get('form', '')} 메모={g.get('memo', '')}")
    return lines + [f"{pid} 더나음={grade.get('better', '')}"]


def build(round_dir: Path) -> None:
    existing = [name for name in OUTPUTS if (round_dir / name).exists()]
    if existing:
        raise SystemExit(f"refusing to overwrite {', '.join(existing)} in {round_dir}")
    spec = tomllib.loads((round_dir / "pack.toml").read_text())
    arms = spec["arms"]
    if len(arms) != 2:
        raise SystemExit("pack.toml needs exactly two arms")
    package = Path(spec["package"])
    rng = random.Random(spec["seed"])
    doc = [f"# 블라인드 출력: {round_dir.name}", "", spec["intro"].strip(), ""]
    key, grades = {}, []
    for number, pair in enumerate(spec["pairs"], 1):
        pid = f"{number:02d}"
        texts = {}
        for label, source in arms.items():
            results, _, arm = source.partition(":")
            texts[label] = load_answer(package / pair["suite"] / "results" / results, arm or "with",
                                       pair["case"], pair["run"])
        order = list(arms)
        rng.shuffle(order)
        key[pid] = {"case": pair["case"], "A": order[0], "B": order[1], "run": {arm: texts[arm][1] for arm in order}}
        doc += ["---", "", f"# {pid} · {pair['case']}", f"질문: {pair['summary']}", ""]
        for side, arm in zip("AB", order):
            doc += [f"┏━━━━━━━━━━━━━━━━ {pid}{side} ━━━━━━━━━━━━━━━━┓", "", texts[arm][0], "",
                    f"┗━━━━━━━━━━━━━━━━ {pid}{side} 끝 ━━━━━━━━━━━━━━┛", ""]
        grades += grade_lines(pid)
    (round_dir / "outputs-blind.md").write_text("\n".join(doc) + "\n")
    (round_dir / "blind-key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n")
    (round_dir / "user-grades.txt").write_text("\n".join(grades) + "\n")
    print(f"wrote {len(key)} pairs to {round_dir}")


def read_grades(path: Path) -> tuple[dict, dict]:
    answers, pairs = {}, {}
    for line in path.read_text().splitlines():
        if m := ANSWER_LINE.match(line):
            answers[m[1] + m[2]] = {"relation": m[3], "waste": m[4], "form": m[5], "memo": m[6].strip()}
        elif m := PAIR_LINE.match(line):
            pairs[m[1]] = {"better": m[2]}
        elif line.strip():
            raise SystemExit(f"{path}: unreadable line: {line}")
    return answers, pairs


def read_documents(path: Path) -> dict:
    """Parse grading-page documents: a JSON array, or one {"id", "data"} object per line among other text."""
    text = path.read_text()
    try:
        docs = json.loads(text)
    except json.JSONDecodeError:
        docs = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
    return {doc["id"]: doc["data"] for doc in docs}


def clean(grade: dict, pid: str) -> dict:
    """Keep only valid grade values; the documents were written by page viewers."""
    out = {}
    for side in "AB":
        g = grade.get(side) if isinstance(grade.get(side), dict) else {}
        out[side] = {}
        for field, allowed in ALLOWED.items():
            value = g.get(field, "")
            if value not in allowed:
                raise SystemExit(f"pair {pid}{side}: invalid {field} {value!r}")
            out[side][field] = value
        out[side]["memo"] = " ".join(str(g.get("memo", "")).split())
    if grade.get("better", "") not in {"", *PREFERENCE}:
        raise SystemExit(f"pair {pid}: invalid preference {grade['better']!r}")
    out["better"] = grade.get("better", "")
    return out


def record(round_dir: Path, docs_path: Path) -> None:
    answers, _ = read_grades(round_dir / "user-grades.txt")
    ids = sorted({answer[:2] for answer in answers})
    docs = read_documents(docs_path)
    unknown = sorted(set(docs) - set(ids))
    if unknown:
        raise SystemExit(f"documents for pairs not in this round: {', '.join(unknown)}")
    lines = []
    for pid in ids:
        lines += grade_lines(pid, clean(docs[pid], pid) if pid in docs else None)
    (round_dir / "user-grades.txt").write_text("\n".join(lines) + "\n")
    answers, pairs = read_grades(round_dir / "user-grades.txt")
    done = sum(all(answers[pid + s]["relation"] and answers[pid + s]["waste"] for s in "AB")
               and bool(pairs[pid]["better"]) for pid in ids)
    print(f"recorded {len(docs)} documents; {done}/{len(ids)} pairs complete")


def unblind(round_dir: Path) -> None:
    key = json.loads((round_dir / "blind-key.json").read_text())
    answers, pairs = read_grades(round_dir / "user-grades.txt")
    ids = sorted({answer[:2] for answer in answers})
    missing = [f"{pid}{side}" for pid in ids for side in "AB"
               if not (answers.get(pid + side, {}).get("relation") and answers.get(pid + side, {}).get("waste"))]
    missing += [pid for pid, pair in pairs.items() if not pair["better"]]
    if missing:
        raise SystemExit(f"grades are incomplete ({', '.join(missing)}); finish grading before unblinding")
    tally = {}
    rows = ["| Pair | Case | A | B | Preferred |", "|---|---|---|---|---|"]
    for pid in ids:
        arm = {side: key[pid][side] for side in "AB"}
        cells = {}
        for side in "AB":
            grade = answers[pid + side]
            stats = tally.setdefault(arm[side], {"win": 0, "loss": 0, "tie": 0, "waste": 0, **{r: 0 for r in RELATION}})
            stats[grade["relation"]] += 1
            stats["waste"] += int(grade["waste"])
            cells[side] = f"{arm[side]} ({grade['relation']}, {grade['waste']})"
        preferred = PREFERENCE.get(pairs.get(pid, {}).get("better", ""), "")
        if preferred in ("A", "B"):
            other = "B" if preferred == "A" else "A"
            tally[arm[preferred]]["win"] += 1
            tally[arm[other]]["loss"] += 1
            shown = arm[preferred]
        elif preferred == "tie":
            for side in "AB":
                tally[arm[side]]["tie"] += 1
            shown = "tie"
        else:
            shown = "-"
        rows.append(f"| {pid} | {key[pid]['case']} | {cells['A']} | {cells['B']} | {shown} |")
    print("\n".join(rows))
    print()
    for name, stats in tally.items():
        relations = " ".join(f"{r}{stats[r]}" for r in RELATION)
        print(f"{name}: wins {stats['win']}, losses {stats['loss']}, ties {stats['tie']}; "
              f"relation {relations}; waste total {stats['waste']}")
    x_against_o = [f"{pid}{side} ({key[pid][side]})" for pid in ids for side, other in ("AB", "BA")
                   if answers[pid + side]["relation"] == "X" and answers[pid + other]["relation"] == "O"]
    print("X where the other answer is O: " + (", ".join(x_against_o) if x_against_o else "none"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("build", "record", "unblind"))
    parser.add_argument("round_dir", type=Path)
    parser.add_argument("docs", type=Path, nargs="?", help="record only: the saved grading-page documents")
    args = parser.parse_args()
    if not args.round_dir.is_dir():
        parser.exit(1, f"not a directory: {args.round_dir}\n")
    if args.command == "record":
        if args.docs is None:
            parser.error("record needs the documents file")
        record(args.round_dir, args.docs)
    elif args.docs is not None:
        parser.error(f"{args.command} takes only the round directory")
    else:
        build(args.round_dir) if args.command == "build" else unblind(args.round_dir)


if __name__ == "__main__":
    sys.exit(main())
