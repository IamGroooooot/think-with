# holdout 블라인드 출력: 새 스킬 후보 vs 0.1.4

케이스마다 두 답변을 A와 B로 무작위로 배치했습니다. 두 답변 모두 플러그인을 설치한 상태의 답변이고, 하나는 lay-out 수정 후보, 다른 하나는 0.1.4입니다. 답변 본문은 수정하지 않았습니다.

---

# 01 · h1-diff-auth-middleware
질문: 머지 전 PR: 인증 처리를 라우트별 호출에서 미들웨어로 옮김 (TS)

┏━━━━━━━━━━━━━━━━ 01A ━━━━━━━━━━━━━━━━┓

# PR 인증 처리 변경 (머지 전, 아직 적용 안 됨)

인증 방식이 핸들러마다 `requireUser`를 부르던 구조에서 전역 미들웨어 체인으로 바뀝니다.

## 파일 변경

```
src/
├─ server.ts            ~ authenticate 전역 등록,
│                         /admin에 requireRole 추가
├─ middleware/
│  └─ auth.ts           + 신규 (authenticate, requireRole)
└─ routes/
   ├─ orders.ts         - requireUser 제거 → req.user
   ├─ reports.ts        - requireUser 제거 → req.user
   │                    ~ exportAll()에 user.id 인자 추가
   └─ admin.ts          - requireUser와 role 체크 제거
```

`services/reports`의 `exportAll` 시그니처 변경은 diff에 없습니다. 변경 데이터가 없어서 반영됐는지 알 수 없습니다.

## 라우트별 인증 비교

```
 라우트                  이전              이후
 ───────────────────────────────────────────────────
 /health                없음              없음
 GET  /orders           requireUser       authenticate
 POST /orders           requireUser       authenticate
 GET  /reports/monthly  requireUser       authenticate
-GET  /reports/export   없음 (전체 조회)
+GET  /reports/export                     authenticate
+                                         (user.id 범위)
 POST /admin/refunds/:id requireUser      authenticate
                        + role 체크       + requireRole
-  403 응답 본문        빈 본문 (.end())
+  403 응답 본문                          {error:"forbidden"}
+매칭 안 되는 경로       404 (추정)        401 (추정)
```

실제 동작이 바뀌는 곳은 `/reports/export`입니다. 이전에는 인증 없이 전체 데이터를 내보냈습니다.

## 요청 처리 순서 (이후)

```
요청
 ├─ express.json()
 ├─ /health ─────────────────→ healthRouter (공개)
+├─ authenticate
+│   ├─ verifySession(req.cookies?.sid)
+│   ├─ user 없음 → 401 {error:"unauthenticated"}
+│   └─ req.user = user
 ├─ /orders  ────────────────→ ordersRouter
 ├─ /reports ────────────────→ reportsRouter
 └─ /admin
+    ├─ requireRole("admin")
+    │   └─ role 불일치 → 403 {error:"forbidden"}
     └─ adminRouter
```

## diff만으로는 확인할 수 없는 부분

- **cookie-parser:** `server.ts`에 등록돼 있지 않습니다. 없으면 `req.cookies`가 항상 undefined이고, 그러면 모든 보호 라우트가 401을 반환합니다. 다른 곳에서 등록하는지는 알 수 없습니다.
- **async 에러 처리:** Express 4에서는 `authenticate` 안의 `verifySession`이 reject되면 그 에러가 잡히지 않습니다. Express 5라면 에러 핸들러로 넘어갑니다. 버전은 diff에 없습니다.
- **`req.user` 타입:** `Request` 타입 확장(declaration merging)이 diff에 없습니다. 없으면 TS 컴파일 에러가 날 수 있습니다.
- **기존 동작과 같은지:** 이전 `requireUser`의 401 응답 형식과 세션을 읽는 방식이 새 코드와 같은지는 비교할 자료가 없습니다.

