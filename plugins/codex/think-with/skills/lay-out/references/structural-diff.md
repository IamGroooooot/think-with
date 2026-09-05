# Structural diff

Use this for changed branches or connectors that need realignment. Keep the unchanged spine visible; the marker column is outside the diagram. A simple file summary or code patch needs no extra diagram convention.

File layout:

```diff
 src/
 ├─ commands/
+│  └─ show-me.ts       # expands the command
 ├─ sessions/
-└─ transport.ts
+└─ transport/
+   ├─ client.ts
+   └─ stream.ts
```

Call tree:

```diff
 submitForm
 └─ createSession
    ├─ persistPrompt
+   ├─ expandSkillMention
    └─ launchAgent
```
