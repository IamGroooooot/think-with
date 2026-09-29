---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out 머지 전 PR이야. 인증 처리가 어떻게 바뀌는지 보여줘.

```diff
diff --git a/src/server.ts b/src/server.ts
@@ -1,14 +1,19 @@
 import express from "express";
+import { authenticate, requireRole } from "./middleware/auth";
 import { ordersRouter } from "./routes/orders";
 import { reportsRouter } from "./routes/reports";
 import { adminRouter } from "./routes/admin";
 import { healthRouter } from "./routes/health";

 const app = express();
 app.use(express.json());
 app.use("/health", healthRouter);
-app.use("/orders", ordersRouter);
-app.use("/reports", reportsRouter);
-app.use("/admin", adminRouter);
+app.use(authenticate);
+app.use("/orders", ordersRouter);
+app.use("/reports", reportsRouter);
+app.use("/admin", requireRole("admin"), adminRouter);
 export default app;
diff --git a/src/middleware/auth.ts b/src/middleware/auth.ts
new file mode 100644
@@ -0,0 +1,22 @@
+import type { Request, Response, NextFunction } from "express";
+import { verifySession } from "../lib/session";
+
+export async function authenticate(req: Request, res: Response, next: NextFunction) {
+  const user = await verifySession(req.cookies?.sid);
+  if (!user) return res.status(401).json({ error: "unauthenticated" });
+  req.user = user;
+  next();
+}
+
+export function requireRole(role: string) {
+  return (req: Request, res: Response, next: NextFunction) => {
+    if (req.user?.role !== role) return res.status(403).json({ error: "forbidden" });
+    next();
+  };
+}
diff --git a/src/routes/orders.ts b/src/routes/orders.ts
@@ -1,20 +1,14 @@
 import { Router } from "express";
-import { requireUser } from "../lib/requireUser";
 import * as orders from "../services/orders";

 export const ordersRouter = Router();

 ordersRouter.get("/", async (req, res) => {
-  const user = await requireUser(req, res);
-  if (!user) return;
-  res.json(await orders.list(user.id));
+  res.json(await orders.list(req.user.id));
 });

 ordersRouter.post("/", async (req, res) => {
-  const user = await requireUser(req, res);
-  if (!user) return;
-  res.status(201).json(await orders.create(user.id, req.body));
+  res.status(201).json(await orders.create(req.user.id, req.body));
 });
diff --git a/src/routes/reports.ts b/src/routes/reports.ts
@@ -1,16 +1,12 @@
 import { Router } from "express";
-import { requireUser } from "../lib/requireUser";
 import * as reports from "../services/reports";

 export const reportsRouter = Router();

 reportsRouter.get("/monthly", async (req, res) => {
-  const user = await requireUser(req, res);
-  if (!user) return;
-  res.json(await reports.monthly(user.id));
+  res.json(await reports.monthly(req.user.id));
 });

 reportsRouter.get("/export", async (req, res) => {
-  res.csv(await reports.exportAll());
+  res.csv(await reports.exportAll(req.user.id));
 });
diff --git a/src/routes/admin.ts b/src/routes/admin.ts
@@ -1,14 +1,10 @@
 import { Router } from "express";
-import { requireUser } from "../lib/requireUser";
 import * as admin from "../services/admin";

 export const adminRouter = Router();

 adminRouter.post("/refunds/:id", async (req, res) => {
-  const user = await requireUser(req, res);
-  if (!user) return;
-  if (user.role !== "admin") return res.status(403).end();
   res.json(await admin.refund(req.params.id));
 });
```