┗━━━━━━━━━━━━━━━━ 01A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 01B ━━━━━━━━━━━━━━━━┓

**머지 전 PR(proposed)**: 라우트마다 하던 인증을 전역 미들웨어 한 곳으로 옮깁니다. 그 과정에서 `/reports/export`가 처음으로 인증을 거치게 됩니다.

```
src/
├─ server.ts             authenticate 전역 등록, /admin에 requireRole
├─ middleware/auth.ts    (신규) authenticate, requireRole
└─ routes/
   ├─ orders.ts          requireUser 제거, req.user 사용
   ├─ reports.ts         requireUser 제거, export에 user.id 전달
   └─ admin.ts           requireUser·role 검사 제거
```

**요청 처리 경로 (+ 추가 / - 제거)**

```diff
 요청 ──▶ express.json()
  │
  ├─ /health ──────▶ healthRouter      (계속 인증 없음)
  │
+ ├─ authenticate    cookies.sid → verifySession
+ │    └─ user 없음 → 401 {error:"unauthenticated"}
  │
  ├─ /orders   GET /, POST /
- │    ├─ requireUser(req,res) → 없으면 return
  │    └─ orders.list / create(user.id)
  │
  ├─ /reports
  │    ├─ GET /monthly
- │    │    ├─ requireUser(req,res) → 없으면 return
  │    │    └─ reports.monthly(user.id)
  │    └─ GET /export
- │         └─ 인증 없이 exportAll()
+ │         └─ 인증 후 exportAll(req.user.id)
  │
  └─ /admin
+      ├─ requireRole("admin") → 403 {error:"forbidden"}
       └─ POST /refunds/:id
-           ├─ requireUser → 없으면 return
-           ├─ role ≠ admin → 403 (빈 본문)
            └─ admin.refund(id)
```

- `orders`, `monthly`, `admin`의 인증 조건은 그대로이고 검사 위치만 옮겨졌습니다. 다만 403 응답이 빈 본문에서 JSON으로 바뀝니다. `requireUser`의 기존 401 형식은 diff에 없어서 그 부분이 달라지는지는 알 수 없습니다.
- `/health` 뒤의 모든 경로는 매칭되는 라우트가 없어도 인증을 먼저 거칩니다. 그래서 로그인하지 않은 요청은 404 대신 401을 받습니다.

**머지 전 확인할 점**
1. diff 어디에도 `cookie-parser`가 없습니다. 등록돼 있지 않으면 `req.cookies`가 항상 `undefined`여서 `/health`를 뺀 모든 요청이 401이 됩니다.
2. `authenticate`는 async 함수입니다. Express 4에서는 `verifySession`이 throw하면 에러가 에러 핸들러로 넘어가지 않아 요청이 멈춥니다. `req.user` 타입 선언(augmentation)도 diff에 없습니다.
3. `/export`를 인증 없이 호출하던 쪽(배치 등)은 이제 401을 받습니다. `exportAll(userId)`가 전체 대신 해당 사용자 데이터만 내보내게 되는지는 services diff가 없어서 확인하지 못했습니다.

┗━━━━━━━━━━━━━━━━ 01B 끝 ━━━━━━━━━━━━━━┛

---

# 02 · h2-concept-pkce-bff
질문: PKCE + BFF 로그인에서 브라우저·BFF·IdP 사이에 뭐가 오가고 토큰이 어디 있나 (영어)

┏━━━━━━━━━━━━━━━━ 02A ━━━━━━━━━━━━━━━━┓

**Takeaway:** only the opaque `sid` cookie stays in the browser. The three tokens go from Auth0 to the BFF over a server-to-server call and are stored in Redis. The browser only sees one-time values in URLs (`cc`, `state`, `code`).

