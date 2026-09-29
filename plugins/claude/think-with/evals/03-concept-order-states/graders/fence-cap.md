---
type: regex
target: last_message
match: not_contains
weight: 0.5
---
(```[^\n]*\n[\s\S]*?\n```[\s\S]*?){4}
