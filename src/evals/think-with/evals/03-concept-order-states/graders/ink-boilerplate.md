---
type: regex
target: last_message
match: not_contains
flags: i
weight: 0.5
---
(파일 변경|file changes)[^\n]{0,20}(해당 없음|not applicable|none|없음)|edge 전체