```text
Browser        BFF         Redis        Auth0      Services
   |            |            |            |            |
 ·· 1. start login ··
   |-GET /login>|            |            |            |
   |            |-cv,state-->|            |            |
   |<-302 + tmp-|            |            |            |
   |-- GET /authorize cc,state ---------->|            |
   |<---- user signs in ----------------->|            |
   |<- 302 /callback?code,state ----------|            |
 ·· 2. callback + code exchange ··
   | /callback  |            |            |            |
   | code,state |            |            |            |
   |-+ tmp ---->|            |            |            |
   |            |-get by tmp>|            |            |
   |            |<-cv,state--|            |            |
   |            | check state|            |            |
   |            | code,cv,client secret   |            |
   |            |-- POST /oauth/token --->|            |
   |            |<- AT,RT,IDT ------------|            |
   |            | key = sid  |            |            |
   |            |-AT,RT,IDT->|            |            |
   | 302 to app |            |            |            |
   |<-+ sid ----|            |            |            |
 ·· 3. every API call ··
   | /api/*     |            |            |            |
   |-+ sid ---->|            |            |            |
   |            |-get sid--->|            |            |
   |            |<-AT,RT-----|            |            |
   |            | if AT expired:          |            |
   |            |-- RT + secret --------->|            |
   |            |<- new AT ---------------|            |
   |            |-new AT---->|            |            |
   |            |-- Authorization: Bearer AT --------->|
   |            |<- response ---------------------------|
   |<-response--|            |            |            |
```
`cv` = code_verifier · `cc` = code_challenge (derived from cv) · `tmp` = temporary cookie that keys the PKCE entry · AT / RT / IDT = access / refresh / ID token

**Where each item ends up**

| Item | Where it's stored | Visible to the browser? |
|---|---|---|
| `cv` | Redis temp entry | No. Only `cc` passes through the browser |
| `state` | Redis temp entry | Yes, in the redirect URLs |
| `code` | Nowhere; used once | Yes, in the callback URL. It's useless without `cv` and the client secret |
| AT | Redis session; sent to Services | No |
| RT, IDT | Redis session | No |
| `sid` | Browser cookie (HttpOnly) | Stored, but JavaScript can't read it |

**Caveats that could change a decision**
- **`tmp` cookie attributes:** your setup doesn't give them. The `/callback` request is a cross-site navigation coming from Auth0, so the cookie has to be `Lax`. With `Strict`, the browser won't send it and the `state` lookup fails.
- **`sid` and subdomains:** app. and api.example.com count as the same site. That's why `SameSite=Lax` still sends `sid` on the SPA's `fetch` calls, provided the SPA uses `credentials: 'include'` and the BFF sends CORS headers that allow credentials for that exact origin. It also means SameSite gives no CSRF protection against other `*.example.com` hosts.
- **Parallel refreshes (my inference):** your setup doesn't say whether Auth0 refresh-token rotation is on. If it is, two parallel requests that both find the AT expired can reuse the same RT. Auth0's reuse detection can then revoke the whole session. Locking the refresh per session prevents this.

┗━━━━━━━━━━━━━━━━ 02A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 02B ━━━━━━━━━━━━━━━━┓

Nothing in the repo changed, so there are no file edits to show. This is only a picture of the design you described.

**Sequence: what passes between the browser, the BFF and Auth0**

```text
Browser                   BFF                   Auth0
   |                       |                      |
   |-- GET /login -------->|                      |
   |                       | new verifier + state |
   |                       | -> Redis (tmp key)   |
   |<-- 302 + tmp cookie --|                      |
   |-- /authorize code_challenge, state --------->|
   |<===== user signs in at Auth0 ===============>|
   |<-- 302 /callback?code,state -----------------|
   |-- code,state,tmp ---->|                      |
   |                       | check state vs Redis |
   |                       |-- /oauth/token ----->|
   |                       |  code+verifier+secret|
   |                       |<-- AT, RT, ID -------|
   |                       | -> Redis session[sid]|
   |<-- Set-Cookie sid, 302|                      |
   |                       |                      |
   |-- /api/* + sid cookie>|                      |
   |                       | Redis[sid] -> tokens |
   |                       |-- refresh (if exp) ->|
   |                       |<-- new AT -----------|
   |                       | Bearer AT -> internal|
   |<-- API response ------|                      |
```

