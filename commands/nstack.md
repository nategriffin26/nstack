---
name: nstack
description: Run nstack explicitly. /nstack <task> | shape <ask> | review | verify | formal [area | maintain] | correct <mistake>
---
Nate invoked nstack. Read `skill://nstack` and apply it to the request below. By its first word:

- `shape <ask>`: also read `skill://nstack-design`; ground it and stop at the shape and the one decision message. Do not implement.
- `review`: read `skill://nstack-review` and give the current change one deep review.
- `verify`: read `skill://nstack-verify` and prove the current work on Nate's surface.
- `formal [area]`: read `skill://nstack-formal` and run its create pass, starting from the named area or property if any. `formal maintain`: run its maintain pass.
- `correct <mistake>`: the mistake keeps coming back. Find its past instances (Nate's corrections, reverts, workaround comments), fix it at the highest level that holds (architecture, a type, a check whose error names the fix, a test; a project AGENTS.md line only for a judgment call), and prove the new check fails on a real past instance.
- anything else: do it as a task under nstack. An empty request applies nstack to the rest of this conversation.

Request: $ARGUMENTS
