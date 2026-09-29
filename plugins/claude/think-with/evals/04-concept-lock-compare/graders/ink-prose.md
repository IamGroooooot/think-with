---
type: llm
focus: last_message
weight: 1
---
Judge whether the answer is carried by its diagrams rather than by text.

Count "diagram lines": lines inside fenced code blocks, plus rows of tables whose cells are short labels or values.
Count "prose lines": sentences and bullet points outside fences, plus rows of tables whose cells are full sentences.

PASS if both hold:
1. Diagram lines outnumber prose lines.
2. A reader who skips all prose still gets the key relationship; the prose adds caveats or a one-line takeaway, not the explanation itself.

FAIL if the answer reads as a text document with diagrams attached. Report the two counts.