**Data flow: where the secrets and tokens are stored**

```text
(/login) --verifier,state--> ||Redis tmp|| --> (/callback)

[Auth0] --AT,RT,ID--> (/callback) --AT,RT,ID--> ||Redis sid||

(/callback) --sid (HttpOnly,Secure,Lax)--> [Browser]

[Browser] --sid--> (/api/*) <--AT,RT-- ||Redis sid||
(/api/*) --Bearer AT--> [Internal services]
```

The browser only ever holds `code_challenge`, `state`, `code`, the temporary cookie and `sid`. The access token, refresh token, ID token, `code_verifier` and client secret all stay on the server side.

Your description doesn't settle these points:
- **Refresh token rotation:** it's unknown whether Auth0 returns a new refresh token on refresh, and whether the BFF writes it back to Redis.
- **Temporary Redis entry:** it's unknown whether it's deleted after `/callback`, which would make it single-use.
- **ID token:** it's stored, but nothing in the flow reads it.
- **Session lifetime:** it's unknown how long the `sid` session lasts compared with the refresh token's lifetime.
- **CSRF on `/api/*`:** SameSite=Lax blocks cross-site POSTs. It's unknown whether there's also a CSRF token or Origin check, which matters for GET requests with side effects.
- **Temporary cookie attributes (my inference):** it must be sent on Auth0's top-level redirect back to `/callback`, so it needs SameSite=Lax or None, not Strict.

┗━━━━━━━━━━━━━━━━ 02B 끝 ━━━━━━━━━━━━━━┛

---

# 03 · h3-deps-layer-violation
질문: 모노레포 12개 패키지의 의존 구조 (계층 위반 있음, 영어)

┏━━━━━━━━━━━━━━━━ 03A ━━━━━━━━━━━━━━━━┓

```text
apps      web      admin      api
features  cart     auth
shared    ui       api-client
server    db                       only apps/api imports ✓
core      domain   logger
base      utils    config

every other edge points down a layer or more
✗ upward: ui → features/cart      cycle: cart ⇄ ui
  admin → ui → features/cart      admin now bundles cart
  auth  → ui → features/cart      auth now depends on cart
```

**Takeaway:** There is one bad edge, `ui → features/cart`. It turns the design-system package into a feature package, creates a cycle, and pulls cart into `apps/admin` and `features/auth` even though neither imports cart.

- The list doesn't say which `ui` file imports cart. Look for a cart-aware component, such as a cart badge in a header, and move it into `features/cart`, or have `ui` take it as a prop or slot.
- `db` is safe as the list stands, because only `apps/api` reaches it. A lint rule like `no-restricted-imports` or an Nx boundary tag would keep it that way.

┗━━━━━━━━━━━━━━━━ 03A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 03B ━━━━━━━━━━━━━━━━┓

**File changes:** none. This is a map of the current dependency graph.

**1. Layered dependency graph** (arrows point to what each package imports)

```
apps      apps/web    → cart, auth, ui, api-client, config
          apps/admin  → auth, ui, api-client, config
          apps/api    → domain, db, logger, config
            │
feature   features/auth → ui, api-client, utils
            │
  ┌──────── cycle ─────────────────────────────┐
  │ features/cart ──imports──▶ ui              │
  │       ▲                    │               │
  │       └──────imports───────┘               │
  │ cart → api-client, domain, utils           │
  │ ui   → utils                               │
  └────────────────────────────────────────────┘
            │
service   api-client → domain, utils, config
          db         → domain, logger, config   [server]
            │
core      domain → utils
          logger → config
            │
leaf      utils      config
```

**2. What each app pulls in transitively**

