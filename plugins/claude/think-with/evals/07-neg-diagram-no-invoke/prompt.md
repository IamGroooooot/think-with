---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill, Read]
runs: 3
---
아직 리뷰 중인 PR이야. 이 PR이 뭘 바꿨는지 다이어그램으로 보여줘.

```diff
diff --git a/app/cache.py b/app/cache.py
new file mode 100644
--- /dev/null
+++ b/app/cache.py
@@ -0,0 +1,20 @@
+import json
+from app.config import settings
+from app.infra.redis import get_redis
+
+
+def _key(user_id: int) -> str:
+    return f"user:{user_id}"
+
+
+def get_user(user_id: int):
+    raw = get_redis().get(_key(user_id))
+    return json.loads(raw) if raw else None
+
+
+def set_user(user_id: int, data: dict) -> None:
+    get_redis().setex(_key(user_id), settings.USER_CACHE_TTL_SECONDS, json.dumps(data))
+
+
+def invalidate_user(user_id: int) -> None:
+    get_redis().delete(_key(user_id))
diff --git a/app/config.py b/app/config.py
--- a/app/config.py
+++ b/app/config.py
@@ -8,6 +8,7 @@ class Settings(BaseSettings):
     DATABASE_URL: str
     REDIS_URL: str = "redis://localhost:6379/0"
     LOG_LEVEL: str = "INFO"
+    USER_CACHE_TTL_SECONDS: int = 300
 
 
 settings = Settings()
diff --git a/app/repo/users.py b/app/repo/users.py
--- a/app/repo/users.py
+++ b/app/repo/users.py
@@ -1,20 +1,31 @@
 from app.infra.db import session
 from app.domain.user import User
+from app import cache
 
 
 def find_user(user_id: int) -> dict | None:
+    cached = cache.get_user(user_id)
+    if cached is not None:
+        return cached
     row = session().get(User, user_id)
-    return row.to_dict() if row else None
+    if row is None:
+        return None
+    data = row.to_dict()
+    cache.set_user(user_id, data)
+    return data
 
 
 def update_user(user_id: int, fields: dict) -> dict:
     row = session().get(User, user_id)
     for k, v in fields.items():
         setattr(row, k, v)
     session().commit()
+    cache.invalidate_user(user_id)
     return row.to_dict()
 
 
 def delete_user(user_id: int) -> None:
     session().query(User).filter_by(id=user_id).delete()
     session().commit()
+    cache.invalidate_user(user_id)
diff --git a/app/handlers/users.py b/app/handlers/users.py
--- a/app/handlers/users.py
+++ b/app/handlers/users.py
@@ -1,6 +1,9 @@
+import logging
 from fastapi import APIRouter, HTTPException
 from app.repo import users as repo
 
+logger = logging.getLogger(__name__)
+
 router = APIRouter()
 
 
@@ -12,6 +15,7 @@ router = APIRouter()
 @router.get("/users/{user_id}")
 def get_user(user_id: int):
+    logger.debug("get_user", extra={"user_id": user_id})
     user = repo.find_user(user_id)
     if user is None:
         raise HTTPException(404)
     return user
diff --git a/tests/test_users_cache.py b/tests/test_users_cache.py
new file mode 100644
--- /dev/null
+++ b/tests/test_users_cache.py
@@ -0,0 +1,19 @@
+from app.repo import users as repo
+
+
+def test_find_user_populates_cache(fake_cache, db_user):
+    repo.find_user(42)
+    assert fake_cache.get("user:42") is not None
+
+
+def test_update_invalidates_cache(fake_cache, db_user):
+    repo.find_user(42)
+    repo.update_user(42, {"name": "Kim"})
+    assert fake_cache.get("user:42") is None
+
+
+def test_cache_hit_skips_db(fake_cache, db_user, db_spy):
+    repo.find_user(42)
+    repo.find_user(42)
+    assert db_spy.get_calls == 1
```
