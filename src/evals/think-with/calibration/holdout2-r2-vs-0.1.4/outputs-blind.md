# 3차 블라인드 출력: 수정안 2 vs 0.1.4

케이스마다 두 답변을 A와 B로 무작위로 배치했습니다. 두 답변 모두 플러그인을 설치한 상태의 답변이고, 하나는 lay-out 수정안 2, 다른 하나는 0.1.4입니다. 답변 본문은 수정하지 않았습니다.

---

# 01 · f1-diff-retry-policy
질문: 머지 전 PR: 외부 API 호출을 공통 재시도 정책으로 모음 (Python)

┏━━━━━━━━━━━━━━━━ 01A ━━━━━━━━━━━━━━━━┓

**아직 머지 전인 PR입니다.** 이 PR로 POST 요청인 결제·메일도 타임아웃이나 5xx가 나면 자동으로 다시 보내게 됩니다. 결제는 한 번 요청했는데 두 번 청구될 수 있습니다.

```
app/
├── http/policy.py      + 새 파일: PolicyClient (5s, 3회 재시도)
└── clients/
    ├── payments.py     ~ PolicyClient로 교체
    ├── email.py        ~ PolicyClient로 교체 (timeout=10)
    ├── geo.py          ~ PolicyClient로 교체
    └── search.py       ~ PolicyClient로 교체
```

**클라이언트별 동작 변화** (위험도 순)

```
client    method  timeout    retry          최악 대기*
────────  ──────  ─────────  ─────────────  ─────────────
payments  POST    20s → 5s   없음 → 3회  !  20s → ~16.5s
email     POST    30s → 10s  없음 → 3회  !  30s → ~31.5s
search    GET      2s → 5s   없음 → 3회     2s → ~16.5s
geo       GET     10s → 5s   없음 → 3회     10s → ~16.5s
────────────────────────────────────────────────────────
retry 조건: TimeoutException 또는 5xx / 4xx·연결 오류는 재시도 안 함
backoff: 0.5s → 1s   /   reraise=True → 호출부가 받는 예외 타입은 그대로
```
\* 3 × timeout + 1.5s로 계산한 근사치입니다. httpx timeout은 connect/read 같은 단계마다 따로 걸리므로 실제 상한은 이보다 길 수 있습니다.

**결제 중복 청구가 생기는 경로**

```
charge() ─POST /charges─▶ PAY    결제 처리 중 (>5s)
         ◀── ReadTimeout (5s)    서버에서는 결제 완료됨
  retry  ─POST /charges─▶ PAY    두 번째 결제 생성
         ◀── 200 {id}            호출부는 id 하나만 받음
```

- 원래 20s였던 결제 timeout이 5s로 줄어서 이 경로에 들어갈 확률이 높아집니다.
- 서버가 처리를 끝낸 뒤 5xx를 돌려주는 경우도 같은 결과가 됩니다.
- email도 같은 구조라서 메일이 중복으로 발송될 수 있습니다.
- 결제 API가 idempotency key를 지원하는지는 diff만 봐서는 알 수 없습니다. 지원한다면 키를 넘기는 것만으로 이 문제가 해결됩니다.

**머지 전에 볼 것**
- POST는 재시도하지 않게 하거나, 재시도 대상을 `ConnectTimeout`으로만 좁히거나, idempotency key를 붙여야 합니다.
- search는 2s였던 최악 대기가 약 16s로 늘어납니다. 상위 요청의 timeout이나 SLA를 넘지 않는지 확인이 필요합니다.
- 결제 timeout을 5s로 줄인 게 의도한 건지 확인해야 합니다. 이 부분은 PolicyClient 기본값을 그대로 따라간 결과로 보입니다.

┗━━━━━━━━━━━━━━━━ 01A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 01B ━━━━━━━━━━━━━━━━┓

**상태:** 머지 전 PR의 제안 변경입니다. 아직 적용되지 않았고, 아래 내용은 모두 diff만 보고 판단했습니다.

### 파일 변경

