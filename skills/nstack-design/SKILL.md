---
name: nstack-design
description: "Shape a big ask into a one-page plan before anyone builds. For rewrites, new systems, an unsettled architecture or look, and plans Nate hands you: verified facts, his decisions, the simplest architecture, slices with checks. Read for L/XL work, after nstack."
---

# nstack design

Most of what goes wrong in a big build is set before the first line of code: a fact assumed, a keep dropped, a wish built as a requirement, taste built before Nate saw it, a design too broad to verify. The shape is the one page the build runs on, and its architecture follows `skill://nstack` › Design.

## Ground
- Read the code and system the work touches: data shapes, who owns each piece of state, the seams (APIs, processes, devices, deploy and restart paths).
- Tag each requirement **Nate** (he asked), **forced** (it cannot work on his setup without it) or **wish**; a wish goes under Out and gets nothing now.
- Check every load-bearing fact with a command and note how. For a rewrite, turn each keep into an executable check (golden outputs, conformance cases, recorded behavior) before the rewrite starts.
- Outside evidence comes through `skill://nstack-research` at the smallest size that settles it, after the code is read and any scope he must pick is pinned.

## Walk his real failures
For each promise whose break would cost him (work or data he cannot redo, a send or spend done twice, a job stuck without him knowing), walk only what happens on his setup: the process stopping mid-step (an update, a crash, his Mac sleeping or rebooting), the same command or message arriving twice, two copies running where his setup can start two (a timer and a manual run, two workers), a service it depends on being down. One line each on what he sees. "It fails loudly and he reruns it" is a good answer and builds nothing. Where he would lose something, take the fix that keeps the design as simple (write then rename, resume on startup, a unique key) and note it under `Forced by`; a fix that adds a mechanism (a queue, retries, a lock, another process) goes to him as a decision, defaulting to skip. Attackers, scale, clock changes and other users are walked only when the project is published to, or serves, people other than him; only walks that change the design are written down.

## A plan he hands you
Read it against the code once and return one list: wrong facts, open decisions, and wishes written as requirements. Never an edit wave, and the plan does not grow. His picks in it stand; its mechanisms are judged like any design. Distill it into the shape; briefs cite the shape, not the plan.

## The shape
Batch every `[Nate]` decision into one message first (`skill://nstack` › Decide) and pin the permissions the run will need. Then write one page at the top of the ledger `local/nstack/<slug>.md`, for the agents that build from it:

```
Outcome: <Nate's words> / <your reading>
Proof: <surface> - <done-checks>
Requirements: <requirement or number> - <Nate | forced | wish -> Out>
Keeps: <each as a check>
Out: <deliberately excluded>
Facts: <fact> - <how verified>
Decided: <decision> - <by Nate | default>
Architecture: <3-5 lines: the plain shape, its data and who owns it> (considered: <alternative, why not>; changes when: <the signal on his setup>)
Forced by: <each part beyond the plain shape> - <what he asked for, or why it cannot work without it>
Seams: <shared contracts each slice honors; who integrates; how it reaches his surface>
Slices:
- [ ] 1 <slice> - done when: <command or observation on his surface>
```

Slice 1 is the thinnest end-to-end path, riskiest unknown first, and it sets the patterns agents will copy, so it stays plain. When the surface has no scripted way in, slice 1 also builds the verify script (`skill://nstack-verify` › Evidence), so every later slice can prove itself there. Parallel slices own disjoint modules.

Nate reads a version built for him, never the page itself: what he must decide first; the outcome and where he will check it; the architecture as a small diagram of its parts and who owns each piece of data; the decisions, his and your defaults, and what is out; the slices by what he will see after each. No separate specs, roadmaps or status files unless he asks; contracts live in code.
