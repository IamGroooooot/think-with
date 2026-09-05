"""Exercise command exit codes and filesystem effects in an isolated checkout."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build import ROOT


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="think-with-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "checkout"
        self.root.mkdir()
        for name in ("scripts", "adapters"):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(Path(__file__).parent / "fixtures/catalog.toml", self.root / "catalog.toml")
        self.source = self.root / "src/internal/sample"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: sample\ndescription: Test skill\n---\nInspect input.\n")
        (self.root / "tests").mkdir()
        (self.root / "tests/test_example.py").write_text(
            "import unittest\nclass Example(unittest.TestCase):\n    def test_example(self):\n        self.assertTrue(True)\n"
        )
        self.assertEqual(self.run_cli("build").returncode, 0)

    def test_check_passes_from_an_unrelated_working_directory_without_writes(self):
        before = self.snapshot()
        result = self.run_cli("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tests passed", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_check_rejects_changed_generated_file_without_repair(self):
        (self.root / ".agents/skills/sample/SKILL.md").write_text("stale")
        self.assert_rejected_without_writes("check", "changed: .agents/skills/sample/SKILL.md")

    def test_check_rejects_missing_generated_file_without_repair(self):
        (self.root / ".claude/skills/sample/SKILL.md").unlink()
        self.assert_rejected_without_writes("check", "missing: .claude/skills/sample/SKILL.md")

    def test_check_returns_failure_when_the_test_suite_fails(self):
        test = self.root / "tests/test_example.py"
        test.write_text(test.read_text().replace("assertTrue(True)", "assertTrue(False)"))
        before = self.snapshot()
        result = self.run_cli("check")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("FAILED", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_yaml_has_a_diagnostic_without_writes(self):
        (self.source / "SKILL.md").write_text("---\nname: [\n---\n")
        for command in ("build", "check"):
            with self.subTest(command=command):
                self.assert_rejected_without_writes(command, f"{command}:")

    def test_malformed_catalog_has_a_diagnostic_without_writes(self):
        (self.root / "catalog.toml").write_text("[marketplace\n")
        for command in ("build", "check"):
            with self.subTest(command=command):
                self.assert_rejected_without_writes(command, f"{command}:")

    def test_inspect_reports_inventory_and_rejects_a_non_skill_directory(self):
        before = self.snapshot()
        result = self.run_cli("inspect_skill", self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"path": "SKILL.md"', result.stdout)
        result = self.run_cli("inspect_skill", self.root)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("source must be a skill directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_table_shapes_have_diagnostics_without_writes(self):
        for config in ('[codex]\nblocks = 1\n', '[codex]\nopenai = "bad"\n'):
            (self.source / "skill.toml").write_text(config)
            for command in ("build", "check"):
                with self.subTest(config=config, command=command):
                    self.assert_rejected_without_writes(command, "must be a table")

    def test_invalid_python_helper_has_a_diagnostic_without_writes(self):
        (self.source / "skill.toml").write_text('files = ["scripts/helper.py"]\n')
        (self.source / "scripts").mkdir()
        (self.source / "scripts/helper.py").write_text(
            '# /// script\n# requires-python = ">=3.12"\n# dependencies = []\n# ///\nif\n'
        )
        for command in ("build", "check"):
            with self.subTest(command=command):
                self.assert_rejected_without_writes(command, "invalid syntax")

    def assert_rejected_without_writes(self, command, message):
        before = self.snapshot()
        result = self.run_cli(command)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def run_cli(self, command, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / f"{command}.py"), *map(str, args)],
            cwd=self.temp.name, capture_output=True, text=True, timeout=15,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