```
app/
├── http/
│   └── policy.py      + 신규: PolicyClient (타임아웃 + 재시도)
└── clients/
    ├── geo.py         ~ httpx.Client → PolicyClient
    ├── search.py      ~ httpx.Client → PolicyClient
    ├── email.py       ~ httpx.Client → PolicyClient(timeout=10)
    └── payments.py    ~ httpx.Client → PolicyClient
```

### 1. 클라이언트별 동작 비교

```diff
  client    op    timeout  tries  retry on       worst~
- geo       GET   10s      1      -              ~10s
+ geo       GET    5s      3      timeout, 5xx   ~16.5s
- search    GET    2s      1      -              ~2s
+ search    GET    5s      3      timeout, 5xx   ~16.5s
- email     POST  30s      1      -              ~30s
+ email     POST  10s      3      timeout, 5xx   ~31.5s
- payments  POST  20s      1      -              ~20s
+ payments  POST   5s      3      timeout, 5xx   ~16.5s
```

`worst~`는 3 × timeout에 재시도 대기 0.5s + 1s를 더한 대략값입니다. httpx의 timeout은 connect, read 같은 단계마다 따로 적용되고 요청 전체 시간 제한이 아니라서 실제 값은 달라질 수 있습니다. 대기 시간도 tenacity 버전에 따라 다를 수 있습니다.

### 2. 요청 한 번의 흐름 (`PolicyClient.request`)

```diff
  request(method, path, **kw):
+   up to 3 attempts:
      resp = httpx send(method, path, timeout=T)
      resp.raise_for_status()
      return resp
+     TimeoutException          → wait, retry
+     HTTPStatusError, ≥ 500    → wait, retry
+     4xx / ConnectError / etc. → raise immediately
+     wait: exponential, multiplier 0.5
+   3rd failure → re-raise original exception
```

**그대로인 것:** `raise_for_status()` 호출, 각 함수의 반환값, 최종 실패 시 올라가는 예외 타입(`reraise=True`라서 원래 예외가 그대로 나갑니다).

### 리뷰에서 짚을 점

- **결제가 중복될 수 있습니다.** `POST /charges`가 timeout이나 5xx에서 재시도됩니다. 서버가 이미 결제를 처리한 뒤 응답만 늦은 ReadTimeout이면 같은 결제가 다시 요청됩니다. diff에는 idempotency key가 없습니다. 게다가 timeout이 20s에서 5s로 줄어서 이런 상황이 더 자주 생길 수 있습니다.
- **메일도 같은 이유로 중복 발송될 수 있습니다.** `POST /send`가 재시도되고, timeout은 30s에서 10s로 줄었습니다.
- **search는 최대 대기 시간이 크게 늘어납니다.** 원래 약 2s면 실패했는데 이제 최악의 경우 약 16.5s까지 기다립니다. 호출하는 쪽의 시간 예산이 버틸 수 있는지 확인이 필요합니다.
- **timeout 값이 서비스마다 달랐던 것이 사라졌습니다.** email을 빼면 전부 5s로 통일됩니다. 이전 값을 의도적으로 정했던 것인지는 diff만으로는 알 수 없습니다.

### diff만으로는 알 수 없는 것

- 결제/메일 서버가 idempotency key를 지원하는지
- 상위 호출자에게 자체 재시도나 deadline이 있는지 (있다면 재시도가 겹칩니다)
- 이 네 파일 말고도 PolicyClient를 쓰게 될 곳이 있는지

POST는 재시도하지 않거나, 재시도 조건을 `ConnectTimeout`으로만 좁히거나, idempotency key를 붙이는 방향을 먼저 논의해 보는 걸 권합니다.

┗━━━━━━━━━━━━━━━━ 01B 끝 ━━━━━━━━━━━━━━┛

---

# 02 · f2-deps-ports-adapters
질문: 포트와 어댑터 구조 파이썬 패키지 11개의 의존 구조 (영어)

┏━━━━━━━━━━━━━━━━ 02A ━━━━━━━━━━━━━━━━┓

The only rule break is `app/domain → app/infra/sql`. It gives the core a direct import of an adapter, and it creates an import cycle.

