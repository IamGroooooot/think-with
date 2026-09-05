# 내부용 스킬

이 폴더는 think-with 프로젝트를 관리할 때만 쓰는 내부용 스킬의 공통 원본입니다.
배포용 스킬은 `src/skills/`에 둡니다. 내부용 스킬은 `catalog.toml`의 플러그인 목록에 등록하지 않습니다.

`mise run build`는 각 스킬을 플랫폼별로 변환하여 Claude용 `.claude/skills/`와 Codex용 `.agents/skills/`에 생성합니다.
수정은 이 폴더의 원본에서 하고, 생성된 파일은 직접 수정하지 않습니다.
