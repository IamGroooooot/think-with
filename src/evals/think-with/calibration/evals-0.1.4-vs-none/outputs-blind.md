# 블라인드 출력: evals-0.1.4-vs-none

케이스마다 두 답변을 A와 B로 무작위로 배치했습니다. 하나는 플러그인을 설치한 상태의 답변이고, 다른 하나는 설치하지 않은 상태의 답변입니다. 플러그인이 없는 답변은 첫 줄에 '명령이 설치되어 있지 않다'고 써서 정체가 드러나므로 그 줄만 지웠습니다. 나머지 본문은 그대로입니다.

---

# 01 · 01-diff-add-cache
질문: 리뷰 중인 PR(Python 5개 파일, Redis 사용자 캐시 추가)이 뭘 바꿨는지 보여줘

┏━━━━━━━━━━━━━━━━ 01A ━━━━━━━━━━━━━━━━┓

아직 리뷰 중인 PR이라, 아래 내용은 **main에 반영된 게 아니라 제안된 변경**이에요. 주신 diff만 근거로 정리했고, 코드베이스는 확인하지 않았어요.

**파일 변경**

```text
app/
├─ + cache.py             신규: Redis get / setex / delete
├─ ~ config.py            + USER_CACHE_TTL_SECONDS = 300
├─ repo/
│  └─ ~ users.py          find: 캐시 조회 / update·delete: 무효화
└─ handlers/
   └─ ~ users.py          + logger.debug 추가 (응답은 그대로)
tests/
└─ + test_users_cache.py  테스트 3개
```

**읽기 경로: `find_user` 로직**

```diff
 find_user(id):
+  hit = redis.get("user:{id}")
+  if hit is not None: return hit      # DB 조회 생략
   row = db.get(User, id)
   if row is None: return None         # 없는 유저는 캐시 안 함
+  redis.setex("user:{id}", 300s, row.to_dict())
   return row.to_dict()
```

**데이터 흐름 (`+` = 이번 PR에서 추가)**

```text
Read, miss:
|| DB users || --row--> (find_user) --dict--> [GET /users/{id}]
                  + (find_user) --json, TTL 300s--> || Redis ||

Read, hit:
+ || Redis || --json--> (find_user) --dict--> [GET /users/{id}]

Write:
[caller] --fields--> (update_user) --commit--> || DB users ||
       + (update_user) --DEL user:{id}--> || Redis ||
[caller] --id--> (delete_user) --commit--> || DB users ||
       + (delete_user) --DEL user:{id}--> || Redis ||
```

**리뷰할 때 볼 것**
- **테스트가 다루는 것:** 캐시 채우기, `update` 후 무효화, 캐시 hit이면 DB 조회를 건너뛰는 것.
- **테스트가 없는 것:**
  - `delete_user` 후 무효화
  - TTL 값
  - `None`(없는 유저)을 캐시하지 않는 동작
- **추정 (검증 안 함):** 캐시는 DB commit 뒤에 지워요. 그래서 동시에 들어온 `find_user`가 옛 데이터를 읽고 삭제 뒤에 `setex`하면, 최대 300초 동안 옛 데이터가 남을 수 있어요.
- **확인 못 한 것:**
  - `fake_cache`, `db_user`, `db_spy` fixture는 diff에 없어서, 실제로 Redis를 대체하는지 알 수 없어요.
  - Redis 장애가 나면 어떻게 동작하는지는 diff만으로는 알 수 없어요. 예외 처리가 없는 것만 보여요.

┗━━━━━━━━━━━━━━━━ 01A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 01B ━━━━━━━━━━━━━━━━┓

## 요약

**사용자 조회에 Redis read-through 캐시를 추가한 PR입니다.** 조회할 때 캐시를 먼저 보고, 수정하거나 삭제하면 캐시를 지웁니다. TTL은 설정값이고 기본 300초입니다.

## 파일별 변경

| 파일 | 종류 | 내용 |
|---|---|---|
| `app/cache.py` | 신규 | `user:{id}` 키로 JSON을 저장·조회·삭제하는 `get_user` / `set_user` / `invalidate_user` 함수 |
| `app/config.py` | 수정 | 설정 `USER_CACHE_TTL_SECONDS: int = 300` 추가 |
| `app/repo/users.py` | 수정 | 핵심 로직 변경 (아래 참고) |
| `app/handlers/users.py` | 수정 | `GET /users/{id}`에 debug 로그 한 줄 추가 (캐시와는 관계없음) |
| `tests/test_users_cache.py` | 신규 | 캐시 동작 테스트 3개 |

## 동작 흐름

```
find_user(id)
  ├─ 캐시 hit → 캐시 값 반환 (DB 조회 안 함)
  └─ 캐시 miss → DB 조회
        ├─ 없음 → None (캐시에 저장 안 함)
        └─ 있음 → to_dict() → 캐시에 저장(TTL) → 반환

update_user(id, fields) → DB commit → 캐시 삭제
delete_user(id)         → DB commit → 캐시 삭제
```