```text
wiring    bootstrap    → api, cli,
                         infra/sql, infra/stripe, infra/mail
delivery  api          → services, schemas
          cli          → services
app       services     → domain, ports
          schemas      → domain
core      ports        → domain
          domain       → common, infra/sql ✗
adapters  infra/sql    → ports, domain, common
          infra/stripe → ports, common
          infra/mail   → ports, common
shared    common
```

The import closes two loops, and both pass through the ✗ edge:

```text
          ┌──────── ✗ ────────┐
          │                   ▼
       domain ◀────────── infra/sql
          ▲                   │
          └───── ports ◀──────┘
```

Anything that imports the core also pulls in the SQL adapter:

```text
api     → services → domain → infra/sql ✗
cli     → services → domain → infra/sql ✗
schemas → domain   → infra/sql ✗
ports   → domain   → infra/sql ✗
```

- **Everything else follows your rules.** `infra/stripe` and `infra/mail` depend only on `ports` and `common`, and only `bootstrap` wires the adapters in.
- **Caveat:** This list doesn't show which names `domain` takes from `infra/sql`. It also doesn't show whether the import runs when the module loads or inside a function. If it runs at load time, Python can raise circular-import errors depending on which module loads first. The usual fix is to move whatever `domain` needs behind an interface in `ports`, which `infra/sql` then implements.

┗━━━━━━━━━━━━━━━━ 02A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 02B ━━━━━━━━━━━━━━━━┓

No files were changed; you gave me a dependency listing, not a diff.

The main finding is that `app/domain` imports `app/infra/sql`. That breaks the first rule and creates a cycle through the core.

**Dependency graph** (arrow means "imports"; the `app/` prefix is dropped)

```
                    bootstrap
      ┌──────────┬──┴──────┬───────────┐
      ▼          ▼         ▼           ▼
     api        cli   infra/stripe infra/mail
   ┌──┴─────┐    │         └─────┬─────┘
   ▼        ▼    │               │
schemas services◀┘               ▼
   │      │  └────────────────▶ports
   │      │                      │
   ▼      ▼                      │
   └───┬──┘                      │
       ▼                         │
     domain ◀────────────────────┘
       ├──▶ common
       │
       ▼  ✗ core imports an adapter
   infra/sql ──▶ ports, domain, common
```

Not drawn: `bootstrap → infra/sql` (allowed), and `stripe`, `mail`, `sql → common` (fine).

**Check against your rules**

| Rule | Result | Evidence |
|---|---|---|
| Domain and services don't know infra | ✗ | `domain → infra/sql` directly. `services`, `schemas`, `ports`, `api` and `cli` all reach it through `domain`. |
| No cycles in the core | ✗ | `domain → infra/sql → domain`, and `domain → infra/sql → ports → domain` |
| Adapters implement `ports` | ✓ as far as imports show | All three `infra` packages import `ports`. An import list can't show whether they actually implement the interfaces. |
| Only `bootstrap` wires adapters | ✗ partial | `bootstrap` imports all three adapters, but `domain` also imports `infra/sql` |
| Everything else | ✓ | `common` imports nothing. `stripe` and `mail` stay out of the core. |

**Likely fix:** find what `domain` uses from `infra/sql`. If it's something like a repository or session, define an interface for it in `ports` and let `bootstrap` inject the implementation. If it's a plain type, move it into `domain` or `common`. I can't tell which from the import list alone.

┗━━━━━━━━━━━━━━━━ 02B 끝 ━━━━━━━━━━━━━━┛

---

# 03 · f3-flow-pii-phone
질문: 사용자 전화번호가 어디로 흘러가 어디에 저장되나

┏━━━━━━━━━━━━━━━━ 03A ━━━━━━━━━━━━━━━━┓

**핵심:** Postgres는 암호화하고 CS 화면은 마스킹하지만, `user.created` 이벤트에 전화번호가 평문으로 들어 있습니다. 그 결과 S3와 BigQuery에 평문 전화번호가 쌓이고, S3에는 기한 없이 남습니다.

