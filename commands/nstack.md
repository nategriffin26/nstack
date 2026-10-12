---
name: nstack
description: Run nstack explicitly. /nstack <task> | shape <ask> | catchup | review | verify
---
Nate invoked nstack. Read `skill://nstack` and apply it to the request below. Then, by the first word of the request:

- `shape <ask>`: also read `skill://nstack-design`. Ground, settle what probes can settle, and stop at the shape and the one decision message for Nate. Do not implement.
- `catchup`: read `skill://nstack-writing` and catch Nate up on everything since his last message. Read-only.
- `review`: read `skill://nstack-review` and review the current change once.
- `verify`: read `skill://nstack-verify` and prove the current work on Nate's surface.
- anything else: do it as a task under nstack.

An empty request means: apply nstack to the rest of this conversation. Acknowledge in one line.

Request: $ARGUMENTS
