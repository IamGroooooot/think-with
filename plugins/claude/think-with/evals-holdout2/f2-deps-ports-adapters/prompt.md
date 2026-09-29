---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out Show me how the packages in our Python service depend on each other. Each line lists a package and the packages it imports.

```
app/api           -> app/services, app/schemas
app/cli           -> app/services
app/services      -> app/domain, app/ports
app/schemas       -> app/domain
app/ports         -> app/domain
app/domain        -> app/infra/sql, app/common
app/infra/sql     -> app/ports, app/domain, app/common
app/infra/stripe  -> app/ports, app/common
app/infra/mail    -> app/ports, app/common
app/bootstrap     -> app/api, app/cli, app/infra/sql, app/infra/stripe, app/infra/mail
app/common        -> (none)
```

We follow ports and adapters: the domain and services must not know about infrastructure, adapters in `app/infra` implement the interfaces in `app/ports`, and only `app/bootstrap` wires adapters in.