**① 수집**
```text
앱 ─POST /signup: 평문─▶ API ─┬─ user.created: 평문 ─▶ Kafka
                              └─ AES 암호문 ─▶ Postgres users
```

**② Kafka 이후 (Kafka 자체에는 평문으로 7일 보존)**
```text
Kafka ─┬─ 매일 밤, 원본 그대로 ─▶ S3        ⚠ 평문
       ├─ email만 해시 ─────────▶ BigQuery  ⚠ 평문
       └─ 구독 ─▶ notify ─┬─ 평문 ─▶ 외부 SMS 업체  ⚠ 제3자
                          └─ 로그: 뒤 4자리만
```

**③ 조회**
```text
Postgres users ─읽기─▶ CS 도구 ─▶ 화면: 010-****-1234
```

**저장 위치별 상태** (위험한 순서)

| 저장 위치            | 전화번호 형태  | 보존 기간          |
|----------------------|----------------|--------------------|
| S3 아카이브          | **평문**       | **무기한**         |
| BigQuery             | **평문**       | 알려주지 않음      |
| 외부 SMS 업체        | 평문           | 알려주지 않음 (계약 확인 필요) |
| Kafka `user.created` | 평문           | 7일                |
| Postgres `users`     | AES 암호문     | 알려주지 않음      |
| notify 발송 로그     | 뒤 4자리       | 알려주지 않음      |
| CS 도구              | 마스킹해서 표시만 함 | 저장하지 않는 것으로 보임 (추정) |

**점검할 때 참고할 점**
- analytics 커넥터에서 해시 대상에 전화번호 필드를 추가해도 S3 문제는 남습니다. S3는 Kafka 원본을 그대로 아카이브하기 때문입니다. 근본적으로는 이벤트에서 전화번호를 빼거나 암호화해야 합니다. 이미 S3와 BigQuery에 쌓인 과거 데이터도 따로 정리해야 합니다.
- 이번에 주신 정보에는 API 요청 로그, APM, Kafka DLQ가 어떻게 처리되는지 없습니다. 이 중 하나라도 요청이나 이벤트 본문을 기록한다면 평문이 저장되는 곳이 더 있을 수 있습니다.

┗━━━━━━━━━━━━━━━━ 03A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 03B ━━━━━━━━━━━━━━━━┓

파일 변경은 없습니다. 적어주신 구조를 그대로 정리했습니다.

**전화번호 흐름 (DFD)**

```text
① 가입
[App] --POST /signup--> (API) --AES 암호화--> || PG users ||
                          |
                          +--평문--> || Kafka (7일) ||

② Kafka 소비 (토픽: user.created)
|| Kafka ||--평문--> (notify) --평문--> [SMS 업체]
                        |
                        +--뒤4자리--> || 발송 로그 ||

|| Kafka ||--평문*--> (analytics) --평문--> || BigQuery ||

|| Kafka ||--원본, 매일 밤--> || S3 (무기한) ||

③ 조회
|| PG users ||--복호화?--> (CS 도구) --마스킹--> [상담원]
```
`*` 커넥터는 `email`만 해시합니다. 그래서 전화번호는 평문 그대로 넘어갑니다.
`복호화?`는 추정입니다. 가려서라도 보여주려면 CS 도구가 복호화해야 하는데, 키를 어디서 가져오는지는 받은 정보에 없습니다.

**저장 위치별 형태**

| 위치 | 전화번호 형태 | 보존 기간 |
|---|---|---|
| PG `users` | AES 암호문 | 정보 없음 |
| Kafka `user.created` | **평문** | 7일 |
| S3 아카이브 | **평문** (토픽 원본) | **무기한** |
| BigQuery | **평문** | 정보 없음 |
| SMS 업체 | 평문 (발송에 필요) | 정보 없음 (업체 정책) |
| notify 발송 로그 | 뒤 4자리 | 정보 없음 |
| CS 화면 | `010-****-1234` | 화면 표시만 |

