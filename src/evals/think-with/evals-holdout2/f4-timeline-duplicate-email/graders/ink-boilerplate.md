---
type: regex
target: last_message
match: not_contains
flags: i
weight: 0.5
---
(파일 변경|file changes?|file edits?)[^\n]{0,20}(해당 없|not applicable|none|없음|없습니다|n/a)|nothing in the repo changed|no files? (were |was )?(changed|edited|modified)|no file (edits|changes)|edge 전체