```
package        web   admin  api   note
─────────────  ────  ─────  ────  ──────────────────────
features/cart  yes   yes*   no    *admin gets it via ui
features/auth  yes   yes    no
ui             yes   yes    no
api-client     yes   yes    no
domain         yes   yes    yes
utils          yes   yes    yes
config         yes   yes    yes
logger         no    no     yes
db             no    no     yes   server-only: OK
```

**What the map shows:**
- **There's a cycle between `ui` and `features/cart`.** `ui` is meant to be the shared design system, but it imports a feature package. Because of that, every package that uses `ui` also pulls in cart, `api-client` and `domain`. That's why `apps/admin` ships cart code it never imports directly.
- **The server-only rule for `db` holds.** Only `apps/api` reaches `db`, directly or indirectly, so neither frontend app can bundle Prisma.
- **To fix it,** remove the `ui → features/cart` import. Either move the shared piece into `ui` itself or into a new lower-level package. Once that's gone, the graph has no cycles and `ui` sits just above `utils`.

┗━━━━━━━━━━━━━━━━ 03B 끝 ━━━━━━━━━━━━━━┛

---

# 04 · h4-process-deploy-handoffs
질문: 배포 절차에서 누가 언제 뭘 넘겨받나, 왜 하루 넘게 걸리나

┏━━━━━━━━━━━━━━━━ 04A ━━━━━━━━━━━━━━━━┓

머지 이후 실제 작업 시간은 staging 8분과 prod 6분 정도이고, QA 확인 시간은 주어진 정보에 없습니다. 나머지는 모두 넘겨받을 때까지 기다리는 시간입니다.

**누가 누구에게 무엇을 넘기는가**

```text
Dev      Rev      GHA      QA       RM       SRE/Argo OnCall
 |        |        |        |        |        |        |
 |--- PR/CI 12m -->|        |        |        |        |
 |-- PR ->|        |        |        |        |        |  2~3h 대기
 |<-- ok -|        |        |        |        |        |
 |---- merge ----->|        |        |        |        |  ▶ 머지
 |        |        |- stg ->|        |        |        |  8분, 다음 10/16시까지 대기
 |        |        |        |- pass->|        |        |  QA 소요 미상
 |        |        |        |        |- tag ->|        |  1시간 이내
 |        |        |        |        |        |        |  Slack 승인 평균 3h, 근무시간만
 |        |        |        |        |        |- prod->|  6분 배포 + 30분 관찰
 |        |        |        |        |        |<-rollbk|  에러율 2% 넘으면
```

**하루를 넘기는 경우 (예: 11시 머지, 근무 종료 18시로 가정)**

```text
D1 11:00  merge
   11:08  staging 배포 완료
          ░░░░░░░░░░ QA 배치 대기 ~5h
   16:00  QA 확인 (소요 시간 미상)
  ~17:00  tag 생성
          ░░░░ SRE 대기 (평균 3h) → 18시 근무 종료
          ░░░░░░░░░░░░░░ 밤사이 대기
D2 오전   SRE 승인 → prod 6분 → 30분 관찰
```

16시 이후에 머지하면 첫 QA가 다음 날 10시라서 처음부터 하룻밤을 기다립니다.

- 가장 큰 원인은 시간이 정해진 관문 두 개가 연달아 있다는 점입니다. QA는 하루 두 번(10시, 16시)만 확인하고, SRE는 근무시간에만 승인합니다. 16시 QA를 통과해도 태그 생성(최대 1시간)과 SRE 대기(평균 3h)를 더하면 근무시간을 넘기기 쉽고, 그러면 배포가 다음 날로 넘어갑니다.
- SRE 근무시간과 QA 확인 소요 시간은 주어지지 않아서 18시와 "미상"으로 두었습니다. 실제 값에 따라 16시 QA를 통과한 건이 당일에 배포될 수 있는지가 달라집니다.

┗━━━━━━━━━━━━━━━━ 04A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 04B ━━━━━━━━━━━━━━━━┓

