# Horizontal sequence

```text
Customer          App              Payment
   |               |                  |
   |-- submit ---->|                  |
   |               |-- authorize ---->|
   |               |<--- approved ----|
   |<-- confirm ---|                  |
   |               |                  |
```

If this does not fit, shorten participant and message names or split the interaction into focused phases. Keep time vertical and participants horizontal. For handoffs between people or teams, make each role a column, label each arrow with what is handed over, and note a wait on the time axis when the wait matters.
