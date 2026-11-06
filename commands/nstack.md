---
name: nstack
description: Run nstack explicitly. /nstack <task> | shape <ask> | grill [topic] | review | verify | formal [area | maintain] | correct <mistake> | simplify [area]
---
Nate invoked nstack. Read `skill://nstack` and apply it to the request below. By its first word:

- `shape <ask>`: also read `skill://nstack-design`; ground it and stop at the shape and the one decision message. Build nothing.
- `grill [topic]`: read `skill://nstack-grill` and grill Nate on the topic, or the current task, until he confirms the frame.
- `review`: read `skill://nstack-review` and give the current change one deep review, from an agent of another model family than the one that wrote it.
- `verify`: read `skill://nstack-verify` and prove the current work on Nate's surface.
- `formal [area]`: read `skill://nstack-formal` and run its create pass from the named area or property; `formal maintain` runs its maintain pass.
- `correct <mistake>`: the mistake keeps coming back. Find its past instances (his corrections, reverts, workaround comments), fix it at the highest level that holds (the architecture, a type, a check whose error names the fix, a test; a project AGENTS.md line only for a judgment call), and prove the new check fails on a real past instance.
- `simplify [area]`: make an area smaller without changing what it does. Take the area from the request, or from `git log`: the files changed most in recent commits, and files that keep changing together (often one concept split in two). Cut what `skill://nstack` › Design calls overbuilt and what the review's simplify questions find (`skill://nstack-review` › Method), plus modules whose interface is nearly as large as their body (one whose deletion only moves a few lines merges into its caller or neighbor), dead code, compatibility shims, defensive checks on trusted paths, type escapes, and comments that narrate the code or its history. Keep every capability, state and safeguard Nate asked for. Tests pass before and after, each simplification is its own commit, and a change to an interface other code or Nate uses goes to him first. Report the lines and concepts removed, and the median files touched per commit in the area over its last 20 commits before this pass, recorded in the last commit's body and compared with the previous pass's number when there is one.
- anything else: do it as a task under nstack. An empty request applies nstack to the rest of this conversation.

Request: $ARGUMENTS
