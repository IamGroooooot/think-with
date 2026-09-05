# Working on think-with

Use the project-local `manage-skills` skill for changes to skills or packaging, and `port-skill` to bring in a skill from elsewhere.

Edit `src/`, `adapters/`, and `catalog.toml`. Files listed in `.generated.json` are generated; update their sources instead. Internal skills belong only in `src/internal/`; distributable skills belong in `src/skills/`.

Run `mise install`, `mise run build`, then `mise run check`. The check command must also pass on a fresh checkout without running build first. Development scripts use Python with uv inline metadata. Do not add machine-local paths or dependencies on the author's other repositories to distributed skills.
