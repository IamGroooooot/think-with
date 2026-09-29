---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out 머지 전 PR이야. 외부 API 호출 정책을 한곳으로 모았대. 뭐가 달라지는지 보여줘.

```diff
diff --git a/app/http/policy.py b/app/http/policy.py
new file mode 100644
--- /dev/null
+++ b/app/http/policy.py
@@ -0,0 +1,27 @@
+import httpx
+from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
+
+DEFAULT_TIMEOUT = 5.0
+MAX_ATTEMPTS = 3
+
+
+def _retryable(exc: BaseException) -> bool:
+    if isinstance(exc, httpx.TimeoutException):
+        return True
+    if isinstance(exc, httpx.HTTPStatusError):
+        return exc.response.status_code >= 500
+    return False
+
+
+class PolicyClient:
+    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT):
+        self._client = httpx.Client(base_url=base_url, timeout=timeout)
+
+    @retry(stop=stop_after_attempt(MAX_ATTEMPTS),
+           wait=wait_exponential(multiplier=0.5),
+           retry=retry_if_exception(_retryable),
+           reraise=True)
+    def request(self, method: str, path: str, **kw) -> httpx.Response:
+        resp = self._client.request(method, path, **kw)
+        resp.raise_for_status()
+        return resp
diff --git a/app/clients/geo.py b/app/clients/geo.py
--- a/app/clients/geo.py
+++ b/app/clients/geo.py
@@ -1,9 +1,8 @@
-import httpx
+from app.http.policy import PolicyClient
 from app.config import settings
 
-_client = httpx.Client(base_url=settings.GEO_URL, timeout=10)
+_client = PolicyClient(settings.GEO_URL)
 
 
 def lookup(ip: str) -> dict:
-    resp = _client.get(f"/ip/{ip}")
-    resp.raise_for_status()
-    return resp.json()
+    return _client.request("GET", f"/ip/{ip}").json()
diff --git a/app/clients/search.py b/app/clients/search.py
--- a/app/clients/search.py
+++ b/app/clients/search.py
@@ -1,9 +1,8 @@
-import httpx
+from app.http.policy import PolicyClient
 from app.config import settings
 
-_client = httpx.Client(base_url=settings.SEARCH_URL, timeout=2)
+_client = PolicyClient(settings.SEARCH_URL)
 
 
 def query(q: str) -> list:
-    resp = _client.get("/search", params={"q": q})
-    resp.raise_for_status()
-    return resp.json()["hits"]
+    return _client.request("GET", "/search", params={"q": q}).json()["hits"]
diff --git a/app/clients/email.py b/app/clients/email.py
--- a/app/clients/email.py
+++ b/app/clients/email.py
@@ -1,9 +1,8 @@
-import httpx
+from app.http.policy import PolicyClient
 from app.config import settings
 
-_client = httpx.Client(base_url=settings.MAIL_URL, timeout=30)
+_client = PolicyClient(settings.MAIL_URL, timeout=10)
 
 
 def send(to: str, template: str, data: dict) -> None:
-    resp = _client.post("/send", json={"to": to, "template": template, "data": data})
-    resp.raise_for_status()
+    _client.request("POST", "/send", json={"to": to, "template": template, "data": data})
diff --git a/app/clients/payments.py b/app/clients/payments.py
--- a/app/clients/payments.py
+++ b/app/clients/payments.py
@@ -1,10 +1,9 @@
-import httpx
+from app.http.policy import PolicyClient
 from app.config import settings
 
-_client = httpx.Client(base_url=settings.PAY_URL, timeout=20)
+_client = PolicyClient(settings.PAY_URL)
 
 
 def charge(customer_id: str, amount: int) -> str:
-    resp = _client.post("/charges", json={"customer": customer_id, "amount": amount})
-    resp.raise_for_status()
-    return resp.json()["id"]
+    resp = _client.request("POST", "/charges", json={"customer": customer_id, "amount": amount})
+    return resp.json()["id"]
```
