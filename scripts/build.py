# /// script
# requires-python = ">=3.12"
# dependencies = ["PyYAML==6.0.3"]
# ///
"""Generate a pair of self-contained packages from explicitly selected files."""

import argparse
import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
INDEX = ".generated.json"
PLATFORMS = ("claude", "codex")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
BLOCK = re.compile(r"^\{\{tw:([a-z][a-z0-9-]*)\}\}$", re.MULTILINE)
COMMON_FIELDS = {"name", "description", "license", "compatibility", "metadata"}
CLAUDE_FIELDS = {
    "argument-hint", "arguments", "allowed-tools", "model", "context", "agent",
    "user-invocable", "hooks", "shell", "when_to_use",
}
EXCLUDED = {".git", ".github", ".venv", "__pycache__", "node_modules", "evals", "evaluations"}
LEGAL = re.compile(r"(?:LICENSE|LICENCE|NOTICE|COPYING|AUTHORS|COPYRIGHT)(?:\.[^/]+)?$")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        outputs = render_repository(args.root.resolve())
        write_outputs(args.root.resolve(), outputs)
    except (ValueError, OSError, SyntaxError, yaml.YAMLError) as error:
        parser.exit(1, f"build: {error}\n")
    print(f"Generated {len(outputs)} files.")


def render_repository(root):
    catalog = read_catalog(root)
    marketplace = catalog["marketplace"]
    outputs = {}
    entries = {platform: [] for platform in PLATFORMS}
    for name, plugin in catalog["plugins"].items():
        for platform in PLATFORMS:
            package_path = f"plugins/{platform}/{name}"
            outputs.update(render_plugin(root, package_path, name, plugin, marketplace, platform))
            entry = {"name": name, "source": f"./{package_path}"}
            if platform == "codex":
                entry.update(source={"source": "local", "path": f"./{package_path}"},
                             policy={"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                             category="Productivity")
            entries[platform].append(entry)
    for platform in PLATFORMS:
        outputs.update(render_internal_skills(root, platform))
        destination, manifest = render_marketplace(marketplace, entries[platform], platform)
        outputs[destination] = json_bytes(manifest)
    outputs[INDEX] = json_bytes(sorted(outputs))
    return outputs


def write_outputs(root, outputs):
    previous = read_owned_paths(root)
    for relative in previous | outputs.keys():
        path = safe_path(root, relative)
        if relative in outputs and path.exists() and relative not in previous and relative != INDEX:
            raise ValueError(f"refusing to overwrite unowned file: {relative}")
    unexpected = unexpected_plugin_files(root, outputs, previous)
    if unexpected:
        raise ValueError("unowned files inside generated plugins: " + ", ".join(unexpected))
    for relative, content in sorted(outputs.items()):
        if relative == INDEX:
            continue
        path = safe_path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != content:
            path.write_bytes(content)
    for relative in sorted(previous - outputs.keys()):
        path = safe_path(root, relative)
        if path.is_file():
            path.unlink()
            parent = path.parent
            while parent != root and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    safe_path(root, INDEX).write_bytes(outputs[INDEX])


def output_differences(root, outputs):
    previous = read_owned_paths(root)
    differences = []
    for relative in sorted(previous | outputs.keys()):
        path = safe_path(root, relative)
        if relative not in outputs:
            differences.append(f"stale: {relative}")
        elif not path.is_file():
            differences.append(f"missing: {relative}")
        elif path.read_bytes() != outputs[relative]:
            differences.append(f"changed: {relative}")
    differences.extend(f"unowned: {p}" for p in unexpected_plugin_files(root, outputs, previous))
    return differences


def read_catalog(root):
    catalog = tomllib.loads(safe_path(root, "catalog.toml", exists=True).read_text())
    validate_allowed_keys(catalog, {"marketplace", "plugins"}, "catalog")
    if not {"marketplace", "plugins"} <= catalog.keys():
        raise ValueError("catalog requires marketplace and plugins tables")
    market = catalog["marketplace"]
    validate_allowed_keys(market, {"name", "display_name", "description", "owner", "repository"}, "marketplace")
    if set(market) != {"name", "display_name", "description", "owner", "repository"}:
        raise ValueError("marketplace requires name, display_name, description, owner, and repository")
    validate_name(market["name"])
    for key in ("display_name", "description", "owner", "repository"):
        validate_nonempty_string(market[key], key)
    if not market["repository"].startswith("https://github.com/"):
        raise ValueError("marketplace.repository must be an HTTPS GitHub repository URL")
    if not isinstance(catalog["plugins"], dict):
        raise ValueError("plugins must be a table")
    for name, plugin in catalog["plugins"].items():
        validate_name(name)
        validate_allowed_keys(plugin, {"version", "description", "skills"}, name)
        if set(plugin) != {"version", "description", "skills"}:
            raise ValueError(f"{name}: version, description, and skills are required")
        if not isinstance(plugin["version"], str) or not VERSION.fullmatch(plugin["version"]):
            raise ValueError(f"{name}: use a release version MAJOR.MINOR.PATCH")
        validate_nonempty_string(plugin["description"], f"{name}.description")
        for skill in require_unique_strings(plugin["skills"], f"{name}.skills"):
            validate_name(skill)
    return catalog


def render_plugin(root, base, name, plugin, market, platform):
    manifest = {
        "name": name, "version": plugin["version"],
        "description": plugin["description"],
        "author": {"name": market["owner"]}, "repository": market["repository"],
    }
    if plugin["skills"]:
        manifest["skills"] = "./skills/"
    if platform == "codex":
        manifest["interface"] = {
            "displayName": name, "shortDescription": plugin["description"],
            "longDescription": plugin["description"], "developerName": market["owner"],
            "category": "Productivity", "capabilities": [], "defaultPrompt": [],
            "websiteURL": market["repository"],
        }
    outputs = {f"{base}/.{platform}-plugin/plugin.json": json_bytes(manifest)}
    for skill in plugin["skills"]:
        bundled = render_skill(root, root / "src/skills" / skill, platform)
        outputs.update({f"{base}/skills/{skill}/{path}": content for path, content in bundled.items()})
    return outputs


def render_internal_skills(root, platform):
    local = ".claude" if platform == "claude" else ".agents"
    internal = root / "src/internal"
    outputs = {}
    for source in sorted(internal.iterdir()) if internal.exists() else []:
        if source.name == "README.md" and source.is_file() and not source.is_symlink():
            continue
        if not source.is_dir():
            raise ValueError(f"unexpected internal source: {source}")
        for path, content in render_skill(root, source, platform).items():
            outputs[f"{local}/skills/{source.name}/{path}"] = content
    return outputs


def render_marketplace(market, entries, platform):
    manifest = {"name": market["name"], "plugins": entries}
    if platform == "claude":
        manifest["owner"] = {"name": market["owner"]}
        manifest["description"] = market["description"]
        return ".claude-plugin/marketplace.json", manifest
    manifest["interface"] = {"displayName": market["display_name"]}
    return ".agents/plugins/marketplace.json", manifest


def render_skill(root, source, platform):
    metadata, body, config = read_skill(root, source)
    platform_config = config.get(platform, {})
    blocks = read_blocks(root, platform_config, platform)
    explicit_only = config.get("invocation", "auto") == "explicit"
    if platform == "claude":
        claude_frontmatter = platform_config.get("frontmatter", {})
        validate_allowed_keys(claude_frontmatter, CLAUDE_FIELDS, "claude.frontmatter")
        metadata.update(claude_frontmatter)
        if explicit_only:
            metadata["disable-model-invocation"] = True
    bundled_files = {"SKILL.md": ("---\n" + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
                            + "---\n\n" + render_blocks(body, blocks)).encode()}
    bundled_files.update(render_runtime_files(source, config, blocks))
    if platform == "codex":
        openai = require_table(platform_config.get("openai", {}), "codex.openai").copy()
        validate_allowed_keys(openai, {"interface", "dependencies"}, "codex.openai (invocation is configured separately)")
        if explicit_only:
            openai["policy"] = {"allow_implicit_invocation": False}
        if openai:
            validate_openai(openai, bundled_files)
            bundled_files["agents/openai.yaml"] = yaml.safe_dump(openai, sort_keys=False, allow_unicode=True).encode()
    validate_links(bundled_files)
    return bundled_files


def read_skill(root, source):
    validate_name(source.name)
    safe_path(root, source.relative_to(root).as_posix(), exists=True)
    metadata, body = parse_frontmatter(safe_path(source, "SKILL.md", exists=True).read_text())
    validate_allowed_keys(metadata, COMMON_FIELDS, f"{source.name} common frontmatter")
    if metadata.get("name") != source.name:
        raise ValueError(f"{source.name}: directory and frontmatter name must match")
    validate_nonempty_string(metadata.get("description"), f"{source.name}.description")
    config_path = safe_path(source, "skill.toml")
    config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
    validate_allowed_keys(config, {"invocation", "files", "origin", "claude", "codex"}, f"{source.name} config")
    invocation = config.get("invocation", "auto")
    if invocation not in ("auto", "explicit"):
        raise ValueError(f"{source.name}: invocation must be auto or explicit")
    for target in PLATFORMS:
        validate_allowed_keys(config.get(target, {}), {"blocks", "frontmatter"} if target == "claude" else {"blocks", "openai"}, target)
    return metadata, body, config


def read_blocks(root, selected, platform):
    blocks = {}
    adapter = root / "adapters" / platform
    for path in sorted(adapter.glob("*.md")):
        safe_path(root, path.relative_to(root).as_posix(), exists=True)
        blocks[path.stem] = path.read_text().strip()
    blocks.update(require_table(selected.get("blocks", {}), f"{platform}.blocks"))
    for key, value in blocks.items():
        validate_nonempty_string(value, f"block {key}")
    return blocks


def render_runtime_files(source, config, blocks):
    bundled_files = {}
    selected_files = require_unique_strings(config.get("files", []), f"{source.name}.files")
    # Legal notices remain part of the package even when omitted from the file list.
    legal_notices = {p.name for p in source.iterdir() if LEGAL.fullmatch(p.name)}
    for relative in sorted(set(selected_files) | legal_notices):
        path = safe_path(source, relative, exists=True)
        parts = PurePosixPath(relative).parts
        if set(parts) & EXCLUDED:
            raise ValueError(f"{source.name}: development-only file cannot be bundled: {relative}")
        if parts[0] not in {"scripts", "references", "assets"} and not LEGAL.fullmatch(relative):
            raise ValueError(f"{source.name}: unsupported bundled path: {relative}")
        if not path.is_file():
            raise ValueError(f"{source.name}: files must name individual files: {relative}")
        if parts[0] == "scripts":
            if path.suffix != ".py":
                raise ValueError(f"{relative}: executable helpers must be Python uv scripts")
            validate_script(path.read_text(), relative)
        content = path.read_bytes()
        if parts[0] == "references" and path.suffix == ".md":
            content = render_blocks(content.decode(), blocks).encode()
        bundled_files[relative] = content
    return bundled_files


def render_blocks(body, blocks):
    def replace(match):
        key = match[1]
        if key not in blocks:
            raise ValueError(f"missing platform block: {key}")
        return blocks[key]
    rendered = BLOCK.sub(replace, body)
    if "{{tw:" in rendered:
        raise ValueError("unresolved block; put each {{tw:name}} on a separate line (blocks cannot nest)")
    return rendered.rstrip() + "\n"


def validate_script(text, label):
    match = re.search(r"(?m)^# /// script\n((?:#.*\n)*)# ///\s*$", text)
    if not match:
        raise ValueError(f"{label}: missing PEP 723 script metadata")
    raw = "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in match[1].splitlines())
    config = tomllib.loads(raw)
    validate_nonempty_string(config.get("requires-python"), f"{label} requires-python")
    require_unique_strings(config.get("dependencies"), f"{label} dependencies")
    compile(text, label, "exec")


def validate_openai(config, bundled):
    interface = config.get("interface", {})
    validate_allowed_keys(interface, {"display_name", "short_description", "default_prompt", "icon_small", "icon_large", "brand_color"}, "codex.openai.interface")
    for key, value in interface.items():
        validate_nonempty_string(value, key)
        if key in {"icon_small", "icon_large"} and value.removeprefix("./") not in bundled:
            raise ValueError(f"missing bundled UI asset: {value}")
    dependencies = config.get("dependencies", {})
    validate_allowed_keys(dependencies, {"tools"}, "codex.openai.dependencies")
    if not isinstance(dependencies.get("tools", []), list):
        raise ValueError("codex.openai.dependencies.tools must be an array")
    for tool in dependencies.get("tools", []):
        validate_allowed_keys(tool, {"type", "value", "description", "transport", "url"}, "tool dependency")
        if tool.get("type") != "mcp":
            raise ValueError("Codex tool dependency type must be mcp")
        validate_nonempty_string(tool.get("value"), "tool dependency value")


def validate_links(bundled):
    # Check literal Markdown resource links; code examples and URLs are not dependencies.
    for relative, content in bundled.items():
        if relative != "SKILL.md" and not (relative.startswith("references/") and relative.endswith(".md")):
            continue
        text = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", content.decode())
        targets = re.findall(r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", text)
        targets += re.findall(r"(?m)^\[[^\]]+\]:\s*(<[^>]+>|\S+)", text)
        for target in targets:
            normalized = resolve_resource_link(relative, target)
            if normalized is not None and normalized not in bundled and not any(p.startswith(normalized + "/") for p in bundled):
                raise ValueError(f"{relative}: missing bundled link: {target}")


def resolve_resource_link(relative, target):
    parsed = urlsplit(target.strip("<>"))
    if parsed.scheme in {"file", "skill"}:
        raise ValueError(f"{relative}: resource depends on an external local location: {target}")
    if parsed.scheme or not parsed.path:
        return None
    path = PurePosixPath(unquote(parsed.path))
    if path.is_absolute():
        raise ValueError(f"{relative}: absolute resource link: {target}")
    components = list(PurePosixPath(relative).parent.parts)
    for part in path.parts:
        if part == "..":
            if not components:
                raise ValueError(f"{relative}: resource link escapes skill: {target}")
            components.pop()
        elif part != ".":
            components.append(part)
    return "/".join(components)


def unexpected_plugin_files(root, outputs, previous):
    owned = set(outputs) | previous
    bases = {"/".join(p.split("/")[:3]) for p in owned if p.startswith("plugins/")}
    found = []
    for base in sorted(bases):
        directory = safe_path(root, base)
        for path in directory.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or (path.is_file() and relative not in owned):
                found.append(relative)
    return found


def read_owned_paths(root):
    path = safe_path(root, INDEX)
    if not path.exists():
        return set()
    paths = require_unique_strings(json.loads(path.read_text()), INDEX)
    for relative in paths:
        safe_path(root, relative)
        is_marketplace = relative in {".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"}
        is_generated_content = relative.startswith((".claude/skills/", ".agents/skills/", "plugins/claude/", "plugins/codex/"))
        if not (is_marketplace or is_generated_content):
            raise ValueError(f"invalid generated ownership path: {relative}")
    return set(paths)


def safe_path(root, relative, exists=False):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError(f"invalid relative path: {relative!r}")
    parts = PurePosixPath(relative).parts
    if PurePosixPath(relative).is_absolute() or ".." in parts or relative != PurePosixPath(relative).as_posix():
        raise ValueError(f"path must be normalized and inside its root: {relative}")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"symlink must be materialized first: {path}")
    if exists and not path.exists():
        raise ValueError(f"missing source: {path}")
    return path


def parse_frontmatter(text):
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)(.*)", text, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md must begin with YAML frontmatter")
    metadata = yaml.safe_load(match[1])
    if not isinstance(metadata, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    return metadata, match[2].lstrip("\n")


def validate_allowed_keys(value, allowed, label):
    require_table(value, label)
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{label}: unsupported keys: {', '.join(sorted(unknown))}")


def require_table(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a table")
    return value


def validate_nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def validate_name(value):
    if not isinstance(value, str) or len(value) > 64 or not NAME.fullmatch(value):
        raise ValueError(f"invalid kebab-case name: {value!r}")


def require_unique_strings(value, label):
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value) or len(set(value)) != len(value):
        raise ValueError(f"{label} must be an array of unique non-empty strings")
    return value


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


if __name__ == "__main__":
    main()
