"""Behavioral packaging checks. All mutations are confined to temporary roots."""

import json
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from build import (
    ROOT, INDEX, parse_frontmatter, output_differences, render_repository,
    render_skill, validate_script, write_outputs,
)
from inspect_skill import inspect


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="think-with-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copyfile(Path(__file__).parent / "fixtures/catalog.toml", self.root / "catalog.toml")
        shutil.copytree(ROOT / "adapters", self.root / "adapters")

    def test_empty_scaffold_has_installable_manifests_without_fake_skills(self):
        output = render_repository(self.root)
        self.assertFalse(any("/skills/" in path for path in output))
        for platform in ("claude", "codex"):
            manifest = json.loads(output[f"plugins/{platform}/think-with/.{platform}-plugin/plugin.json"])
            self.assertEqual(manifest["name"], "think-with")
            self.assertNotIn("skills", manifest)

    def test_internal_skills_never_enter_plugins(self):
        self.create_skill("maintain", internal=True)
        (self.root / "src/internal/README.md").write_text("Project-only skills.\n")
        output = render_repository(self.root)
        self.assertIn(".claude/skills/maintain/SKILL.md", output)
        self.assertIn(".agents/skills/maintain/SKILL.md", output)
        self.assertFalse(any("plugins/" in path and "maintain" in path for path in output))
        self.assertFalse(any(path.endswith("README.md") for path in output))

    def test_explicit_policy_and_question_block_are_adapted_together(self):
        source = self.create_skill(body="{{tw:ask-user}}\n", config='invocation = "explicit"\n')
        claude = render_skill(self.root, source, "claude")
        codex = render_skill(self.root, source, "codex")
        claude_metadata, claude_body = parse_frontmatter(claude["SKILL.md"].decode())
        codex_metadata, codex_body = parse_frontmatter(codex["SKILL.md"].decode())
        self.assertEqual(claude_metadata["name"], codex_metadata["name"])
        self.assertTrue(claude_metadata["disable-model-invocation"])
        self.assertNotIn("disable-model-invocation", codex_metadata)
        self.assertIn("AskUserQuestion", claude_body)
        self.assertIn("request_user_input", codex_body)
        self.assertNotIn("AskUserQuestion", codex_body)
        self.assertEqual(yaml.safe_load(codex["agents/openai.yaml"])["policy"], {"allow_implicit_invocation": False})

    def test_default_invocation_does_not_disable_discovery(self):
        source = self.create_skill()
        self.assertNotIn("agents/openai.yaml", render_skill(self.root, source, "codex"))
        metadata, _ = parse_frontmatter(render_skill(self.root, source, "claude")["SKILL.md"].decode())
        self.assertNotIn("disable-model-invocation", metadata)

    def test_platform_metadata_and_override_do_not_leak(self):
        source = self.create_skill(body="{{tw:ask-user}}\n", config='''
[claude.frontmatter]
argument-hint = "[input]"
[codex.blocks]
ask-user = "Ask in chat."
[codex.openai.interface]
display_name = "Sample"
''')
        claude_metadata, _ = parse_frontmatter(render_skill(self.root, source, "claude")["SKILL.md"].decode())
        codex = render_skill(self.root, source, "codex")
        codex_metadata, codex_body = parse_frontmatter(codex["SKILL.md"].decode())
        self.assertEqual(claude_metadata["argument-hint"], "[input]")
        self.assertNotIn("argument-hint", codex_metadata)
        self.assertEqual(codex_body.strip(), "Ask in chat.")
        self.assertEqual(yaml.safe_load(codex["agents/openai.yaml"])["interface"]["display_name"], "Sample")

    def test_unknown_or_inline_blocks_fail_instead_of_shipping(self):
        for body in ("{{tw:unknown}}\n", "Use {{tw:ask-user}} now.\n"):
            with self.subTest(body=body):
                source = self.create_skill(name="case-" + ("one" if "unknown" in body else "two"), body=body)
                with self.assertRaises(ValueError):
                    render_skill(self.root, source, "codex")

    def test_literal_tool_names_and_user_assets_are_unchanged(self):
        source = self.create_skill(body="Explain the string AskUserQuestion in this example.\n", config='files = ["assets/app.js"]\n')
        (source / "assets").mkdir()
        asset = b"const template = '{{tw:example}}';\n"
        (source / "assets/app.js").write_bytes(asset)
        output = render_skill(self.root, source, "codex")
        self.assertIn(b"AskUserQuestion", output["SKILL.md"])
        self.assertEqual(output["assets/app.js"], asset)

    def test_required_transitive_reference_is_checked(self):
        source = self.create_skill(body="Read [index](references/index.md).\n", config='files = ["references/index.md"]\n')
        (source / "references").mkdir()
        (source / "references/index.md").write_text("Read [chapter](chapter.md).\n")
        with self.assertRaisesRegex(ValueError, "missing bundled link"):
            render_skill(self.root, source, "codex")
        (source / "references/chapter.md").write_text("Required source.\n")
        (source / "skill.toml").write_text('files = ["references/index.md", "references/chapter.md"]\n')
        output = render_skill(self.root, source, "codex")
        self.assertIn("references/chapter.md", output)

    def test_relative_links_resolve_from_each_reference(self):
        source = self.create_skill(
            body="Read [guide](references/nested/guide.md). [Web](https://example.invalid)\n",
            config='files = ["references/nested/guide.md", "references/shared notes.md"]\n',
        )
        (source / "references/nested").mkdir(parents=True)
        (source / "references/nested/guide.md").write_text(
            "[Notes](../shared%20notes.md#section)\n[Again][notes]\n"
            "[notes]: <../shared notes.md>\n[Here](#section)\n"
            "```md\n[Example](missing.md)\n```\n"
        )
        (source / "references/shared notes.md").write_text("# Section\nShared notes.\n")
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                output = render_skill(self.root, source, platform)
                self.assertEqual(output["references/shared notes.md"], b"# Section\nShared notes.\n")

    def test_root_escape_and_absolute_resource_links_fail(self):
        for index, target in enumerate(("../outside.md", "/Users/someone/book.md", "file:///tmp/book.md", "skill://other-skill/reference")):
            with self.subTest(target=target):
                source = self.create_skill(name=f"case-{index}", body=f"Read [book]({target}).\n")
                with self.assertRaises(ValueError):
                    render_skill(self.root, source, "claude")

    def test_only_selected_runtime_files_and_legal_notices_are_bundled(self):
        source = self.create_skill()
        (source / "LICENSE").write_text("Keep original terms.\n")
        (source / "evals").mkdir()
        (source / "evals/report.json").write_text("{}")
        (source / "README.md").write_text("Development setup.\n")
        output = render_skill(self.root, source, "codex")
        self.assertEqual(set(output), {"SKILL.md", "LICENSE"})
        (source / "skill.toml").write_text('files = ["evals/report.json"]\n')
        with self.assertRaisesRegex(ValueError, "development-only"):
            render_skill(self.root, source, "codex")

    def test_symlinks_and_path_traversal_are_rejected(self):
        source = self.create_skill(config='files = ["references/linked.md"]\n')
        (source / "references").mkdir()
        (self.root / "outside.md").write_text("outside")
        (source / "references/linked.md").symlink_to(self.root / "outside.md")
        with self.assertRaisesRegex(ValueError, "symlink"):
            render_skill(self.root, source, "codex")
        (source / "skill.toml").write_text('files = ["../outside.md"]\n')
        with self.assertRaisesRegex(ValueError, "inside its root"):
            render_skill(self.root, source, "codex")

    def test_unknown_configuration_fails_instead_of_dropping_behavior(self):
        source = self.create_skill(config='invocaton = "explicit"\n')
        with self.assertRaisesRegex(ValueError, "unsupported keys"):
            render_skill(self.root, source, "codex")
        (source / "skill.toml").write_text('[codex.openai.policy]\nallow_implicit_invocation = false\n')
        with self.assertRaisesRegex(ValueError, "invocation is configured separately"):
            render_skill(self.root, source, "codex")

    def test_python_script_requires_inline_dependencies(self):
        for text in ("print('missing metadata')\n", '# /// script\n# requires-python = ">=3.12"\n# ///\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_script(text, "helper.py")

    def test_shell_helper_cannot_be_bundled_as_runtime_code(self):
        source = self.create_skill(config='files = ["scripts/helper.sh"]\n')
        (source / "scripts").mkdir()
        (source / "scripts/helper.sh").write_text("echo hello\n")
        with self.assertRaisesRegex(ValueError, "Python uv"):
            render_skill(self.root, source, "codex")

    def test_build_is_idempotent_and_check_detects_stale_content_without_repair(self):
        source = self.create_skill()
        self.register_public_skills(["sample"])
        output = render_repository(self.root)
        write_outputs(self.root, output)
        before = {p: (self.root / p).read_bytes() for p in output}
        write_outputs(self.root, render_repository(self.root))
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in output})
        (source / "SKILL.md").write_text((source / "SKILL.md").read_text() + "A new instruction.\n")
        updated = render_repository(self.root)
        self.assertTrue(output_differences(self.root, updated))
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in output})

    def test_cleanup_only_removes_previously_generated_files(self):
        self.create_skill("old", internal=True)
        write_outputs(self.root, render_repository(self.root))
        unrelated = self.root / ".agents/skills/unrelated/SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("User-owned content")
        sibling = self.root / ".agents/skills/old/notes.md"
        sibling.write_text("User-owned sibling")
        shutil.rmtree(self.root / "src/internal/old")
        write_outputs(self.root, render_repository(self.root))
        self.assertFalse((self.root / ".agents/skills/old/SKILL.md").exists())
        self.assertEqual(unrelated.read_text(), "User-owned content")
        self.assertEqual(sibling.read_text(), "User-owned sibling")

    def test_refused_rebuild_preserves_all_existing_files(self):
        source = self.create_skill("existing", internal=True)
        write_outputs(self.root, render_repository(self.root))
        (source / "SKILL.md").write_text((source / "SKILL.md").read_text() + "Updated instruction.\n")
        self.create_skill("new", internal=True)
        foreign = self.root / ".agents/skills/new/SKILL.md"
        foreign.parent.mkdir(parents=True)
        foreign.write_text("User-owned file")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with self.assertRaisesRegex(ValueError, "unowned"):
            write_outputs(self.root, render_repository(self.root))
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_build_refuses_unowned_collision(self):
        self.create_skill("sample", internal=True)
        path = self.root / ".agents/skills/sample/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("User's existing skill")
        with self.assertRaisesRegex(ValueError, "unowned"):
            write_outputs(self.root, render_repository(self.root))
        self.assertEqual(path.read_text(), "User's existing skill")

    def test_unexpected_files_in_package_fail_check_and_build(self):
        output = render_repository(self.root)
        write_outputs(self.root, output)
        path = self.root / "plugins/codex/think-with/evals/results.json"
        path.parent.mkdir()
        path.write_text("{}")
        self.assertTrue(any("unowned:" in d for d in output_differences(self.root, output)))
        with self.assertRaisesRegex(ValueError, "unowned"):
            write_outputs(self.root, output)

    def test_forged_ownership_cannot_delete_source_files(self):
        (self.root / INDEX).write_text(json.dumps(["catalog.toml"]))
        with self.assertRaisesRegex(ValueError, "ownership"):
            write_outputs(self.root, render_repository(self.root))
        self.assertTrue((self.root / "catalog.toml").exists())

    def test_second_plugin_uses_catalog_without_generator_changes(self):
        self.create_skill()
        catalog = self.root / "catalog.toml"
        catalog.write_text(catalog.read_text() + '\n[plugins.research]\nversion = "1.2.3"\ndescription = "Research helpers"\nskills = ["sample"]\n')
        output = render_repository(self.root)
        for platform in ("claude", "codex"):
            manifest = json.loads(output[f"plugins/{platform}/research/.{platform}-plugin/plugin.json"])
            self.assertEqual(manifest["version"], "1.2.3")
            self.assertIn(f"plugins/{platform}/research/skills/sample/SKILL.md", output)

    def test_marketplaces_point_to_each_platform_package_without_repeating_versions(self):
        self.create_skill()
        self.register_public_skills(["sample"])
        output = render_repository(self.root)
        claude = json.loads(output[".claude-plugin/marketplace.json"])
        codex = json.loads(output[".agents/plugins/marketplace.json"])
        self.assertEqual(claude["plugins"], [{
            "name": "think-with", "source": "./plugins/claude/think-with",
        }])
        self.assertEqual(codex["plugins"], [{
            "name": "think-with",
            "source": {"source": "local", "path": "./plugins/codex/think-with"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }])
        for platform in ("claude", "codex"):
            manifest = json.loads(output[f"plugins/{platform}/think-with/.{platform}-plugin/plugin.json"])
            self.assertEqual(manifest["skills"], "./skills/")

    def test_skill_name_must_match_its_directory(self):
        source = self.create_skill()
        (source / "SKILL.md").write_text("---\nname: another\ndescription: Test\n---\n")
        with self.assertRaisesRegex(ValueError, "directory and frontmatter name must match"):
            render_skill(self.root, source, "codex")

    def test_codex_icons_must_be_bundled(self):
        source = self.create_skill(config='[codex.openai.interface]\nicon_small = "./assets/icon.svg"\n')
        with self.assertRaisesRegex(ValueError, "missing bundled UI asset"):
            render_skill(self.root, source, "codex")
        (source / "assets").mkdir()
        (source / "assets/icon.svg").write_text("<svg/>")
        config = source / "skill.toml"
        config.write_text('files = ["assets/icon.svg"]\n' + config.read_text())
        output = render_skill(self.root, source, "codex")
        self.assertEqual(output["assets/icon.svg"], b"<svg/>")

    def test_codex_dependencies_require_mcp_and_a_value(self):
        source = self.create_skill()
        for dependency, error in (("type = 'shell'\nvalue = 'example'", "type must be mcp"),
                                  ("type = 'mcp'", "tool dependency value")):
            with self.subTest(dependency=dependency):
                (source / "skill.toml").write_text("[[codex.openai.dependencies.tools]]\n" + dependency)
                with self.assertRaisesRegex(ValueError, error):
                    render_skill(self.root, source, "codex")
        (source / "skill.toml").write_text("[[codex.openai.dependencies.tools]]\ntype = 'mcp'\nvalue = 'example'\n")
        output = render_skill(self.root, source, "codex")
        self.assertEqual(yaml.safe_load(output["agents/openai.yaml"])["dependencies"]["tools"],
                         [{"type": "mcp", "value": "example"}])

    def test_inspector_never_executes_and_skips_development_directories(self):
        source = self.create_skill(body="AskUserQuestion\nRead [guide](references/guide.md).\n")
        sentinel = self.root / "MUST_NOT_EXIST"
        (source / "scripts").mkdir()
        (source / "scripts/danger.sh").write_text(f"touch {shlex.quote(str(sentinel))}\n")
        (source / "evals").mkdir()
        (source / "evals/result.md").write_text("evaluation")
        result = inspect(source)
        self.assertIn("scripts/danger.sh", [entry["path"] for entry in result["files"]])
        self.assertEqual(result["excluded_candidates"][0]["path"], "evals")
        self.assertTrue(result["review_signals"])
        self.assertFalse(sentinel.exists())

    def test_inspector_excludes_file_directory_and_dangling_symlinks(self):
        source = self.create_skill()
        external = self.root / "external"
        external.mkdir()
        (external / "secret.md").write_text("AskUserQuestion [secret](private.md)\n")
        (source / "linked.md").symlink_to(external / "secret.md")
        (source / "linked-dir").symlink_to(external, target_is_directory=True)
        (source / "dangling.md").symlink_to(external / "missing.md")
        result = inspect(source)
        self.assertEqual([entry["path"] for entry in result["files"]], ["SKILL.md"])
        self.assertEqual({entry["path"] for entry in result["excluded_candidates"]},
                         {"linked.md", "linked-dir", "dangling.md"})
        self.assertEqual(result["review_signals"], [])
        self.assertEqual(result["links"], [])

    def test_ported_helper_matches_shell_and_runs_after_relocation(self):
        # A safe example: preserve stdout and missing-input exit code while removing Bash.
        source = self.create_skill(config='files = ["scripts/label.py", "references/suffix.txt"]\n')
        (source / "scripts").mkdir()
        (source / "references").mkdir()
        (source / "references/suffix.txt").write_text("ready\n")
        original = self.root / "original.sh"
        original.write_text('if [ "$#" -ne 1 ]; then exit 2; fi\nprintf "%s:ready\\n" "$(printf "%s" "$1" | tr "[:lower:]" "[:upper:]")"\n')
        (source / "scripts/label.py").write_text('''# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
import sys
from pathlib import Path
if len(sys.argv) != 2:
    sys.exit(2)
suffix = (Path(__file__).resolve().parent.parent / "references/suffix.txt").read_text().strip()
print(f"{sys.argv[1].upper()}:{suffix}")
''')
        rendered = {platform: render_skill(self.root, source, platform) for platform in ("claude", "codex")}
        work = self.root / "unrelated working directory"
        work.mkdir()
        cases = (["hello world"], [])
        expected = [subprocess.run(["bash", str(original), *args], capture_output=True, cwd=work) for args in cases]
        original.unlink()
        shutil.rmtree(source)
        for platform, output in rendered.items():
            relocated = self.root / f"isolated {platform} skill"
            for path, content in output.items():
                destination = relocated / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            for args, old in zip(cases, expected):
                new = subprocess.run(["uv", "run", "--script", str(relocated / "scripts/label.py"), *args], capture_output=True, cwd=work)
                self.assertEqual((new.returncode, new.stdout), (old.returncode, old.stdout), new.stderr.decode())

    def create_skill(self, name="sample", *, internal=False, body="Inspect the user's input.\n", config=""):
        directory = self.root / "src" / ("internal" if internal else "skills") / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Inspect sample input and return findings.\n---\n\n{body}")
        if config:
            (directory / "skill.toml").write_text(config)
        return directory

    def register_public_skills(self, names):
        catalog = self.root / "catalog.toml"
        catalog.write_text(catalog.read_text().replace("skills = []", f"skills = {json.dumps(names)}"))


if __name__ == "__main__":
    unittest.main()