**파일 변경:** 해당 없음. 절차 설명만 있고 코드나 설정 변경은 없습니다.

**누가 누구에게 무엇을 넘기는가** (선 위의 라벨이 넘겨지는 것)

```text
[개발자]       PR 올림
     │ PR
     ▼
[CI]           테스트·린트 (~12분)
     │ 통과 결과
     ▼
[리뷰어]       승인 (대기 2~3h)
     │ 승인
     ▼
[개발자]       main 머지        ◀ 측정 시작
     │ main 커밋
     ▼
[GH Actions]   빌드 → staging 배포 (~8분)
     │ staging 빌드
     ▼
[QA팀]         수동 확인 (10시·16시 배치)
     │ QA 통과
     ▼
[릴리스 매니저] 태그 생성 (≤1h)
     │ 태그
     ▼
[Argo CD]      prod 배포 준비
     │ Slack 승인 요청
     ▼
[SRE]          승인 (근무시간, 평균 3h)
     │ 승인
     ▼
[Argo CD]      prod 배포 (~6분)
     │ 배포 완료
     ▼
[온콜]         에러율 30분 관찰
     ├─ ≤2% → 완료
     └─ >2% → 롤백
```

**머지부터 prod까지 시간표** (주신 평균값 기준. `?`는 제공되지 않은 값)

```text
A) 16시 배치 직후 머지 (16:30)
16:30  머지
16:38  staging 배포 완료
       ░░░░░░░░ QA 배치 대기 ~17h20m
10:00  (익일) QA 시작, 소요 ?
~11:00 태그 (QA 결과 확인 후 ≤1h)
       ░░░ SRE 승인 대기 평균 3h
~14:00 승인 → 14:06 prod 배포
14:36  관찰 종료          합계 ≈ 22h + QA 소요

B) 오전 배치 직후 머지 (10:30)
10:30  머지 → 10:38 staging
       ░░░░ QA 배치 대기 ~5h20m
16:00  QA 시작, 소요 ?
~17:00 태그
       ░░░ SRE 대기 3h → 근무시간을 넘김
       → 익일로 넘어감 (추정, 근무 종료 시각 ?)
```

- 실제로 작업하는 시간은 빌드 8분, 배포 6분, 관찰 30분을 합쳐 약 45분입니다. 나머지는 모두 사람을 기다리는 시간입니다.
- 가장 크게 늘어지는 곳은 **QA 배치 대기**(최대 약 17시간)와 **SRE 승인 대기**(평균 3시간, 근무시간에만 승인)입니다. 두 대기가 이어지면 머지한 시각과 상관없이 하루를 넘기기 쉽습니다.
- 확인이 필요한 값은 QA 한 번에 걸리는 시간과 SRE 근무 종료 시각입니다. 이 두 값에 따라 B 경우가 하루를 넘기는지가 정해집니다.

┗━━━━━━━━━━━━━━━━ 04B 끝 ━━━━━━━━━━━━━━┛

---

# 05 · 05-deps-cycle
질문: 25개 모듈 import 목록의 의존 구조 (패키지 수준 순환 있음)

┏━━━━━━━━━━━━━━━━ 05A ━━━━━━━━━━━━━━━━┓

파일 변경은 해당 없습니다. 제공된 import 목록만 분석했고 코드는 수정하지 않았습니다.

**① 계층별 모듈 (out = import하는 모듈 수, in = 이 모듈을 import하는 모듈 수)**

```
layer     module                  out  in
────────  ──────────────────────  ───  ──
entry     api/routes/users          3   0
          api/routes/billing        3   0
          api/routes/admin          3   0
          jobs/nightly_invoices     2   0
          jobs/cleanup              2   0
api       api/deps                  2   3
services  users/profile             4   3
          users/plan                3   1
          users/auth                3   2
          billing/invoice           5   3
          billing/pricing           2   2
          billing/payment           3   1
          notify/email              2   1
          notify/templates          1   1
domain    user                      1   2
          invoice                   1   2
          plan                      1   2
          money                     0   3
infra     db                        2   6  ◄ hub
          settings                  0   6  ◄ hub
          redis                     1   1
          stripe_client             2   1
          smtp                      1   1
common    logging                   0   3
          errors                    0   3
```

