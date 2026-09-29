# Working on think-with

Use the project-local `manage-skills` skill for changes to skills or packaging, `port-skill` to bring in a skill from elsewhere, and `blind-grade` to decide through the user's blind grades whether a skill candidate ships.

Edit `src/`, `adapters/`, and `catalog.toml`. Files listed in `.generated.json` are generated; update their sources instead. Internal skills belong only in `src/internal/`; distributable skills belong in `src/skills/`.

Run `mise install` when the pinned tools need installation. Run `mise run build` after changing generation inputs, and `mise run check` to validate packaging changes. The check command must also pass on a fresh checkout without running build first. Development scripts use Python with uv inline metadata. Do not add machine-local paths or dependencies on the author's other repositories to distributed skills.
