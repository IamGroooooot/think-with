---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out 지난주에 머지된 변경이야. 회원가입 환영 메일 발송을 큐로 옮겼어. 무엇이 바뀌었는지 보여줘.

Before, `app/api/signup.py`:

```python
@router.post("/signup", status_code=201)
def signup(body: SignupIn):
    user = users.create(body.email, body.password)
    mailer.send_welcome(user.email)   # SMTP. 보통 1~3초, 가끔 10초 타임아웃
    return {"id": user.id}
```

After, `app/api/signup.py`:

```python
@router.post("/signup", status_code=201)
def signup(body: SignupIn):
    user = users.create(body.email, body.password)
    jobs.enqueue("send_welcome", user_id=user.id)   # Redis list에 push
    return {"id": user.id}
```

새 파일 `app/worker.py`:

```python
handlers = {"send_welcome": lambda user_id, **_: mailer.send_welcome(users.get(user_id).email)}

def run():
    while True:
        job = jobs.dequeue(block=True)
        try:
            handlers[job.name](**job.args)
        except SMTPError:
            if job.attempts < 3:
                jobs.enqueue(job.name, attempts=job.attempts + 1, **job.args)
            else:
                jobs.dead_letter(job)
```

`Procfile`에는 `worker: python -m app.worker` 한 줄이 추가됐어.