**점검할 곳**
- **S3 아카이브:** 평문을 기한 없이 보관합니다. 그래서 Kafka의 7일 보존은 실제로 적용되지 않는 셈입니다.
- **BigQuery:** 평문이 들어갑니다. 보존 기간과 접근 권한은 정보가 없습니다.
- **PG 암호화의 효과:** 평문 사본이 따로 두 곳(S3, BigQuery)에 있어서 효과가 제한적입니다.

**확인하지 못한 것**
- AES 키를 어디에 두고 누가 접근하는지
- S3와 BigQuery의 저장 시 암호화 여부와 접근 권한
- SMS 업체가 데이터를 얼마나 보관하는지(위탁 계약 조건)
- Kafka를 거쳐 가는 구간에 TLS가 적용되는지

┗━━━━━━━━━━━━━━━━ 03B 끝 ━━━━━━━━━━━━━━┛

---

# 04 · f4-timeline-duplicate-email
질문: 월 청구 메일이 두 번 가는 이유 (영어)

┏━━━━━━━━━━━━━━━━ 04A ━━━━━━━━━━━━━━━━┓

**File changes:** not applicable. No code or diff was provided, so this only explains the logs.

**Cause:** every step of rendering, sending and deleting took longer than the 30 s visibility timeout. SQS made m‑77 visible again at 02:00:33, while worker‑2 was still rendering. Worker‑4 received it a second later, and both workers sent the email.

```text
          SQS               worker-2         worker-4     SES
          |                 |                |            |
02:00:03  |-- m-77 h1 ----->|                |            |
          | hidden to :33   | render (48 s)  |            |
02:00:33  | visible again   |                |            |
02:00:34  |-- m-77 h2 ---------------------->|            |
          | hidden to 01:04 |                | render 55 s|
02:00:51  |                 |-- send email #1 ----------->|
02:00:51  |<- delete(h1) ---|                |            |
          |-- FAIL: stale ->|                |            |
02:01:04  | visible again   |                |            |
02:01:29  |                 |                |- send #2 ->|
02:01:29  |<- delete(h2) --------------------|            |
          |-- OK, removed ------------------>|            |
```

**Holds vs. work time** (1 char ≈ 3 s, starting at 02:00:00)

```text
           :00       :30       01:00     01:30
           |---------|---------|---------|
w2 hold     [=========]
w2 work     [===============] send #1, delete fails
w4 hold               [=========]
w4 work               [==================] send #2
visible               ^         ~~~~~~~~~~
```

- **Not the cause:** worker‑2's failed delete. The duplicate was already certain at 02:00:34, when worker‑4 got the message. The only effect of the failed delete was that worker‑4's delete was the one that removed the message.
- **Inference:** none of the logs show a visibility extension, which suggests the workers don't extend it. Otherwise m‑77 wouldn't have become visible again at 02:00:33.
- **Unlogged risk (inference):** m‑77 was also visible from 02:01:04 to 02:01:29 while worker‑4 was still working. A third worker could have picked it up and sent a third email. The logs show no third receive for this message.
- **Gap:** only customer 8812's logs were provided. Likely affected: any customer whose PDF takes longer than about 30 s to render, which is the 40–60 s group.

┗━━━━━━━━━━━━━━━━ 04A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 04B ━━━━━━━━━━━━━━━━┓

Worker-2 took 48 s on the message, but the queue only hides a message for 30 s after a worker receives it. At 02:00:33 SQS made m-77 visible again, and worker-4 picked it up and sent a second email.

```text
time      worker-2          SQS m-77          worker-4
          |                 |                 |
02:00:03  |<--- receive ----|                 |
          | render PDF      | hidden 30 s     |
          | (big invoice)   |                 |
02:00:33  |  still busy     | VISIBLE AGAIN   |  <- 30 s up
02:00:34  |                 |---- receive --->|
          |                 | hidden 30 s     | render PDF
02:00:51  | SES send #1     |                 |
02:00:51  |---- delete ---->|                 |
          |<-- FAIL: stale  |                 |
          |    handle       |                 |
02:01:04  |                 | visible again   |  (inferred)
02:01:29  |                 |                 | SES send #2
02:01:29  |                 |<--- delete OK --|
```

