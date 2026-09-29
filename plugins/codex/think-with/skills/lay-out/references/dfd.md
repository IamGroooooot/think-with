# Horizontal data flow

Name each box plainly, adding its kind only when the name alone is unclear, as in `Orders DB`. Label each edge with what moves and, when it matters, when it moves. Show the smallest connected path from left to right. Split long flows into focused connected paths; keep each path horizontal. Add another path only when it changes the answer.

```text
Buyer --order--> Checkout --on submit: order row--> Orders DB
```
