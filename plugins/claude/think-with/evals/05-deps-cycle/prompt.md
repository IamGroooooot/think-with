---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out 우리 백엔드 모듈 의존성을 보여줘. 아래는 모듈 25개의 import 목록이야 (`A -> B, C`는 A가 B와 C를 import한다는 뜻).

```
api/routes/users.py          -> services/users/profile.py, services/users/auth.py, api/deps.py
api/routes/billing.py        -> services/billing/invoice.py, services/billing/payment.py, api/deps.py
api/routes/admin.py          -> services/users/profile.py, services/billing/invoice.py, api/deps.py
api/deps.py                  -> infra/db.py, services/users/auth.py
services/users/profile.py    -> domain/user.py, services/users/plan.py, infra/db.py, common/errors.py
services/users/plan.py       -> domain/plan.py, services/billing/pricing.py, infra/db.py
services/users/auth.py       -> domain/user.py, infra/redis.py, infra/settings.py
services/billing/invoice.py  -> domain/invoice.py, services/billing/pricing.py, services/users/profile.py, infra/db.py, services/notify/email.py
services/billing/pricing.py  -> domain/plan.py, domain/money.py
services/billing/payment.py  -> domain/invoice.py, infra/stripe_client.py, common/errors.py
services/notify/email.py     -> services/notify/templates.py, infra/smtp.py
services/notify/templates.py -> infra/settings.py
domain/user.py               -> common/errors.py
domain/invoice.py            -> domain/money.py
domain/plan.py               -> domain/money.py
domain/money.py              -> (none)
infra/db.py                  -> infra/settings.py, common/logging.py
infra/redis.py               -> infra/settings.py
infra/stripe_client.py       -> infra/settings.py, common/logging.py
infra/smtp.py                -> infra/settings.py
infra/settings.py            -> (none)
jobs/nightly_invoices.py     -> services/billing/invoice.py, infra/db.py
jobs/cleanup.py              -> infra/db.py, common/logging.py
common/logging.py            -> (none)
common/errors.py             -> (none)
```
