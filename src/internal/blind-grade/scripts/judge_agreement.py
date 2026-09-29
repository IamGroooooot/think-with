# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Measure how often a pairwise LLM judge agrees with the user's blind preferences.

Exploratory only: the user's grades decide. The judge sees only each answer's
diagrams (fenced blocks and Markdown tables), in both orders, and a side wins
only when both orders agree. The label of a pair is the user's 더나음 when
recorded, else the better relation grade (O > △ > X), then the lower waste.

  judge_agreement.py EVALS_ROOT [--round NAME ...] [--model sonnet] [--list] [--out FILE]

EVALS_ROOT is src/evals/<plugin>; rounds are read from its calibration/ folder.
Each judged pair costs two `claude -p` calls.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blind_round import PREFERENCE, read_grades  # noqa: E402

FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)
BLOCK = re.compile(r"┏━+ (\d\d[AB]) ━+┓\n(.*?)\n┗━+ \1 끝", re.S)
SUITE = re.compile(r"evals(-[a-z0-9-]+)?")
RELATION_RANK = {"O": 2, "△": 1, "X": 0}

PROMPT = """You compare two terminal answers to the same question. Only their diagrams are shown: fenced code blocks and tables, whitespace preserved. All prose outside them was removed. The reader follows Edward Tufte: they want the key relationship visible in the diagram itself, with the least scanning and mental reconstruction.

<question>
{question}
</question>

<key>
What a reader should come away seeing. This is a guide to what matters, not a required form or wording:
{key}
</key>

<answer id="A">
{a}
</answer>

<answer id="B">
{b}
</answer>

Work in order:
1. For each answer, quote the lines where the key relationship is encoded. Say whether layout encodes it (alignment, rows and columns, adjacency, arrows, nesting) or a sentence inside a fence merely asserts it.
2. For each answer, name what the reader must reconstruct to get the key relationship: pairing scattered +/- lines, following a path across rows, inferring edges that are not drawn, decoding notation. Say whether the most consequential fact stands out or is buried among routine details.
3. Note errors or omissions that change the answer, and clutter that slows reading.
4. Decide which answer lets a reader see the key relationship faster and more correctly. Say TIE when the difference is small.

End with exactly one line: VERDICT: A, VERDICT: B, or VERDICT: TIE"""


def diagrams(text: str) -> str:
    """Keep fenced blocks and Markdown table rows, in order, whitespace intact."""
    parts, pos = [], 0
    for match in FENCE.finditer(text):
        parts.extend(tables(text[pos:match.start()]))
        parts.append(match.group(1).rstrip("\n"))
        pos = match.end()
    parts.extend(tables(text[pos:]))
    return "\n\n".join(parts) if parts else "(no diagrams)"


def tables(prose: str) -> list[str]:
    rows, out = [], []
    for line in prose.splitlines():
        if line.lstrip().startswith("|"):
            rows.append(line)
        elif rows:
            out.append("\n".join(rows))
            rows = []
    if rows:
        out.append("\n".join(rows))
    return out


def verdict(reply: str) -> str:
    found = re.findall(r"VERDICT:\s*\**\s*(A|B|TIE)\b", reply)
    return found[-1] if found else "?"


def case_prompt_and_key(evals_root: Path, case: str) -> tuple[str, str]:
    for suite in sorted(evals_root.iterdir()):
        folder = suite / case
        if SUITE.fullmatch(suite.name) and folder.is_dir():
            prompt = re.sub(r"^---\n.*?\n---\n", "", (folder / "prompt.md").read_text(), flags=re.S)
            prompt = re.sub(r"^/\S+\s+", "", prompt.strip())
            insight = folder / "graders" / "sight-insight.md"
            key = insight.read_text().split("Expected insight:", 1)[-1].strip() if insight.exists() else "(not given)"
            return prompt, key
    raise SystemExit(f"no eval case named {case} under {evals_root}")


def label(answers: dict, pairs: dict, pid: str) -> str:
    preferred = PREFERENCE.get(pairs.get(pid, {}).get("better", ""))
    if preferred:
        return preferred
    a, b = answers[pid + "A"], answers[pid + "B"]
    if a["relation"] != b["relation"]:
        return "A" if RELATION_RANK[a["relation"]] > RELATION_RANK[b["relation"]] else "B"
    if a["waste"] != b["waste"]:
        return "A" if int(a["waste"]) < int(b["waste"]) else "B"
    return "tie"


def build_jobs(evals_root: Path, rounds: list[str]) -> list[dict]:
    jobs = []
    for name in rounds:
        folder = evals_root / "calibration" / name
        texts = {m[1]: m[2].strip() for m in BLOCK.finditer((folder / "outputs-blind.md").read_text())}
        answers, pairs = read_grades(folder / "user-grades.txt")
        key = json.loads((folder / "blind-key.json").read_text())
        for pid in sorted({answer[:2] for answer in answers}):
            if not all(answers[pid + side]["relation"] and answers[pid + side]["waste"] for side in "AB"):
                continue
            case = key[pid]["case"]
            question, insight = case_prompt_and_key(evals_root, case)
            jobs.append({"id": f"{name}:{pid}", "case": case, "label": label(answers, pairs, pid),
                         "question": question, "key": insight, "A": texts[pid + "A"], "B": texts[pid + "B"]})
    return jobs


def ask(prompt: str, model: str, workdir: str) -> str:
    result = subprocess.run(
        ["claude", "-p", "--model", model, "--tools", "", "--disable-slash-commands",
         "--no-session-persistence", "--output-format", "text"],
        input=prompt, capture_output=True, text=True, cwd=workdir, timeout=600,
    )
    return result.stdout


def judge(job: dict, model: str, workdir: str) -> dict:
    a, b = diagrams(job["A"]), diagrams(job["B"])
    forward = ask(PROMPT.format(question=job["question"], key=job["key"], a=a, b=b), model, workdir)
    reverse = ask(PROMPT.format(question=job["question"], key=job["key"], a=b, b=a), model, workdir)
    first = {"A": "A", "B": "B", "TIE": "tie"}.get(verdict(forward), "?")
    second = {"A": "B", "B": "A", "TIE": "tie"}.get(verdict(reverse), "?")
    final = first if first == second else "unstable"
    return {"id": job["id"], "case": job["case"], "label": job["label"], "forward": first, "reverse": second,
            "final": final, "agree": final == job["label"], "replies": [forward, reverse]}


def graded_rounds(evals_root: Path) -> list[str]:
    folder = evals_root / "calibration"
    return sorted(p.parent.name for p in folder.glob("*/user-grades.txt"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("evals_root", type=Path)
    parser.add_argument("--round", action="append", dest="rounds", help="calibration round folder name; default: all")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--list", action="store_true", help="print the pairs and labels without calling a judge")
    parser.add_argument("--out", type=Path, help="write verdicts and judge replies as JSON")
    args = parser.parse_args()
    jobs = build_jobs(args.evals_root, args.rounds or graded_rounds(args.evals_root))
    if args.list:
        for job in jobs:
            print(job["id"], job["case"], "label", job["label"])
        return
    with tempfile.TemporaryDirectory(prefix="judge-") as workdir, ThreadPoolExecutor(6) as pool:
        results = list(pool.map(lambda job: judge(job, args.model, workdir), jobs))
    for r in results:
        print(r["id"], "user", r["label"], "judge", r["forward"], r["reverse"], "->", r["final"])
    print(f"agreement: {sum(r['agree'] for r in results)}/{len(results)} ({args.model})")
    if args.out:
        args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
