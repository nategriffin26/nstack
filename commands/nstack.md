---
name: nstack
description: Run nstack explicitly. /nstack <task> | shape <ask> | catchup | review | verify | correct <mistake>
---
Nate invoked nstack. Read `skill://nstack` and apply it to the request below. Then, by the first word of the request:

- `shape <ask>`: also read `skill://nstack-design`. Ground, settle what probes can settle, and stop at the shape and the one decision message for Nate. Do not implement.
- `catchup`: read `skill://nstack-writing` and catch Nate up on everything since his last message. Read-only.
- `review`: read `skill://nstack-review` and review the current change once.
- `verify`: read `skill://nstack-verify` and prove the current work on Nate's surface.
- `correct <mistake>`: the mistake keeps coming back. Find its class and the past instances that show it (Nate's corrections, commits, reverts, workaround comments), then fix it at the highest level that holds, per `skill://nstack` section 8: architecture first (one owner per state, one way to do the task, internals unreachable, one list the others derive from), then a type, then a check or lint whose error names the fix (failing only on new cases if the pattern is common), then a test; a rule in the project's AGENTS.md only for a judgment call. Prove each new check fails on a real past instance. Note in the project's AGENTS.md what now enforces it, so the next agent adds no duplicate rule. Stay within the named mistake.
- anything else: do it as a task under nstack.

An empty request means: apply nstack to the rest of this conversation. Acknowledge in one line.

Request: $ARGUMENTS
