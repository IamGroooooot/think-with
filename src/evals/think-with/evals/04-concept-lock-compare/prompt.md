---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out We run a cron-style scheduler on 3 app instances and need exactly one of them to fire each job (leader election). We already operate Postgres and Redis; we do not run etcd yet. The candidates are:

1. Redis `SET key value NX PX 30000` with periodic renewal
2. Postgres session-level advisory lock (`pg_try_advisory_lock`) held on a dedicated connection
3. etcd lease + election API (`concurrency.Election`)

Jobs are not idempotent: a double fire sends duplicate invoices. Lay out how these options compare for us.