```text
worker-2 busy  02:00:03 ─────────────── 02:00:51   48 s
worker-4 busy          02:00:34 ──────────────── 02:01:29   55 s
queue timeout  |── 30 s ──|
```

The duplicate was locked in at 02:00:34, when worker-4 received the message. Worker-2's failed delete at 02:00:51 is a symptom, not the cause. By then its receipt handle was stale, and nothing stopped it from sending.

**Caveats that affect the fix:**
- Worker-4 also ran longer than 30 s, so m-77 probably became visible a third time at 02:01:04. If another worker had been polling then, the customer would have gotten three emails. The same can happen to any customer whose PDF takes 40–60 s.
- Raising the visibility timeout makes this rarer but doesn't eliminate it. A slow render, a retry or a crash can still push a worker past the limit. Two changes close the gap:
  - While rendering, have the worker keep calling `ChangeMessageVisibility` to extend the hidden period.
  - Before calling SES, have the worker claim a `(customer, month)` key with a conditional insert, so a second worker skips the send.

┗━━━━━━━━━━━━━━━━ 04B 끝 ━━━━━━━━━━━━━━┛

---

# 05 · h1-diff-auth-middleware
질문: 머지 전 PR: 인증 처리를 라우트별 호출에서 미들웨어로 옮김 (TS)

┏━━━━━━━━━━━━━━━━ 05A ━━━━━━━━━━━━━━━━┓

**머지 전 PR (proposed)**: 라우트마다 하던 인증 검사를 전역 미들웨어 하나로 옮깁니다. 가장 큰 변화는 **`GET /reports/export`가 이제 로그인을 요구한다는 점**입니다. 지금은 인증 없이 전체 데이터를 내보내고 있습니다.

```
src/
├── server.ts            수정: authenticate 전역 적용, /admin에 requireRole 추가
├── middleware/auth.ts   신규: authenticate, requireRole
└── routes/
    ├── orders.ts        수정: requireUser 제거, req.user 사용
    ├── reports.ts       수정: requireUser 제거, export 인자 변경
    └── admin.ts         수정: requireUser와 역할 검사 제거
```

**라우트별 인증 (before → after)**

| 라우트 | Before | After |
|---|---|---|
| **GET /reports/export** | **인증 없음, `exportAll()` 전체 반환** | **로그인 필요, `exportAll(user.id)`** |
| POST /admin/refunds/:id | requireUser + admin 검사 → 403 (빈 본문) | authenticate + requireRole → 403 JSON |
| GET·POST /orders | requireUser | authenticate (동작 동일) |
| GET /reports/monthly | requireUser | authenticate (동작 동일) |
| /health | 공개 | 공개 (authenticate보다 먼저 등록) |
| 매칭 안 되는 경로 | 404 | 비로그인 요청은 401 |

**미들웨어 순서**

```diff
  요청
   → express.json()
   → /health ───────────────────── 공개
+  → authenticate   sid 없음/무효 → 401
   → /orders
   → /reports
+  → /admin → requireRole("admin")  → 403
   → (404)
```

**주의할 점**
- `req.cookies`는 cookie-parser가 있어야 채워집니다. diff의 `server.ts`에는 cookie-parser가 없습니다. 없으면 모든 요청이 401이 됩니다. 기존 `requireUser`가 쿠키를 어떻게 읽었는지는 이 diff만으로는 알 수 없습니다.
- `exportAll(req.user.id)`를 쓰려면 `services/reports`의 시그니처도 바뀌어야 하는데, 이 PR에는 그 파일이 없습니다. 기존 export 소비자가 전체 데이터를 받고 있었다면 이제 본인 데이터만 받게 됩니다.
- Express 4라면 async 미들웨어인 `authenticate`에서 `verifySession`이 reject될 때 에러가 `next`로 전달되지 않아 요청이 멈춥니다. Express 5에서는 문제가 없습니다.

┗━━━━━━━━━━━━━━━━ 05A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 05B ━━━━━━━━━━━━━━━━┓

# PR 인증 처리 변경 (머지 전, 제안된 변경)

아래 내용은 PR diff만 보고 정리했습니다. `requireUser`, `verifySession`, `services/*` 코드는 확인하지 않았습니다.