## 테스트가 검증하는 것

- 조회하면 캐시가 채워진다
- 수정하면 캐시가 지워진다
- 두 번째 조회는 DB를 다시 부르지 않는다 (`db_spy.get_calls == 1`)

## 리뷰할 때 볼 만한 점

1. **짧은 시간 동안 옛날 데이터가 캐시에 남을 수 있음.** 순서가 이렇게 겹치면 생깁니다: 읽는 요청이 commit 전의 DB 값을 가져옴 → 수정 요청이 commit하고 캐시를 지움 → 읽는 요청이 그 옛날 값을 캐시에 씀. 이러면 최대 TTL(300초) 동안 옛날 데이터가 반환됩니다. 이 정도를 허용할 수 있는지 판단이 필요합니다.
2. **없는 사용자는 캐시하지 않음.** 존재하지 않는 id로 반복 요청이 오면 매번 DB까지 갑니다. 의도한 거라면 괜찮습니다.
3. **Redis 장애 처리 없음.** `get_redis()` 호출이 실패하면 DB로 넘어가지 않고 요청 자체가 에러가 납니다. 캐시가 선택 기능이 아니라 필수 의존성이 된 셈입니다.
4. **테스트가 빠진 부분:** 삭제 시 캐시 삭제, 없는 사용자 조회, 캐시 hit일 때 반환값이 DB 값과 같은지.
5. **캐시 hit과 miss의 반환값이 미세하게 다를 수 있음.** hit이면 JSON을 거친 dict가 반환됩니다. `to_dict()`에 datetime 같은 값이 있으면 저장할 때 `json.dumps`가 실패하거나, 복원했을 때 타입이 miss 경우와 달라질 수 있습니다.
6. 핸들러에 추가된 debug 로그는 캐시와 관계없는 변경입니다. 이 PR에 같이 넣을지 따로 뺄지 정하면 됩니다.

┗━━━━━━━━━━━━━━━━ 01B 끝 ━━━━━━━━━━━━━━┛

---

# 02 · 02-diff-sync-to-queue
질문: 머지된 변경(가입 환영 메일을 동기 발송에서 큐+워커로)이 뭘 바꿨는지 보여줘

┏━━━━━━━━━━━━━━━━ 02A ━━━━━━━━━━━━━━━━┓

# 회원가입 환영 메일을 큐로 옮긴 변경

## 한 줄 요약
가입 요청 안에서 SMTP로 바로 보내던 환영 메일을 **Redis 큐에 넣고, 별도 워커 프로세스가 꺼내서 보내는** 구조로 바꿨어요. 가입 응답은 빨라지고 메일 실패가 가입에 영향을 주지 않아요. 대신 메일 발송은 비동기가 되고, 코드에 드러나지 않는 실패 경로가 몇 개 새로 생겼어요.

## 흐름 비교

| | Before | After |
|---|---|---|
| 요청 경로 | `users.create` → SMTP 발송(1~3초, 최악 10초) → 201 | `users.create` → Redis push(수 ms) → 201 |
| 메일 발송 시점 | 응답 전, 동기 | 응답 후 워커가 처리 |
| SMTP 실패 시 | 예외 → **500 응답인데 유저는 이미 생성됨** (재가입하면 이메일 중복 에러가 날 가능성) | 가입은 201. 워커가 재시도하고, 계속 실패하면 dead letter로 보냄 |
| 새 의존성 | SMTP | Redis(요청 경로), SMTP(워커 경로), 워커 프로세스 |
| 배포 단위 | web | web + `worker` (Procfile) |

## 좋아진 점
- **가입 지연 제거**: p99에서 최대 10초까지 걸리던 SMTP 대기가 요청 경로에서 빠졌어요.
- **부분 실패 해소**: 예전에는 "유저는 만들어졌는데 클라이언트는 500을 받는" 상태가 생길 수 있었는데, 이제 없어요.
- **재시도와 dead letter**: 일시적인 SMTP 오류는 자동으로 다시 시도해요.

## 확인이 필요한 점 (중요한 순서)

**1. `attempts`가 실제로 증가하는지 확인해야 해요. 안 되면 무한 재시도예요.**
```python
jobs.enqueue(job.name, attempts=job.attempts + 1, **job.args)
```
가입 코드에서는 `enqueue("send_welcome", user_id=...)`처럼 키워드 인자가 전부 `args`로 들어가요. 그러면 `attempts=`도 `job.args`에 섞이고 `job.attempts`는 계속 초기값에 머물 수 있어요. 핸들러 람다에 `**_`가 붙어 있는 것도 `attempts`가 args로 넘어오는 걸 삼키려고 넣은 흔적처럼 보여요. `jobs.enqueue`가 `attempts`를 따로 꺼내서 처리하는지 확인해야 해요. 제대로 처리하더라도 초기값이 0이면 최대 4번, 1이면 최대 3번 보내요.

