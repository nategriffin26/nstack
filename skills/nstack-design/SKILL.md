---
name: nstack-design
description: "Shape a large ask into a one-page plan before anyone builds. Use for rewrites, new systems, unsettled architecture or look, and plans Nate hands you: verified facts, his decisions, the simplest clean architecture, and vertical slices with done-checks. Read for L/XL work after nstack."
---

# nstack design

Most failures in a large build happen before the first line of code: an assumed fact, a dropped keep, a wish treated as a requirement, taste built at full scale before Nate saw it, or a design too sprawling to verify. This skill produces the one-page shape that guides the build, following `skill://nstack` › Design.

## Ground

- Read the code and system the work touches: data shapes, state ownership, and seams (APIs, processes, devices, deploy and restart paths).
- Tag every requirement **Nate** (he asked), **forced** (it cannot work on his setup without it), or **wish** (goes to **Out**; build nothing for it now).
- Verify every load-bearing fact with a command and record how. For a rewrite, turn every keep into an executable check (golden outputs, conformance cases, recorded behavior) before changing code.
- Check outside facts through `skill://nstack-research` at the smallest size that settles them, after reading the code and pinning scope.

## Walk real failures

For each promise whose break would hurt Nate (unrecoverable work or data, duplicate sends or spends, silent stuck jobs), trace only failures that can happen on his setup:
- process stops mid-step (update, crash, Mac sleep or reboot)
- same command or message arrives twice
- two copies run at once where his setup allows it (timer + manual run, two workers)
- a dependency service is down

Write one line each on what he sees. *"It fails loudly and he reruns it"* is often the right answer and adds zero code. Where he would lose something, choose the simplest fix (atomic write-then-rename, resume on startup, unique key) and record it under **Forced by**. Any fix that adds a new mechanism (queue, retry worker, lock service, extra process) goes to Nate as a decision with the plain alternative beside it.

## When Nate hands you a plan

Read it against the code once and return one concise list: wrong facts, open decisions, and wishes written as requirements. Do not expand the plan or run editing waves over it. His picks in it stand; its mechanisms are judged like any other design. Distill it into the shape below; worker briefs cite the shape, not the raw plan.

## The shape

Batch all `[Nate]` calls into one message up front (`skill://nstack` › Decide) and pin required permissions. Then write one page at the top of the ledger `local/nstack/<slug>.md` for the builders:

```text
Outcome: <Nate's words> / <your reading>
Proof: <surface> - <done-checks>
Requirements: <requirement or number> - <Nate | forced | wish -> Out>
Keeps: <each as an executable check>
Out: <deliberately excluded>
Facts: <fact> - <how verified>
Decided: <decision> - <by Nate | default>
Architecture: <3–5 lines: the plain shape, data model, and ownership> (considered: <alternative, why not>; changes when: <exact signal on his setup>)
Forced by: <each part beyond the plain shape> - <what he asked for, or why it cannot work without it>
Seams: <shared contracts each slice honors; integration owner; how it reaches his surface>
Slices:
- [ ] 1 <slice> - done when: <command or observation on his surface>
```

Slice 1 is the thinnest end-to-end path, riskiest unknown first, setting the clean patterns later slices will follow. When the surface lacks a scripted check, slice 1 also builds the verify script (`skill://nstack-verify` › Evidence). Parallel slices own disjoint modules.

Build a separate plain summary for Nate instead of handing him the builder page: his decisions first, the outcome and where he will check it, a small diagram of parts and state ownership, settled decisions and exclusions, and the slices described by what he will see after each. No separate spec files, roadmaps, or status docs unless he asks; contracts live in code.
