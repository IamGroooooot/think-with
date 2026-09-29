---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out Show me how the packages in our TypeScript monorepo depend on each other. Each line lists a workspace package and the workspace packages it imports.

```
apps/web                -> features/cart, features/auth, ui, api-client, config
apps/admin              -> features/auth, ui, api-client, config
apps/api                -> domain, db, logger, config
features/cart           -> ui, api-client, domain, utils
features/auth           -> ui, api-client, utils
ui                      -> utils, features/cart
api-client              -> domain, utils, config
domain                  -> utils
db                      -> domain, logger, config
logger                  -> config
utils                   -> (none)
config                  -> (none)
```

Notes: `db` wraps Prisma and must only run on the server. `ui` is meant to be the shared design-system package.