**2. `SMTPError`가 아닌 예외가 나면 워커가 죽고 잡이 사라져요.**
- SMTP 연결 타임아웃은 보통 `socket.timeout`/`TimeoutError`, `ConnectionRefusedError` 같은 예외로 올라와요. 이것들은 `SMTPError`의 하위 클래스가 아니라서 except에 안 걸려요. 기존 주석에 적힌 "가끔 10초 타임아웃"이 바로 이 경우예요.
- `users.get(user_id)`가 `None`을 돌려주면 `AttributeError`, 등록되지 않은 잡 이름이면 `KeyError`가 나요.
- 이런 예외는 `run()` 밖으로 빠져나가서 **프로세스가 종료**돼요. 잡은 이미 dequeue(pop)된 상태라 **유실**되고, dead letter에도 남지 않아요.

**3. 전달 보장이 at-most-once에 가까워요.**
pop한 뒤 발송 도중에 워커가 죽거나, 배포 때 SIGTERM을 받으면 그 메일은 사라져요. 반대로 SMTP가 실제로는 보냈는데 이후 단계에서 `SMTPError`가 나면 재시도 때문에 **중복 발송**될 수도 있어요.

**4. 재시도에 백오프가 없어요.**
실패하면 바로 큐 뒤에 다시 넣기 때문에, SMTP가 잠깐 다운되면 3번의 재시도가 몇 초 안에 다 소진되고 dead letter로 넘어가요.

**5. 트랜잭션 커밋 전에 워커가 읽을 수 있어요.**
`users.create`가 요청 단위 트랜잭션 안에서 실행되고 커밋이 응답 시점에 일어난다면, 워커가 먼저 `users.get`을 호출해서 유저를 못 찾을 수 있어요. 이 경우 2번의 `AttributeError`로 이어져요. 세션 구성에 따라 문제가 안 될 수도 있어요.

**6. 가입이 Redis에 의존하게 됐어요.**
Redis가 다운되면 `enqueue`가 실패해서, 예전 SMTP 실패 때와 같은 "유저는 생성됐는데 500" 상태가 다시 생겨요.

**7. 처리량은 워커 하나가 순차로 처리하는 수준이에요.**
메일당 1~3초, 타임아웃이면 10초가 걸리니까, 가입이 몰리면 큐가 쌓이고 환영 메일이 몇 분씩 늦어질 수 있어요.

**8. 워커가 실제로 떠 있는지 먼저 확인하세요.**
Heroku 계열 플랫폼에서는 Procfile에 새로 추가한 프로세스 타입이 기본적으로 **0개로 스케일**돼요. 머지된 지 일주일 됐으니, `worker`가 돌고 있는지와 Redis 리스트 길이, dead letter 개수부터 보는 걸 추천해요. 워커가 안 떠 있었다면 지난주부터 환영 메일이 전혀 나가지 않았을 거예요.

## 제안하는 후속 조치 (작은 것부터)
1. 워커 가동 여부와 큐 길이를 확인하고 모니터링을 붙이기
2. `except SMTPError`를 `except Exception`으로 넓히고, 재시도할 오류와 바로 dead letter로 보낼 오류를 구분하기. 적어도 워커가 죽지는 않게 하기
3. `attempts` 처리 확인하고 테스트 추가하기
4. 재시도에 지연(백오프) 넣기
5. 필요하면 pop 대신 `BLMOVE`로 processing 리스트에 옮기는 패턴을 써서 유실 막기

`jobs` 모듈 코드를 보여주시면 1번과 5번은 추측이 아니라 확실하게 답해드릴 수 있어요.

┗━━━━━━━━━━━━━━━━ 02A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 02B ━━━━━━━━━━━━━━━━┓

**파일 변경** (머지된 상태, 붙여주신 코드 기준이고 저장소에서는 확인하지 않았어)

```text
 app/
M  api/signup.py   SMTP 동기 호출 → 큐에 enqueue
A  worker.py       소비 루프 + SMTPError 재시도
M Procfile         + worker: python -m app.worker
```

```diff
 user = users.create(body.email, body.password)
-mailer.send_welcome(user.email)
+jobs.enqueue("send_welcome", user_id=user.id)
 return {"id": user.id}
```

**요청 흐름** (정상 경로)

```diff
 Client     API       DB      Redis     Worker    SMTP
   |         |        |         |         |         |
   |--POST-->|        |         |         |         |
   |         |-create>|         |         |         |
-  |         |------ send_welcome (SMTP) ---------->|
-  |         |<-------- wait 1~3s (timeout 10s) ----|
-  |<--201---|        |         |         |         |
+  |         |---- enqueue ---->|         |         |
+  |<--201---|        |         |         |         |
+  |         |        |         |-dequeue>|         |
+  |         |        |<---- users.get ---|         |
+  |         |        |         |         |--send-->|
```

