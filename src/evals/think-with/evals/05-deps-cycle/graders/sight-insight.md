---
type: llm
focus: last_message
weight: 1
---
Judge whether the DIAGRAMS alone make the key relationship visible. Do the steps in order.

Step 1. Copy out only the contents of the fenced code blocks (and any table that serves as a main view). Ignore every other sentence from here on.
Step 2. From that content alone, write in 1–2 sentences the core relationship a reader would take away. Write it BEFORE reading the Expected insight below.
Step 3. Compare your sentence with the Expected insight and code it:
- correct: states the same relationship.
- partial: states only part of it, or the reader must piece it together from scattered details.
- wrong emphasis: a detail (a code line, a function, a file, a config key, logging, a test) is the headline instead of the relationship.
- not derivable: the diagrams alone do not show it; it appears only in prose or nowhere.

PASS only if the code is "correct". Otherwise FAIL.

Expected insight: Dependencies mostly flow downward in layers (api/jobs → services → domain/infra → common), with one exception: services/users and services/billing depend on each other (users/plan → billing/pricing, and billing/invoice → users/profile). This package-level cycle is invisible at the file level, where there is no file cycle.
