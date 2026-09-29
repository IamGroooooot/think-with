---
type: llm
focus: last_message
weight: 1
---
The user asked for the difference between a Python list and a tuple "in one line". Check each claim, citing the answer:

1. The core answer is at most two sentences (a short optional code example does not count against this).
2. It contains no diagram, table, or multi-section layout.
3. It states the mutability difference correctly (list mutable, tuple immutable).

PASS if all three hold. A second sentence that adds a related fact (for example, hashability) is fine. Otherwise FAIL.
