---
name: nstack
description: Run nstack explicitly. /nstack <task> | shape <ask> | grill [topic] | review | verify | formal [area | maintain] | correct <mistake> | simplify [area]
---
Nate invoked nstack. Read `skill://nstack` and apply it to the request below. By its first word:

- `shape <ask>`: also read `skill://nstack-design`; ground it and stop at the shape and the one decision message. Do not implement.
- `grill [topic]`: read `skill://nstack-grill` and grill Nate on the topic (or the current task) in rounds until he confirms the frame. Build nothing before his yes.
- `review`: read `skill://nstack-review` and give the current change one review.
- `verify`: read `skill://nstack-verify` and prove the current work on Nate's surface.
- `formal [area]`: read `skill://nstack-formal` and run its create pass, starting from the named area or property if any. `formal maintain`: run its maintain pass.
- `correct <mistake>`: the mistake keeps coming back. Find its past instances (Nate's corrections, reverts, workaround comments), fix it at the highest level that holds (architecture, a type, a check whose error names the fix, a test; a project AGENTS.md line only for a judgment call), and prove the new check fails on a real past instance.
- `simplify [area]`: make an area smaller without changing what it does. Take the area from the request, or from `git log`: the files changed most in recent commits, and files that keep changing together (often one concept split in two). In it, find modules whose interface is nearly as large as their body (a module earns its place when deleting it would spread complexity into its callers; one whose deletion only moves a few lines merges into its caller or neighbor), layers that only forward, two ways to do one job, duplicate helpers or definitions, arguments or booleans that pick between implementations, dead code, compatibility shims, defensive checks and catches on trusted paths, type escapes (`any`, forced casts, ignore comments), comments that narrate the code, and silent defaults. Keep every capability, state and safeguard Nate asked for (the project's AGENTS.md and rules record them). Tests pass before and after, each simplification is its own commit, and a change to an interface that other code or Nate uses goes to him first. Report the lines and concepts (modules, exports, options) removed, and the median number of files touched per commit in the area over its last 20 commits before this pass; put that number in the last commit's body, and when a previous pass recorded one, compare it with the commits made since that pass.
- anything else: do it as a task under nstack. An empty request applies nstack to the rest of this conversation.

Request: $ARGUMENTS