- 이제 201은 메일을 보내기 전에 나가. 응답이 SMTP를 기다리지 않아.
- 이메일 주소는 가입 시점이 아니라 **발송 시점**에 DB에서 다시 읽어.
- 가입 경로가 새로 Redis에 의존해. `enqueue`가 실패하면 유저는 이미 만들어진 상태에서 예외가 나. 이전 코드에서 SMTP가 실패했을 때도 같은 모양이었어. 둘 다 처리 코드가 없고, 응답 코드는 프레임워크 기본값을 따를 거라고 추론만 한 거야.

**워커의 job 처리** (전부 신규)

| 상황 | 결과 |
|---|---|
| 핸들러 성공 | 끝 |
| `SMTPError`, `attempts < 3` | 즉시 재enqueue, `attempts+1`, backoff 없음 |
| `SMTPError`, `attempts ≥ 3` | `dead_letter` |
| 그 외 예외 | 잡히지 않음 → `run()` 탈출 → 워커 종료 |

"그 외 예외"의 예로는 `users.get`이 `None`을 돌려주는 경우, 모르는 `job.name`, Redis 오류가 있어.

**코드만으로는 알 수 없는 부분**

- **`__main__` 진입점:** `worker.py`에 `if __name__ == "__main__": run()`이 안 보여. 이게 없으면 `python -m app.worker`는 정의만 하고 바로 끝나.
- **`attempts` 초기값:** 0인지 1인지에 따라 총 시도 횟수가 3회 또는 4회가 돼.
- **`attempts`가 저장되는 위치:** 별도 메타데이터가 아니라 `job.args`에 들어간다면, 두 번째 재시도에서 `enqueue(..., attempts=..., **job.args)`가 `attempts`를 중복으로 넘겨 `TypeError`가 나고 워커가 죽어. 핸들러에 있는 `**_`를 보면 `attempts`가 args에 섞여 들어가는 것 같은데, 이건 추론이야.
- **`dequeue`가 pop인지:** 처리 전에 꺼내 지우는 방식이면, 워커가 처리 중에 죽을 때 그 job은 사라져.
- **워커가 죽은 뒤 재시작:** Procfile을 실행하는 플랫폼 설정에 달려 있어.

┗━━━━━━━━━━━━━━━━ 02B 끝 ━━━━━━━━━━━━━━┛

---

# 04 · 04-concept-lock-compare
질문: 3개 인스턴스 리더 선출: Redis SET NX PX / PG advisory lock / etcd lease 비교 (영어)

┏━━━━━━━━━━━━━━━━ 04A ━━━━━━━━━━━━━━━━┓

## Summary

None of the three options can guarantee a single fire on its own. Each one is a lease, and any lease can end while the old holder still thinks it's the leader. This happens after a GC pause, a network partition, or a slow network call made after the last renewal check. Because a double fire sends duplicate invoices, you need a dedupe check where the invoice is actually written. Once you have that, the choice of election mechanism matters much less.

## Comparison

| | Redis `SET NX PX` + renewal | Postgres `pg_try_advisory_lock` (session) | etcd lease + `concurrency.Election` |
|---|---|---|---|
| **What ends leadership** | TTL expires (30s) unless renewed | The DB session ends (connection closed, or the server finds the client dead) | Lease TTL expires unless kept alive |
| **Consistency of the lock store** | Async replication. On failover, a replica can be promoted without the key, giving two leaders | Single primary. Advisory locks aren't replicated, so all locks disappear on failover (old sessions die too) | Raft consensus: the most reliable way to know who holds the lock |
| **When can two instances both think they lead?** | Pause longer than the remaining TTL; replica promoted without the key; renewal done as a plain `SET` instead of an atomic check-and-extend (Lua) | Client partitioned from the DB while its process keeps running. The server drops the session after keepalive or `tcp_user_timeout`, another instance takes the lock, and the old one doesn't find out until its next query | Pause longer than the remaining TTL. The old leader keeps acting until its keepalive fails |
| **Fencing token** | None built in (you could add `INCR`) | None built in | Yes: the leader key's revision increases each time leadership changes |
| **Can the token actually be enforced?** | Only if you build a check | Partly for free: if invoice writes go through the **same connection** that holds the lock, a dead session can't write. This breaks if jobs use a separate pool | Only if the invoice writer checks the revision. An external invoice/email provider won't |
| **Common mistakes** | Unsafe renewal or release (must compare the value before extending or deleting); Redlock's known problems | **PgBouncer in transaction mode silently breaks session locks**; the lock connection must not be recycled by the pool; tune keepalives | Leader must stop work immediately when `Observe`/session `Done()` fires; clock and pause assumptions |
| **Ops cost for you** | None (already running) | None (already running) | New 3-node cluster to run, monitor, back up and upgrade |
| **Failure-detection latency** | ≈ TTL | Keepalive or `tcp_user_timeout` settings (can be seconds or minutes if left at defaults) | ≈ lease TTL |

## What this means for you