## 파일 변경

```
src/
├─ server.ts             M  전역 authenticate, /admin에 requireRole 추가
├─ middleware/
│  └─ auth.ts            A  authenticate, requireRole 새로 추가
└─ routes/
   ├─ orders.ts          M  requireUser 제거 → req.user 사용
   ├─ reports.ts         M  requireUser 제거, export 호출 변경
   └─ admin.ts           M  requireUser와 role 체크 제거
```

## 요청 흐름 (server.ts 기준)

```diff
 요청
  │
 express.json()
  │
 /health ───────────────▶ healthRouter  (공개, 그대로)
  │
+authenticate   req.cookies?.sid → verifySession
+  ├─ 실패 → 401 {"error":"unauthenticated"}
+  └─ 성공 → req.user = user, next()
  │
 /orders  ──────────────▶ ordersRouter
 /reports ──────────────▶ reportsRouter
-/admin   ──────────────▶ adminRouter
+/admin   ─▶ requireRole("admin") ─▶ adminRouter
+              └─ role ≠ admin → 403 {"error":"forbidden"}
```

인증 검사가 각 핸들러에서 하던 방식에서 라우터 앞의 미들웨어 한 곳으로 옮겨집니다.

## 라우트별 인증 비교

| 경로 | 이전 | 이후 |
|---|---|---|
| `GET /health` | 공개 | 공개 (변경 없음) |
| `GET·POST /orders` | 핸들러 안에서 `requireUser` | 전역 `authenticate` |
| `GET /reports/monthly` | 핸들러 안에서 `requireUser` | 전역 `authenticate` |
| `GET /reports/export` | **인증 없음**, `exportAll()` | `authenticate` + `exportAll(user.id)` |
| `POST /admin/refunds/:id` | `requireUser` + role 체크, 403 빈 body | `authenticate` + `requireRole`, 403 JSON |
| 정의되지 않은 경로 | 404 | 로그인 안 했으면 401 (추론) |

## 머지 전에 확인할 것

1. **cookie-parser가 필요합니다.** `req.cookies`는 cookie-parser가 있어야 채워지는데, `server.ts`에는 `express.json()`만 등록돼 있습니다. 다른 곳에서도 등록하지 않는다면 `/health`를 뺀 모든 요청이 401을 받습니다. 기존 `requireUser`가 세션을 어떻게 읽었는지는 diff에 없어서 비교할 수 없었습니다.
2. **`/reports/export`의 동작이 달라집니다.** 이전에는 누구나 전체 데이터를 받을 수 있었고, 이제는 로그인이 필요하며 사용자 기준으로 좁혀집니다. 보안 수정으로 보이지만 `services/reports.exportAll`의 시그니처 변경이 diff에 없습니다. 이 함수가 인자를 무시한다면 로그인한 사용자 누구나 전체 데이터를 계속 받을 수 있습니다.
3. **async 미들웨어 에러 처리를 봐야 합니다.** Express 4에서는 `verifySession`이 reject되어도 에러가 `next`로 넘어가지 않아 요청이 멈춥니다. Express 버전은 diff로 확인할 수 없습니다.
4. **`req.user` 타입 선언이 diff에 없습니다.** `Request`에 `user`를 추가하는 타입 확장이 따로 없거나 `user`가 optional이면 `req.user.id`에서 TS 에러가 날 수 있습니다.
5. **admin 보호가 mount 한 곳에만 남습니다.** 이제 `adminRouter` 자체에는 검사가 없어서, 다른 경로에 mount하거나 테스트에서 직접 쓰면 보호 없이 열립니다.
6. **응답 형식이 바뀝니다.** admin 403은 빈 body에서 JSON으로 바뀝니다. 기존 `requireUser`가 무엇을 응답했는지는 알 수 없어서, 401 응답 호환성은 확인하지 못했습니다.
7. **`lib/requireUser`는 삭제되지 않았습니다.** diff에 삭제가 없어서, 다른 곳에서 아직 쓰는지는 알 수 없습니다.

