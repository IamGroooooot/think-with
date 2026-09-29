# 채점 교정 기록

사람이 블라인드로 매긴 채점 기록입니다. LLM judge(`sight-insight`, `ink-prose`)의 판정이 사람의 판단과 얼마나 일치하는지 확인할 때 기준으로 씁니다. `claude plugin eval`이 실행하는 케이스가 아니므로 플러그인 패키지에는 포함되지 않습니다.

## 폴더 구성

각 회차 폴더에는 다음 파일이 있습니다.

- `outputs-blind.md`: 채점한 답변 원문. 케이스마다 두 답변을 A와 B로 무작위로 배치했습니다. arm이 드러나는 첫 줄만 지우고 나머지 본문은 수정하지 않았습니다.
- `blind-key.json`: A와 B가 각각 어느 arm의 답변인지 기록한 키.
- `user-grades.txt`: 사람이 매긴 점수. 한 줄에 답변 하나씩 기록합니다.

## 채점 기준

- 관계: O는 핵심 관계가 정확히 보임, △는 내용은 있지만 애써야 보임, X는 틀렸거나 보이지 않음.
- 낭비: 0은 불필요한 내용 없음, 1은 약간 있음, 2는 뚜렷하게 있음.
- 형태(선택): O는 관계에 맞는 표현 형태, X는 맞지 않는 형태.
- 메모(선택): 한 줄 의견.
- 더나음(두 답변을 비교하는 회차만): A, B, 같음 중 하나.

빈칸은 채점하지 않았다는 뜻입니다.

## 회차

- `pilot3-dev`: 2026-09-29 실행 `evals/results/2026-09-29T09-48-18-520Z`. dev 케이스 01, 02, 04, 05, 06을 한 번씩 실행했습니다. arm은 `with`(think-with 0.1.4 설치)와 `without`(플러그인 없음)입니다. Claude Code 2.1.284.
- `holdout-new-vs-0.1.4`: 2026-09-29 실행. holdout 케이스 h1–h4는 `evals-holdout/results/2026-09-29T11-27-33-140Z`(후보)와 `evals-holdout/results/old-0.1.4`에서, dev 케이스 05는 `evals/results/2026-09-29T11-23-31-959Z`(후보)와 `evals/results/2026-09-29T10-59-42-291Z`(0.1.4)에서 같은 실행 번호의 답변을 한 쌍씩 골랐습니다. 두 arm 모두 플러그인을 설치했고, `blind-key.json`의 `new`는 커밋되지 않은 lay-out 수정 후보, `0.1.4`는 릴리스 0.1.4입니다. Claude Code 2.1.284.
- `holdout2-r2-vs-0.1.4`: 2026-09-29 실행. `evals-holdout2`의 새 케이스 f1–f4는 `evals-holdout2/results/r2`(수정안 2)와 `evals-holdout2/results/old-0.1.4`에서 실행 번호 1을, 개발 케이스로 바뀐 h1과 h3는 `evals-holdout/results/r2`와 `evals-holdout/results/old-0.1.4`에서 h1은 실행 번호 1, h3는 실행 번호 2를 골랐습니다. h3의 0.1.4 실행 번호 1은 이전 회차에서 이미 채점했기 때문입니다. 두 arm 모두 플러그인을 설치했습니다. `blind-key.json`의 `r2`는 커밋되지 않은 lay-out 수정안 2, `0.1.4`는 릴리스 0.1.4입니다. 판정 규칙은 `evals-holdout2/PREREG.md`에 있습니다.
