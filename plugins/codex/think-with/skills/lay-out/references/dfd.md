# Horizontal DFD

Use `[entity]`, `(process)`, and `|| store ||`. Show the smallest connected path from left to right. Split long flows into focused connected paths; keep each path horizontal. Add another path only when it changes the answer.

```text
[Buyer] --order--> (Create) --order record--> || Orders ||
```
