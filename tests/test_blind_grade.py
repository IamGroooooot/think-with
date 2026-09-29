"""Exercise the blind-grade scripts on synthetic eval results and rounds."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build import ROOT

SCRIPTS = ROOT / "src/internal/blind-grade/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS))
    written, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SCRIPTS))
        sys.dont_write_bytecode = written
    return module


def results(folder, cases):
    """Write aggregate-result.json; cases maps name -> {arm: [answer or None for an errored run]}."""
    folder.mkdir(parents=True)
    data = {"cases": [
        {"name": name, "arms": {arm: [{"error": "boom"} if a is None else {"graders": [{"evidence": a}]} for a in runs]
                                for arm, runs in arms.items()}}
        for name, arms in cases.items()
    ]}
    (folder / "aggregate-result.json").write_text(json.dumps(data))


class BlindGradeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="blind-grade-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.package = self.root / "package"
        suite = self.package / "evals-x" / "results"
        results(suite / "r9", {"c1-case": {"with": ["r9 answer c1 run0", None, "r9 answer c1 run2"]},
                               "c2-case": {"with": ["r9 answer c2 run0", "r9 answer c2 run1"]}})
        results(suite / "0.1.9", {"c1-case": {"with": ["base c1 run0", "base c1 run1", "base c1 run2"],
                                              "without": ["bare c1 run0", "bare c1 run1"]},
                                  "c2-case": {"with": ["base c2 run0", "base c2 run1"]}})
        self.round = self.root / "calibration" / "evals-x-r9-vs-0.1.9"
        self.round.mkdir(parents=True)
        self.write_pack({"r9": "r9", "0.1.9": "0.1.9"})

    def write_pack(self, arms):
        arm_lines = "\n".join(f'"{label}" = "{source}"' for label, source in arms.items())
        (self.round / "pack.toml").write_text(
            f'package = "{self.package.as_posix()}"\nseed = 7\nintro = "Two arms, hidden order."\n\n'
            f"[arms]\n{arm_lines}\n\n"
            '[[pairs]]\ncase = "c1-case"\nsuite = "evals-x"\nrun = 1\nsummary = "첫 질문"\n\n'
            '[[pairs]]\ncase = "c2-case"\nsuite = "evals-x"\nrun = 0\nsummary = "둘째 질문"\n'
        )

    def run_script(self, name, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / f"{name}.py"), *map(str, args)],
                              capture_output=True, text=True, cwd=self.root)

    def build(self):
        result = self.run_script("blind_round", "build", self.round)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.round / "blind-key.json").read_text())

    def grade(self, text):
        (self.round / "user-grades.txt").write_text(text)

    def test_build_writes_a_blind_pack_and_skips_errored_runs(self):
        key = self.build()
        self.assertEqual(set(key), {"01", "02"})
        self.assertEqual(sorted((key["01"]["A"], key["01"]["B"])), ["0.1.9", "r9"])
        self.assertEqual(key["01"]["run"]["r9"], 2)
        self.assertEqual(key["01"]["run"]["0.1.9"], 1)
        pack = (self.round / "outputs-blind.md").read_text()
        self.assertTrue(pack.startswith("# 블라인드 출력: evals-x-r9-vs-0.1.9\n\nTwo arms, hidden order.\n"))
        self.assertIn("# 01 · c1-case\n질문: 첫 질문", pack)
        self.assertIn("r9 answer c1 run2", pack)
        self.assertNotIn("r9", pack.replace("r9 answer", "").replace("evals-x-r9", ""))
        self.assertEqual((self.round / "user-grades.txt").read_text().splitlines()[:3],
                         ["01A 관계= 낭비= 형태= 메모=", "01B 관계= 낭비= 형태= 메모=", "01 더나음="])

    def test_build_is_reproducible_and_refuses_to_overwrite(self):
        self.build()
        first = (self.round / "outputs-blind.md").read_text()
        result = self.run_script("blind_round", "build", self.round)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        for name in ("outputs-blind.md", "blind-key.json", "user-grades.txt"):
            (self.round / name).unlink()
        self.build()
        self.assertEqual((self.round / "outputs-blind.md").read_text(), first)

    def test_build_reads_the_no_plugin_arm_of_a_with_without_run(self):
        self.write_pack({"0.1.9": "0.1.9", "none": "0.1.9:without"})
        (self.round / "pack.toml").write_text((self.round / "pack.toml").read_text().split("\n\n[[pairs]]")[0]
                                              + '\n\n[[pairs]]\ncase = "c1-case"\nsuite = "evals-x"\nrun = 1\nsummary = "q"\n')
        key = self.build()
        self.assertEqual(key["01"]["run"]["none"], 1)
        self.assertIn("bare c1 run1", (self.round / "outputs-blind.md").read_text())

    def test_record_turns_page_documents_into_grades_and_rejects_bad_values(self):
        self.build()
        doc = {"A": {"rel": "O", "waste": "0", "form": "", "memo": " 좋음\n  아주 "},
               "B": {"rel": "△", "waste": "2", "form": "X", "memo": ""}, "better": "A", "updatedAt": "t"}
        docs = self.root / "docs.txt"
        docs.write_text("1 documents\n=== BEGIN ===\n" + json.dumps({"id": "01", "data": doc, "version": 3},
                                                                     ensure_ascii=False) + "\n=== END ===\n")
        result = self.run_script("blind_round", "record", self.round, docs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1/2 pairs complete", result.stdout)
        self.assertEqual((self.round / "user-grades.txt").read_text().splitlines(), [
            "01A 관계=O 낭비=0 형태= 메모=좋음 아주", "01B 관계=△ 낭비=2 형태=X 메모=", "01 더나음=A",
            "02A 관계= 낭비= 형태= 메모=", "02B 관계= 낭비= 형태= 메모=", "02 더나음=",
        ])
        for bad in ({"id": "01", "data": {**doc, "better": "C"}}, {"id": "01", "data": {**doc, "A": {"rel": "maybe"}}},
                    {"id": "09", "data": doc}):
            docs.write_text(json.dumps([bad]))
            self.assertNotEqual(self.run_script("blind_round", "record", self.round, docs).returncode, 0)

    def test_unblind_refuses_incomplete_grades_then_tallies_by_arm(self):
        key = self.build()
        self.grade("01A 관계=O 낭비=0 형태= 메모=\n01B 관계=X 낭비=1 형태= 메모=\n01 더나음=A\n"
                   "02A 관계=O 낭비=1 형태= 메모=\n02B 관계= 낭비= 형태= 메모=\n02 더나음=\n")
        result = self.run_script("blind_round", "unblind", self.round)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("02B", result.stderr)
        self.grade("01A 관계=O 낭비=0 형태= 메모=\n01B 관계=X 낭비=1 형태= 메모=\n01 더나음=A\n"
                   "02A 관계=O 낭비=1 형태= 메모=\n02B 관계=O 낭비=0 형태= 메모=\n02 더나음=같음\n")
        result = self.run_script("blind_round", "unblind", self.round)
        self.assertEqual(result.returncode, 0, result.stderr)
        winner, loser = key["01"]["A"], key["01"]["B"]
        self.assertIn(f"{winner}: wins 1, losses 0, ties 1", result.stdout)
        self.assertIn(f"{loser}: wins 0, losses 1, ties 1", result.stdout)
        self.assertIn(f"X where the other answer is O: 01B ({loser})", result.stdout)

    def test_grading_page_uses_only_the_pack_and_escapes_answers(self):
        self.round.joinpath("outputs-blind.md").write_text(
            "# 블라인드 출력: r\n\nIntro **bold**.\n\n---\n\n# 01 · c1-case\n질문: 무엇이 바뀌나\n\n"
            "┏━━ 01A ━━┓\n\n<script>alert(1)</script> and `a</script>`\n\n```diff\n- old\n+ 새 값\n context\n```\n\n"
            "┗━━ 01A 끝 ━━┛\n\n┏━━ 01B ━━┓\n\n| a | b |\n|---|--:|\n| 1 | 2 |\n\n- item\n  - nested\n\n┗━━ 01B 끝 ━━┛\n"
        )
        out = self.root / "page.html"
        result = self.run_script("grading_page", self.round, out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.round / "blind-key.json").exists())
        page = out.read_text()
        self.assertNotIn("{{", page)
        self.assertNotIn("<script>alert", page)
        self.assertEqual(page.count("</script>"), 1)
        self.assertIn('<span class="dl del">- old</span>', page)
        self.assertIn('<span class="dl add">+ <span class="c2"><i>새</i></span> <span class="c2"><i>값</i></span></span>', page)
        self.assertIn('<td style="text-align:right">2</td>', page)
        self.assertIn("<ul><li>item<ul><li>nested</li></ul></li></ul>", page)
        self.assertIn('const PAIRS = ["01"]', page)
        self.assertIn('name="01A-rel"', page)

    def test_markdown_follows_commonmark_emphasis_and_escapes(self):
        page = load("grading_page")
        self.assertEqual(page.inline("**`GET /x`가 바뀜**입니다"), "<strong><code>GET /x</code>가 바뀜</strong>입니다")
        self.assertEqual(page.inline("add_middleware 를 **바깥쪽(먼저)**이 됨"), "add_middleware 를 **바깥쪽(먼저)**이 됨")
        self.assertEqual(page.inline(r"\* 3 × timeout"), "* 3 × timeout")
        self.assertEqual(page.markdown("a  \nb\nc"), "<p>a<br>\nb\nc</p>")

    def test_judge_lists_labels_and_reads_verdicts(self):
        self.build()
        case = self.root / "evals-x" / "c1-case"
        (case / "graders").mkdir(parents=True)
        (case / "prompt.md").write_text("---\nx: 1\n---\n/think-with:lay-out what changed?\n")
        (case / "graders" / "sight-insight.md").write_text("Grade it.\nExpected insight: the key change")
        (self.root / "evals-x" / "c2-case").mkdir()
        (self.root / "evals-x" / "c2-case" / "prompt.md").write_text("second\n")
        self.grade("01A 관계=△ 낭비=0 형태= 메모=\n01B 관계=O 낭비=0 형태= 메모=\n01 더나음=\n"
                   "02A 관계=O 낭비=0 형태= 메모=\n02B 관계=O 낭비=0 형태= 메모=\n02 더나음=A\n")
        result = self.run_script("judge_agreement", self.root, "--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["evals-x-r9-vs-0.1.9:01 c1-case label B",
                                                      "evals-x-r9-vs-0.1.9:02 c2-case label A"])
        judge = load("judge_agreement")
        self.assertEqual(judge.case_prompt_and_key(self.root, "c1-case"), ("what changed?", "the key change"))
        self.assertEqual(judge.verdict("reasoning\nVERDICT: A\nlater VERDICT: **TIE**"), "TIE")
        self.assertEqual(judge.diagrams("prose\n```\nx → y\n```\n| a |\n|---|\nmore"), "x → y\n\n| a |\n|---|")


if __name__ == "__main__":
    unittest.main()