┗━━━━━━━━━━━━━━━━ 05B 끝 ━━━━━━━━━━━━━━┛

---

# 06 · h3-deps-layer-violation
질문: 모노레포 12개 패키지의 의존 구조 (계층 위반 있음, 영어)

┏━━━━━━━━━━━━━━━━ 06A ━━━━━━━━━━━━━━━━┓

No files were changed. This view is built only from the import list you gave me.

**Who imports whom**

Columns follow the same top-to-bottom order as the rows. In a clean layering every mark sits to the right of the row's own column. Only one mark doesn't.

```
              cart auth ui   apic db   dom  log  util conf
apps/web      ●    ●    ●    ●    ·    ·    ·    ·    ●
apps/admin    ·    ●    ●    ●    ·    ·    ·    ·    ●
apps/api      ·    ·    ·    ·    ●    ●    ●    ·    ●
features/cart ·    ·    ●    ●    ·    ●    ·    ●    ·
features/auth ·    ·    ●    ●    ·    ·    ·    ●    ·
ui            ✗    ·    ·    ·    ·    ·    ·    ●    ·
api-client    ·    ·    ·    ·    ·    ●    ·    ●    ●
db            ·    ·    ·    ·    ·    ●    ●    ·    ●
domain        ·    ·    ·    ·    ·    ·    ·    ●    ·
logger        ·    ·    ·    ·    ·    ·    ·    ·    ●
```
`utils` and `config` import nothing.

**The two things that matter**

```
1. Cycle: the design system depends on a feature

   apps/admin ─► features/auth ─► ui ─► features/cart
                                  ▲          │
                                  └──────────┘

   · ui ⇄ features/cart import each other.
   · ui is meant to be shared, but it can't be used
     without also pulling in the cart feature.
   · apps/admin never imports cart, but still gets it
     through auth → ui.

2. Server-only boundary: holds

   apps/api ─► db ─► domain, logger, config

   · Nothing apps/web or apps/admin imports, directly
     or indirectly, leads to db or logger.
   · domain is shared by server and browser code, so it
     must stay free of Prisma. Right now it imports
     only utils.
```

**Suggested fix:** Remove the `ui → features/cart` import. Whatever `ui` uses from cart, such as a cart badge, should either move into `features/cart` or be passed in as props or slots. After that the graph has no cycles and `ui` sits just above `utils` as intended.

One limit: all of this is based only on the listed imports. Type-only imports, dynamic imports and re-exports aren't covered. Running a tool like `madge --circular` or `dependency-cruiser` on the actual repo would confirm both findings.

┗━━━━━━━━━━━━━━━━ 06A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 06B ━━━━━━━━━━━━━━━━┓

**Takeaway:** there is one layering violation. `ui` imports `features/cart`, which creates a cycle and means every package that uses `ui` also pulls in the cart feature. `db` is correctly isolated.

```text
apps      apps/web    → features/cart, features/auth,
                        ui, api-client, config
          apps/admin  → features/auth, ui, api-client, config
          apps/api    → domain, db, logger, config
features  cart        → ui, api-client, domain, utils
          auth        → ui, api-client, utils
shared    ui          → utils, features/cart ✗
          api-client  → domain, utils, config
          db          → domain, logger, config  [server]
          logger      → config
core      domain      → utils
base      utils
          config

cycle     ui ──────────▶ features/cart
           ▲                  │
           └──────────────────┘
           ✗ design system imports a feature
```

What the violation pulls into each package that uses `ui`:

```text
apps/admin → features/auth → ui → features/cart ✗
             (admin never imports cart, but ships it)
features/auth → ui → features/cart ✗
apps/web   → already imports cart directly (no new cost)
```

`db` stays server-only. Only `apps/api` imports it, and neither `apps/web` nor `apps/admin` has any path that reaches it.

**Suggested fix:** move whatever `ui` takes from `features/cart` either down into `ui` or `utils`, or up into `apps/web`. That breaks the cycle, and `apps/admin` stops shipping cart code.

┗━━━━━━━━━━━━━━━━ 06B 끝 ━━━━━━━━━━━━━━┛

