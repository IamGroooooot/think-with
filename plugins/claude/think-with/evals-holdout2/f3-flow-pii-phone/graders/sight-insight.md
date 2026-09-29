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

Expected insight: The phone number is protected only inside Postgres (encrypted) and in its readers (masked in the CS tool, last 4 digits in SMS logs), but it travels in plaintext in the user.created Kafka event and from there is copied unmasked into BigQuery (only email is hashed) and into the S3 archive with no retention limit; it is also sent to the external SMS vendor. The plaintext copies at rest are Kafka (7 days), BigQuery and S3 (indefinitely).