1. **etcd only helps if the invoice write checks its fencing token.** Otherwise you'd run a whole new cluster to get the same "usually one leader" result. It isn't worth adding etcd just for this.
2. **Postgres fits best, because invoices probably live in Postgres already.** That lets you put the real guarantee in the database:
   ```sql
   -- inside the same transaction that creates the invoice rows
   INSERT INTO job_runs (job_name, scheduled_for, claimed_by)
   VALUES ($1, $2, $3)
   ON CONFLICT (job_name, scheduled_for) DO NOTHING
   RETURNING 1;   -- no row returned → someone else already ran it; abort
   ```
   With this unique claim, a double leader can't create duplicate invoices. You could even drop leader election and let all 3 instances race for the claim row. Keeping the advisory lock is still reasonable as a cheap way to avoid wasted work.
3. **The external send is still exposed.** If the invoice is emailed or pushed to a billing provider, a crash between "committed" and "sent" forces a choice: retry and risk a duplicate, or skip and risk a missed send. Close that gap with an outbox table plus the provider's idempotency key. Use a key derived from `(job_name, scheduled_for)`; Stripe and most billing APIs support this.
4. **Redis is the weakest fit.** The failover and TTL-pause cases are real, and dedupe doesn't fit naturally in Redis the way it does in the table that holds the invoices.

## Recommendation

Use a Postgres advisory lock on a dedicated, non-pooled connection, with `tcp_user_timeout` and keepalives tuned, so only one instance normally runs jobs. Rely on the `job_runs` unique constraint plus provider idempotency keys to guarantee no double fire. Skip etcd unless you need it for something else.

┗━━━━━━━━━━━━━━━━ 04A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 04B ━━━━━━━━━━━━━━━━┓

**File changes:** none. This is a design comparison, and no code or diff was provided.

**Bottom line:** none of the three options can guarantee exactly one fire by itself. With each of them, a leader can pause (GC, network partition) past its lease and then fire again after someone else has taken over. The real guarantee has to come from a dedupe check where the invoice is created.

### 1. How the options compare

| | Redis `SET NX PX` | PG advisory lock | etcd Election |
|---|---|---|---|
| New infra | none | none | a 3-node cluster to run |
| Leader loses the role when | renewal misses the TTL | its session/connection dies | lease TTL runs out |
| If the store fails over | async replica can lose the key → 2 leaders | locks aren't replicated; old connection errors out | Raft keeps it linearizable |
| Paused old leader | may fire after its TTL expired | server keeps the lock while the TCP connection lives | may fire after its lease expired |
| When the leader learns it lost | at the next renew | only at its next query or TCP keepalive | when the keepalive channel closes |
| Fencing token | none (build one with `INCR`) | none | yes (revision of the leader key) |
| Gotchas | renewal must be a compare-and-extend Lua script; Redlock's safety is disputed | breaks under PgBouncer transaction pooling; tune keepalives | adds a new failure domain to operate |
| Double fire still possible? | yes | yes, in a narrower window | yes, unless the invoice path checks the revision |

The advisory lock's weak spot is the opposite of Redis's. A partitioned client can hold the lock for minutes, so fires get missed. A client whose session was killed may not notice until its next query, so fires can double up.

### 2. The failure all three share, and the fix

```text
  App A          Lock            App B         PG
   |               |               |              |
   |-- acquire --->|               |              |
   |<----- ok -----|               |              |
   :  pause > TTL  |               |              |
   :               | lease expires |              |
   :               |<-- acquire ---|              |
   :               |------ ok ---->|              |
   :               |               |-- claim 9:00>|
   :               |               |<---- ok -----|
   :               |               |* send invoice|
   |-- claim 9:00 ------------------------------->|
   |<-------------------------- dup: slot taken --|
   * skip send (no second invoice)
```

"Claim" is an `INSERT` into `job_runs` with `UNIQUE (job_id, slot)`, committed before the invoice is sent. Leader election then only affects efficiency, not correctness.

### Recommendation

- **Use the Postgres advisory lock plus the run-slot claim.** It needs no new infrastructure. Connect directly (not through PgBouncer) and set TCP keepalives.
- **Skip etcd for this.** Its fencing token only protects writes to etcd itself. To stop duplicate invoices, the invoice path would still have to check the token, and the slot claim already does that.
- **Only use Redis with the slot claim.** It is the weakest of the three when the store fails over.
- **Trade-off:** claiming before sending means at most one invoice per slot. If the process crashes between the claim and the send, that invoice is missed. You need a check that finds claimed slots with no invoice sent.

**Open questions:**
- Do invoices live in the same Postgres as the scheduler? If so, the claim and the invoice row can go in one transaction.
- Does the invoice or payment provider accept an idempotency key? If so, pass it `job_id:slot`.

┗━━━━━━━━━━━━━━━━ 04B 끝 ━━━━━━━━━━━━━━┛

---

# 05 · 05-deps-cycle
질문: 25개 모듈 import 목록의 의존 구조를 보여줘 (패키지 수준 순환 있음)

┏━━━━━━━━━━━━━━━━ 05A ━━━━━━━━━━━━━━━━┓

**파일 변경:** 해당 없음. 비교할 이전 버전이 없어서 현재 구조만 보여 줍니다.

