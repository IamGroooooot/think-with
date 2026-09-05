# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Inventory a source skill. Never copy it or execute its scripts."""

import argparse
import json
import os
import re
from pathlib import Path

EXCLUDED = {".git", ".github", ".venv", "__pycache__", "node_modules", "evals", "evaluations", "tests", ".pytest_cache"}
SIGNALS = re.compile(r"AskUserQuestion|request_user_input|disable-model-invocation|allow_implicit_invocation|\$\{CLAUDE_[A-Z_]+\}|context:\s*fork|allowed-tools:|(?:/Users/|/home/|~/|\.\./)\S+|(?:uv run|python3?|node|bash|gh|git)\s+[^\n]+")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.source)
    except (OSError, ValueError) as error:
        parser.exit(1, f"inspect: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def inspect(source):
    source = source.resolve()
    if not (source / "SKILL.md").is_file():
        raise ValueError("source must be a skill directory containing SKILL.md")
    files, excluded, signals, links = [], [], [], []
    for directory, dirs, names in os.walk(source, followlinks=False):
        for name in sorted(dirs.copy()):
            path = Path(directory) / name
            if name in EXCLUDED or path.is_symlink():
                reason = "symlink: inspect and materialize if needed" if path.is_symlink() else "development-only candidate; verify callers"
                excluded.append({"path": path.relative_to(source).as_posix(), "reason": reason})
                dirs.remove(name)
        dirs.sort()
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(source).as_posix()
            if path.is_symlink():
                excluded.append({"path": relative, "reason": "symlink: inspect and materialize if needed"})
                continue
            files.append({"path": relative, "bytes": path.stat().st_size})
            file_signals, file_links = inspect_text_file(path, relative)
            signals.extend(file_signals)
            links.extend(file_links)
    return {"files": files, "excluded_candidates": excluded, "review_signals": signals, "links": links,
            "note": "Candidates only. Trace transitive resources and imports before choosing the bundle. No files were executed."}


def inspect_text_file(path, relative):
    signals, links = [], []
    if path.suffix.lower() not in {".md", ".py", ".sh", ".js", ".ts", ".yaml", ".yml", ".toml"}:
        return signals, links
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if SIGNALS.search(line):
            signals.append({"path": relative, "line": number, "text": line[:300]})
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", line):
            links.append({"path": relative, "line": number, "target": link})
    return signals, links


if __name__ == "__main__":
    main()
