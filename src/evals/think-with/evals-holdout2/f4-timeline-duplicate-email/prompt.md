---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out Customers sometimes get the monthly invoice email twice. Show me how that happens.

- On the 1st at 02:00 the billing job enqueues one SQS message per customer.
- Four worker instances long-poll the queue. The queue's visibility timeout is 30 seconds.
- For each message, a worker renders a PDF (usually 5–10 s, but 40–60 s for customers with many line items), sends the email through SES, then deletes the message.
- There is no dedup table, and the email send is not idempotent.
- Last month's logs for customer 8812:
  - 02:00:03 worker-2 received message m-77
  - 02:00:34 worker-4 received message m-77
  - 02:00:51 worker-2 sent invoice email
  - 02:00:51 worker-2 delete failed: receipt handle expired
  - 02:01:29 worker-4 sent invoice email
  - 02:01:29 worker-4 deleted message m-77