**1. 계층 개요:** 아래 계층이 위 계층을 import하는 역방향 의존은 없습니다.

| 계층 | 모듈 | import 대상 계층 |
|---|---|---|
| 진입점 | `api/routes/{users,billing,admin}` | api, services |
| 진입점 | `jobs/{nightly_invoices,cleanup}` | services, infra, common |
| api | `deps` | services, infra |
| services | `users/*`, `billing/*`, `notify/*` | services, domain, infra, common |
| domain | `user`, `invoice`, `plan`, `money` | domain, common |
| infra | `db`, `redis`, `stripe_client`, `smtp`, `settings` | infra, common |
| common | `errors`, `logging` | 없음 |

import가 가장 많이 몰리는 곳은 `infra/settings.py`와 `infra/db.py`로, 각각 6개 모듈이 import합니다.

**2. services 내부 의존:** 구조가 얽히는 곳은 여기뿐입니다.

```
 billing/invoice ──▶ users/profile ──▶ users/plan
    │     │                                │
    │     └──────────▶ billing/pricing ◀───┘
    ▼
 notify/email ──▶ notify/templates
```

- **모듈 단위 순환은 없습니다.** 25개 모듈 모두 확인했습니다.
- **패키지 단위로는 순환이 있습니다(목록에서 추론한 결과):**
  - `billing/invoice`가 `users/profile`을 import합니다 (billing → users).
  - `users/plan`이 `billing/pricing`을 import합니다 (users → billing).
  
  그래서 `services/users`와 `services/billing`이 서로 의존합니다.
- **`billing/invoice`의 영향 범위가 가장 큽니다.** 이 모듈 하나가 간접적으로 14개 모듈을 끌어옵니다. `routes/billing`, `routes/admin`, `jobs/nightly_invoices` 세 곳이 이 모듈을 import합니다.

┗━━━━━━━━━━━━━━━━ 05A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 05B ━━━━━━━━━━━━━━━━┓

## 1. 레이어 배치

각 모듈을 "가장 긴 import 경로의 깊이" 기준으로 배치했어요. 모든 import는 위에서 아래 방향으로만 흘러요.

```
L6  api/routes/billing   api/routes/admin   jobs/nightly_invoices
          │                    │                    │
L5  api/routes/users      services/billing/invoice ◄┘
          │                    │
L4        │               services/users/profile
          │                    │
L3  api/deps              services/users/plan
          │                    │
L2  services/users/auth   services/billing/pricing   services/billing/payment
    services/notify/email jobs/cleanup
          │
L1  domain/user   domain/invoice   domain/plan
    infra/db   infra/redis   infra/stripe_client   infra/smtp
    services/notify/templates
          │
L0  domain/money   infra/settings   common/logging   common/errors
```

## 2. 패키지 단위로 묶어 보기

```
            api/routes ──► api/deps
             │    │           │
             ▼    ▼           ▼
   ┌──► services/billing ◄──► services/users ◄─┐
   │         │    │                │           │
jobs         │    ▼                │         (deps)
   │         │  services/notify    │
   │         ▼        │            ▼
   └──────►  infra ◄──┘         domain
               │                   │
               └──► common ◄───────┘
```

## 3. 눈에 띄는 점

**① `services/users`와 `services/billing`이 패키지 단위로 서로를 import해요** (모듈 단위 순환은 없음)
- `users/plan → billing/pricing`
- `billing/invoice → users/profile`
- 지금은 괜찮지만, 누가 `profile`에서 `invoice`를 import하는 순간 진짜 순환 import가 생겨요.
- `plan`은 사실상 과금 개념이에요. `services/billing/plan.py`로 옮기거나 `pricing`을 `domain` 쪽으로 내리면 이 방향이 하나로 정리돼요.

**② 의존 경로가 가장 긴 체인 (깊이 6)**
```
api/routes/admin → billing/invoice → users/profile → users/plan
               → billing/pricing → domain/plan → domain/money
```
`pricing`이나 `plan`을 바꾸면 invoice, profile, 모든 라우트, 야간 잡까지 영향을 받아요.

**③ `services/billing/invoice`가 가장 무거운 모듈이에요**
- import가 5개이고, users, billing, notify, infra, domain 다섯 영역에 걸쳐 있어요.
- import하는 쪽도 3개예요 (billing 라우트, admin 라우트, 야간 잡).
- 이메일 발송(`notify/email`)을 이벤트나 콜백으로 분리하면 결합도가 꽤 줄어들어요.

**④ 많이 import되는 모듈 (fan-in)**

| 모듈 | 이 모듈을 import하는 모듈 수 |
|---|---|
| `infra/db`, `infra/settings` | 6 |
| `profile`, `billing/invoice`, `api/deps`, `common/errors`, `common/logging`, `domain/money` | 3 |

**⑤ 잘 지켜진 점**
- `domain`은 `domain`과 `common`만 import해요. 순수 레이어가 잘 유지되고 있어요.
- `infra`는 `settings`와 `logging`에만 의존해요.
- 아래 레이어가 위 레이어를 import하는 경우는 없어요.