- 모든 import는 같은 계층이나 더 아래 계층을 향합니다. 아래 계층이 위 계층을 import하는 경우는 없습니다.
- 모듈끼리 순환하는 import도 없습니다.
- 계층을 건너뛰는 import는 있습니다: routes→services 직접, jobs→infra, domain/user→common.

**② 가장 긴 경로이자 users ⇄ billing 교차 의존**

```
services/billing/invoice   ◄ routes/billing, routes/admin,
│                            jobs/nightly_invoices
├─► users/profile          billing → users
│   └─► users/plan
│       └─► billing/pricing      users → billing
│           └─► domain/plan
│               └─► domain/money
├─► billing/pricing   (직접)
└─► notify/email ─► notify/templates, infra/smtp
```

- 패키지 단위로 보면 `services/users`와 `services/billing`이 서로 의존합니다. `invoice→profile`과 `plan→pricing` 두 import 때문입니다.
- 가장 긴 경로는 7개 모듈입니다: routes/billing → invoice → profile → plan → pricing → domain/plan → money.
- `billing/invoice`는 import 5개로 가장 많고, notify 모듈까지 끌고 옵니다.

**추론 (확인 안 됨):** `pricing`은 domain 모듈만 import합니다. 그래서 domain으로 옮기거나 users와 billing 사이의 공용 계층으로 빼면 패키지 간 상호 의존이 없어질 수 있습니다. 옮겨도 되는지는 실제 코드를 봐야 판단할 수 있습니다.

┗━━━━━━━━━━━━━━━━ 05A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 05B ━━━━━━━━━━━━━━━━┓

**모듈 단위로는 순환 import가 없고 위로 거슬러 올라가는 import도 없습니다. 다만 패키지 단위로 보면 `services/billing`과 `services/users`가 서로를 import합니다.**

```text
레이어 순서: 위 → 아래 (레이어 사이 import는 전부 아래 방향)
화살표는 같은 레이어 안의 import만 그림

entry    routes/users  routes/billing  routes/admin
         jobs/nightly_invoices  jobs/cleanup
           ↓
         api/deps
────────────────────────────────────────────────────
service  billing/invoice
           ↓  ✗ billing → users
         users/profile
           ↓
         users/plan
           ↓  ✗ users → billing
         billing/pricing

         billing/payment   users/auth   notify/email
                                          ↓
                                        notify/templates
────────────────────────────────────────────────────
domain   user     invoice   plan
                    ↓        ↓
                  money ←────┘
────────────────────────────────────────────────────
infra    db  redis  stripe_client  smtp
          ↓    ↓       ↓            ↓
         settings ←────┴────────────┘
────────────────────────────────────────────────────
common   errors   logging
```

- **패키지 순환:** `billing/invoice → users/profile → users/plan → billing/pricing` 경로 때문에 billing과 users가 서로를 import합니다. 모듈끼리는 순환이 없어서 지금 당장 import 오류는 나지 않습니다. 하지만 두 패키지를 분리하기는 어렵습니다.
- **분리 방법(제안):** `billing/pricing`은 `domain/plan`, `domain/money`만 import합니다. 그래서 이 모듈을 domain 쪽이나 별도의 `services/pricing`으로 옮기면 이 순환이 없어집니다.
- **범위:** 주신 25개 모듈의 정적 import 목록만 보고 그렸습니다. 함수 안에서 하는 import나 동적 import는 반영되지 않았습니다.

┗━━━━━━━━━━━━━━━━ 05B 끝 ━━━━━━━━━━━━━━┛

