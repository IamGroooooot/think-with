# Layered dependencies

Put modules or packages in rows by layer, entry points at the top. When the user states the intended layering, use theirs, since a violation only means something against the intent. Keep every edge: list each package's imports beside it, grouping targets by layer when a list would wrap. A layer map without its edges hides both the structure and the path that makes a violation matter. Mark a violating import in place with ✗, and draw a cycle as a closed loop so both directions are visible. The example illustrates the level, not a template.

```text
entry   cli     → sync
        server  → sync, search
core    sync    → index, store
        search  → index
data    index   → store, sync ✗
        store

cycle   sync ──▶ index
          ▲        │  ✗ index/rebuild imports sync/queue
          └────────┘
```

When a violation pulls code where it should not go, add what it drags in: the path from each affected entry point, as in `web → ui → billing`, or a small table of entry points against affected packages.

For lookup or grouping questions, such as what each layer imports, use a from/to matrix when adjacency lists would wrap badly. Put rows and columns in the same layer order; each row imports the columns marked in it, so a mark left of the diagonal is an upward edge or part of a cycle.
