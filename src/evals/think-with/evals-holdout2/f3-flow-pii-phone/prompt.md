---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out 개인정보 점검 때문에 그래. 사용자 전화번호가 어디로 흘러가서 어디에 저장되는지 보여줘.

- 모바일 앱이 회원가입할 때 전화번호를 `POST /signup`으로 보낸다.
- API 서버는 전화번호를 Postgres `users` 테이블에 AES로 암호화해 저장하고, Kafka에 `user.created` 이벤트를 발행한다. 이벤트 본문에는 전화번호가 평문으로 들어 있다.
- `notify` 서비스가 `user.created`를 구독해서 외부 SMS 업체 API로 인증번호 문자를 보낸다. 발송 로그에는 전화번호 뒤 4자리만 남긴다.
- `analytics` 커넥터가 모든 Kafka 토픽을 BigQuery로 복제한다. 복제하기 전에 `email` 필드만 해시한다.
- Kafka 토픽 보존 기간은 7일이다. 매일 밤 토픽 원본이 그대로 S3에 아카이브되고, S3 보존 기한은 없다.
- CS 도구는 Postgres에서 읽어 전화번호를 010-****-1234처럼 가려서 보여준다.
