# Get Advice

사용자의 고민에 도움이 되는 연구를 찾고, 전문가 관점의 자문과 독립적인 사실 검증을 거쳐 조언하는 스킬입니다.
연구에서 확인된 사실과 상황에 적용한 추론을 구분해, 사용자가 판단의 근거를 이해하고 더 배울 방향을 찾도록 돕고자 합니다.

## 출처와 영감

1. **김창준님의 네이버 프리미엄 콘텐츠 [Evidence Based Practice](https://naver.me/5t7zElDg)**를 통해 EBP라는 개념을 알게 되었습니다.
2. **itsbluetic의 [expert-panel-by-ebp](https://github.com/itsbluetic/expert-panel-by-ebp)**에서 영감을 받아 이 스킬을 만들었습니다.

## 사용

현재는 **Codex 사용을 권장합니다.** Claude Code는 간단한 동작 확인만 거쳤으며, 다양한 상황에서 충분히 테스트하지는 못했습니다.

Codex에서는 `$get-advice`, Claude Code 플러그인에서는 `/think-with:get-advice`로 호출합니다.

Codex 기준으로 전문가 자문에는 GPT-6 Astra(low), 사실 검증에는 GPT-5.6 Luna(xhigh)를 별도로 호출합니다. 여러 에이전트가 조사와 검증을 수행하므로 **토큰 소모가 클 수 있습니다.**
