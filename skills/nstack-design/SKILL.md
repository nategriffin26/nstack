---
name: nstack-design
description: The shaping step for big asks. Turns a rewrite, new system or ambiguous program into a one-page shape (requirements tagged by source, verified facts, Nate's decisions, the simplest correct architecture, contracts, slices with done-checks) before builders start. Read for L/XL work, architecture or taste forks, a plan Nate hands you, and Dross design tasks.
---

# nstack design

Most of what goes wrong in a big build is set before the first line of code: a fact assumed, taste built before Nate saw it, a design too broad to verify, a keep dropped, a wish built as a requirement. The shape is the one page the build runs on. Simple, correct architecture matters more than anything else on it.

## 1. Ground
- Read the code and system the work touches: data shapes, who owns each piece of state, the seams (APIs, processes, devices, deploy and restart paths).
- Requirements: what it must do, the numbers that matter, the invariants that must never break. Tag each **Nate** (he asked), **forced** (his setup or another requirement makes it necessary) or **wish**. A wish gets a clean seam, not machinery.
- Check every load-bearing fact with a command and write down how. For a rewrite, list the keeps; each becomes an executable check (golden outputs, conformance cases, recorded behavior) before the rewrite starts.
- Outside evidence: one wide research wave through `skill://research`, after the code is read and any scope Nate must pick is pinned.

## 2. Architecture
- **Start plain** and **add only what a requirement forces**, naming it: a service that must outlive or be isolated from the rest, a queue for work that must survive a crash, a cache for a measured slow path, an interface with two real implementations now.
- **State machines where they fit**: give each entity with a lifecycle (a job, a message, an order, a session) one explicit set of states and the transitions between them, owned in one place. Invalid states become unrepresentable, and a model or a person can read the whole behavior from one table.
- **Build in full what is forced**: idempotency for money or exactly-once, durable state and recovery, one owner for concurrent writers, a merge rule for offline edits, a boundary for untrusted input, resumption for long jobs. Walk each invariant through the failures that can happen on his setup (a crash between steps, a restart, a duplicate, two runs at once) and say how it holds.
- **Overbuilt**: a layer that only forwards; an interface with one implementation; options for values that never change; a bus or queue inside one process; another service or store where a module works; an unmeasured cache; the same state kept twice and synced; a framework for one use.
- **Underbuilt**: a requirement the design cannot meet; two writers of one state or two ways to do one task; callers that must know internals; loose flags where a state machine or sum type belongs; external input used past the boundary without one parse into a typed model; types that need casts.
- **Options**: think through two or three real designs (the plainest, the strongest alternative, a blend), each from how a caller uses it. Take the best or a blend by judgment and record why in a few lines. Never build or benchmark both to compare.

## 3. A plan Nate hands you
Read it against the code once and return one list: wrong facts, open decisions, and wishes written as requirements. Never an edit wave, and the plan does not grow. His picks in it stand; its mechanisms are judged like any design above. Distill it into the shape; briefs cite the shape, not the plan.

## 4. Ask once, then slice
Batch every `[Nate]` decision into one message (`skill://nstack` §2), each option with its time and usage estimate and your default, and pin the permissions the run will need. Then slice: each slice ends in something he can see on his surface with its check; slice 1 is the thinnest end-to-end path, riskiest unknown first; parallel slices own disjoint modules.

## 5. The shape
One page, in the reply and at the top of the ledger `local/nstack/<slug>.md`:

```
Outcome: <Nate's words> / <your reading>
Proof: <surface> - <done-checks>
Requirements: <requirement, number or invariant> - <Nate | forced | wish -> seam>
Keeps: <each as a check>
Out: <deliberately excluded>
Facts: <fact> - <how verified>
Decided: <decision> - <by Nate | default>
Architecture: <3-5 lines; state machines named> (considered: <alternative, why not>)
Forced by: <each part beyond the plain design> - <requirement>
Seams: <shared contracts each slice honors; who integrates; how it reaches his surface>
Slices:
- [ ] 1 <slice> - done when: <command or observation on his surface>
Log:
- <time> <what happened>
```

No separate specs, roadmaps or status files unless Nate asks; contracts live in code.
