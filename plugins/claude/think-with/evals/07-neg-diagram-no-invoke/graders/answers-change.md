---
type: llm
focus: last_message
weight: 1
---
The user asked, without invoking any skill, for a diagram of what a PR changes. The PR adds a Redis cache in front of user reads and invalidates it on update and delete. Grade the answer on these claims (yes or no each, citing the passage):

1. It states that user reads now check the cache first and fall back to the DB on a miss, filling the cache.
2. It states that update and delete now invalidate the cached entry.
3. It gives a diagram or structured view (not only prose) of the change.

PASS if all three are yes. Otherwise FAIL.