모듈 25개와 엣지 전체를 담은 Mermaid 그래프가 필요하면 말씀해 주세요. 문서나 PR에 바로 붙일 수 있게 만들어 드릴게요.

┗━━━━━━━━━━━━━━━━ 05B 끝 ━━━━━━━━━━━━━━┛

---

# 06 · 06-mixed-intents
질문: 아키텍처·데이터 흐름·배포·에러 처리·이번 PR(rate limit 미들웨어)을 한꺼번에 보여줘

┏━━━━━━━━━━━━━━━━ 06A ━━━━━━━━━━━━━━━━┓

**상태:** 설명으로만 받은 제안 변경입니다. 이 repo에는 `app/` 코드가 없어서 적용 여부는 확인하지 못했습니다.

**파일 변경**
```diff
  app/
  ├── main.py            ~ auth 다음, router 앞에 RateLimit 등록
  ├── middleware/
+ │   └── ratelimit.py   + Redis token bucket, 초과 시 429
  └── ?settings          ~ RATE_LIMIT_PER_SEC 추가 (파일 경로 미제공)
```

**데이터 흐름과 에러 경로 (DFD)**
```diff
  [Client] --HTTPS--> (nginx ingress) --req--> (API x3)
  (API x3) --rows--> || Postgres (RDS) ||
  (API x3) --session/cache--> || Redis ||
+ (API x3) --bucket per API key--> || Redis ||
  (API x3) --task--> || Redis broker || --> (Celery x2)
  (Celery x2) --report/mail--> ? (대상 미제공)
  (API x3) --exception--> (exc handler) --JSON--> [Client]
  (exc handler) --event--> [Sentry]
  (Celery x2) --3회 재시도 후 실패--> [Sentry]
```
- 알 수 없음: broker와 session/cache/rate-limit가 같은 Redis 인스턴스인지 정보가 없습니다. 같은 인스턴스라면 이번 PR로 Redis 부하가 늘어납니다(추론).

**요청 경로 (sequence)**
```diff
   Client  Ingress  Auth    RLimit  Router  Redis
     |        |       |       |       |       |
     |--req-->|       |       |       |       |
     |        |-req-->|       |       |       |
+    |        |       |-key-->|       |       |
+    |        |       |       |--take token-->|
+    |        |       |       |<--ok / empty--|
+  alt ok
+    |        |       |       |-req-->|       |
     |<------------ 200 --------------|       |
+  alt empty
+    |<------ 429 (empty) ----|       |       |
```

**배포 (trace, PR로 바뀌는 단계 없음)**
```text
[GH Actions] build --> push ECR --> [Argo CD] sync --> k8s
```
- 알 수 없음: `RATE_LIMIT_PER_SEC`를 k8s manifest나 ConfigMap에 넣는 변경이 PR에 있는지 정보가 없습니다.

**리뷰 때 확인할 점**
- **등록 순서:** Starlette `add_middleware`는 마지막에 등록한 것이 먼저 실행됩니다. auth 다음에 rate limit이 실행되게 하려면 코드에서는 ratelimit을 auth보다 **먼저** `add_middleware` 해야 합니다.
- **replica 간 공유:** bucket이 공유 Redis에 있으므로 제한은 replica마다가 아니라 전체 합산으로 API 키당 20/s입니다. 설명대로라면 의도에 맞습니다.
- **인증 실패 요청:** 인증에 실패한 요청은 auth에서 먼저 끊기기 때문에 이 limiter에 도달하지 않습니다(추론).
- **429 응답 형식:** middleware가 응답을 직접 반환하면 exception handler를 거치지 않습니다. 그러면 다른 에러와 JSON 형식이 다를 수 있고 Sentry에도 가지 않습니다. 어떻게 구현했는지는 정보가 없습니다.
- **Redis 장애 시 동작:** Redis가 죽었을 때 요청을 통과시킬지(fail-open) 막을지(fail-closed) 정보가 없습니다.

┗━━━━━━━━━━━━━━━━ 06A 끝 ━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━ 06B ━━━━━━━━━━━━━━━━┓

## 전체 구조 (★ = 이번 PR 변경)

