---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out 우리 서비스 전체 아키텍처, 데이터 흐름, 배포 구조, 에러 처리 방식, 그리고 이번 PR 변경까지 전부 한 번에 보여줘.

서비스 정보:
- FastAPI API 서버 3 replica. k8s에서 nginx ingress 뒤에 있어.
- 데이터는 Postgres(RDS)에 저장하고, 세션과 캐시는 Redis를 써.
- 무거운 작업(리포트 생성, 메일)은 Celery worker 2 replica가 Redis broker로 받아서 처리해.
- 배포는 GitHub Actions에서 이미지 빌드 → ECR push → Argo CD sync 순서야.
- 에러는 FastAPI exception handler가 JSON 에러로 바꾸고 Sentry로 보내. Celery 작업은 3번 재시도한 뒤 Sentry로 보내.

이번 PR:
- `app/middleware/ratelimit.py` 추가. Redis token bucket으로 API 키마다 초당 20 요청으로 제한하고, 넘으면 429를 반환해.
- `app/main.py`에서 이 middleware를 인증 middleware 바로 뒤, 라우터 앞에 등록해.
- `RATE_LIMIT_PER_SEC` 설정 추가.