```
 ┌──────────────────────────── 배포 파이프라인 ─────────────────────────────┐
 │  git push → GitHub Actions ─(이미지 빌드)→ ECR push → Argo CD sync ─┐        │
 └────────────────────────────────────────────────────────────┼────────┘
                                                                  ▼ (API, Worker 이미지 롤아웃)
 ┌──────────────────────────────── k8s 클러스터 ──────────────────────────────────┐
 │                                                                                  │
 │  Client ──HTTPS──▶ nginx ingress                                                 │
 │                        │                                                         │
 │                        ▼                                                         │
 │   ┌──────── FastAPI API × 3 replica ───────────────────┐                         │
 │   │  요청 ─▶ [인증 MW] ─▶ ★[RateLimit MW] ─▶ [Router]    │                         │
 │   │                          │  초과 시 429              │                         │
 │   │                          │  (API 키당 RATE_LIMIT_    │                         │
 │   │                          │   PER_SEC=20/s)          │                         │
 │   │  Exception handler ──▶ JSON 에러 응답 + Sentry        │                         │
 │   └──────┬─────────────┬──────────────┬─────────────────┘                         │
 │          │ SQL         │ 세션/캐시     │ ★ token bucket    │ 작업 enqueue          │
 │          ▼             ▼              ▼                   ▼                      │
 │   ┌───────────┐   ┌──────────────────── Redis ────────────────────┐              │
 │   │ Postgres  │   │  세션 · 캐시 · ★ratelimit 키 · Celery broker    │              │
 │   │  (RDS)    │   └───────────────────────────┬───────────────────┘              │
 │   └─────▲─────┘                               │ 작업 수신                          │
 │         │                                     ▼                                  │
 │         │            ┌──── Celery worker × 2 replica ────┐                       │
 │         └────────────│  리포트 생성 · 메일 발송              │                       │
 │                      │  실패 → 재시도 ×3 → Sentry           │                       │
 │                      └────────────────────────────────────┘                       │
 └──────────────────────────────────────────────────────────────────────────────────┘
                                  Sentry  ◀── API 예외 / Celery 최종 실패
```

## 데이터 흐름

| 경로 | 흐름 |
|---|---|
| 동기 요청 | Client → ingress → 인증 → ★rate limit → router → Postgres / Redis 캐시 → JSON 응답 |
| 비동기 작업 | router → Redis broker에 enqueue → worker가 처리 → Postgres 기록 또는 메일 발송 |
| 세션 | API ↔ Redis. replica 사이에 상태를 공유하므로 3개 replica 모두 stateless |
| ★ 제한 카운터 | 요청마다 Redis의 API 키별 token bucket을 차감. 3개 replica가 같은 bucket을 쓰므로 클러스터 전체 기준으로 20/s |

## 에러 처리

| 발생 위치 | 처리 |
|---|---|
| 라우터 / 비즈니스 로직 | exception handler가 JSON 에러로 변환하고 Sentry로 보냄 |
| Celery 작업 | 3번 재시도한 뒤 Sentry로 보냄 |
| ★ Rate limit 초과 | middleware가 **직접** 429를 반환 (아래 2번 참고) |

## 이번 PR에서 확인할 점

1. **middleware 등록 순서가 반대로 동작할 수 있음.** Starlette에서는 `add_middleware`를 **나중에 호출한 것이 바깥쪽(먼저 실행)**이 됩니다. "인증 뒤, 라우터 앞"에서 실행하려면 코드에서는 rate limit을 인증보다 **먼저** `add_middleware` 해야 합니다. 인증 바로 다음 줄에 추가하면 rate limit이 인증보다 먼저 실행되고, 이때는 아직 API 키를 알 수 없습니다.
2. **429가 기존 JSON 에러 형식과 다를 수 있음.** middleware 안에서 raise한 `HTTPException`은 FastAPI exception handler까지 가지 않습니다. 그래서 `JSONResponse`를 기존 에러 스키마에 맞춰 직접 만들어야 합니다. `Retry-After` 헤더도 함께 넣는 것을 권장합니다. 또 429를 Sentry로 보내지 않는지 확인이 필요합니다. 보내면 노이즈가 폭증합니다.
3. **원자성.** token bucket의 조회·차감이 GET/SET으로 나뉘어 있으면 replica 3개가 동시에 처리할 때 race가 생깁니다. Lua 스크립트나 `EVALSHA` 하나로 처리해야 합니다. key에 TTL도 설정해야 합니다.
4. **Redis 장애 시 동작.** 이제 Redis 하나가 세션, 캐시, broker, rate limit을 모두 맡습니다. Redis 오류가 날 때 fail-open(통과)할지 fail-closed(차단)할지 정하고, 타임아웃을 짧게 둬야 합니다. 그렇지 않으면 Redis 지연이 모든 API 지연으로 이어집니다.
5. **ingress와의 관계.** nginx ingress에 이미 `limit-rps` 같은 annotation이 있으면 제한이 이중으로 걸리므로 겹치는지 확인이 필요합니다. 또 인증 전 단계의 IP 기반 남용은 이번 PR로 막을 수 없으니, 필요하다면 ingress에서 막아야 합니다.
6. **설정 배포.** `RATE_LIMIT_PER_SEC`를 Helm values나 ConfigMap에도 추가해야 Argo CD sync로 반영됩니다. 코드 기본값을 20으로 둘지도 정해야 합니다.
7. **Celery 영향 없음.** worker는 HTTP 경로를 거치지 않으므로 이번 PR의 영향을 받지 않습니다.

원하시면 실제 `app/main.py`와 `ratelimit.py`를 열어서 1~4번이 코드에서 어떻게 되어 있는지 확인하겠습니다.

┗━━━━━━━━━━━━━━━━ 06B 끝 ━━━━━━━━━━━━━━┛
