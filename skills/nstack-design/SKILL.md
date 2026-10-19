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
Spend design where a mistake is expensive to reverse, and keep the rest plain and cheap to change. Each rule below is a default with the condition that flips it: apply the ones the requirements touch, and keep a sound existing codebase's patterns over them.

- **One-way doors first**: the data model and who owns each piece, trust and security boundaries, contracts something else depends on (persisted formats, APIs, protocols, IDs, file layouts), and durability, sync and merge rules. Settle these deliberately, with Nate where they change what he sees. Internals behind a stable contract are two-way doors: choose fast and let them follow the code.
- **Start plain** and **add only what a requirement forces**, naming it: a separate process for something that must outlive, be isolated from, scale or deploy apart from the rest, or run on another runtime or device; a queue for work that must survive a crash; a cache for a measured slow path; an interface with two real implementations now. Otherwise one process, one store, modules and direct calls, the platform's own facilities, and widely used libraries at pinned versions.
- **Data first**: one owner and one source of truth per piece of state; derive what can be derived instead of storing and syncing it. Parse external input (files, APIs, user and model output) once at the boundary into precise types, so nothing past it re-checks or guesses a shape. A value with several cases is a sum type, not flags that can contradict each other.
- **Modules**: each hides one decision behind a small interface and does real work behind it; dependencies point one way, without cycles; a feature's change lands in one obvious place. Hidden coupling costs most: ambient global state, calls that only work in a certain order, formats two places agree on that no type or contract states. Prefer duplication to a wrong abstraction; extract on the third real use.
- **State machines where they fit**: an entity whose lifecycle has wrong transitions that do harm (a job, a payment, a session, a connection, a device mode, an agent run) gets one explicit set of states and one transition function that owns every change, so invalid states and jumps cannot happen and the behavior reads from one table. Take the plainest form that holds: a sum type and an exhaustive transition function, pure (state and event in, next state and effects out) with effects run outside it; state persisted with guarded writes (change only if the state is still the one read) when it must survive restarts or concurrent writers; typestate when the order is fixed at compile time; a statechart library only for real nesting or parallel regions. They do not fit linear or few-branch logic (plain code), or independent dimensions forced into one machine (states multiply: use separate machines or nesting). A wait on a person or another system is usually just a persisted state; a durable-execution engine earns its runtime and versioning cost only when many steps, retries and branches outgrow that.
- **Failure**: build in full what is forced (idempotency for money or exactly-once effects, durable state and recovery, one owner for concurrent writers, a merge rule for offline edits, a boundary for untrusted input, resumption for long jobs), each in one place, with the proven tool (database constraints and transactions, the OS supervisor, a CRDT library) before a homemade one. Serious failures cluster in error handling, so: recovery is the startup path; every remote call has a timeout; retry only idempotent work, with backoff and jitter; deliver at least once to idempotent consumers, never promise bare exactly-once; contending writers go through transactions or version checks, and a store that allows one writer at a time (SQLite) gets exactly one; errors surface loudly near their cause, never swallowed. Walk each invariant through every failure that applies (a crash between any two steps, a restart, the same message twice, two runs at once, a clock or time-zone change, a lost or reset server, a stale read) and say how it holds.
- **Checkable by construction**: keep decisions in a deterministic core and push clock, randomness, network and disk to its edge, so the core runs in tests and replays. Give builders oracles outside the model: types and the compiler, tests written from the intent, property tests for core invariants, golden outputs for keeps, assertions on invariants. A model's review of its own code is not an oracle. Model checking (TLA+ and the like) pays only for concurrent or distributed protocols that must not fail.
- **LLM components**: deterministic code owns control flow and state; a model call is a step whose structured output is parsed into types. Start with one call or one simple tool loop; add agents only for a named need. A wait for Nate or another system is persisted state that survives a restart. Outside content (mail, web pages, files, tool results) must never trigger consequential actions: a flow that combines private data, untrusted content and a way to send things out breaks one of the three (a plan fixed before untrusted data arrives, a quarantined model with no tools, or Nate's approval). Evals are the oracle for model behavior.
- **Built by agents**: agents copy what the repo already does, so slice 1 sets the patterns and each job has one way to do it. Hold structure with checks whose errors name the fix (types, lints, structural tests), not prose. Prefer languages, libraries and versions agents know well; a new or fast-moving API needs its docs at hand and a test.
- **Overbuilt**: a layer that only forwards; an interface, factory or registry with one implementation; options for values that never change; a bus or queue inside one process; another service or store where a module works; an unmeasured cache; the same state kept twice and synced; a framework, DSL or machine library for one simple flow; defensive code for cases that cannot happen.
- **Underbuilt**: a requirement the design cannot meet; two writers of one state or two ways to do one task; callers that must know internals; loose flags where a state machine or sum type belongs; external or model input used past the boundary without one parse; types that need casts; error paths no test runs; a remote call without a timeout; a retry of non-idempotent work; untrusted content that can reach a consequential action.
- **Judge it by use**: the next feature touches one obvious place; state can be inspected and failures surface near their cause; it runs fast, fails small, and is cheap to change or delete.
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
Architecture: <3-5 lines; one-way doors, state owners and state machines named> (considered: <alternative, why not>)
Forced by: <each part beyond the plain design> - <requirement>
Seams: <shared contracts each slice honors; who integrates; how it reaches his surface>
Slices:
- [ ] 1 <slice> - done when: <command or observation on his surface>
Log:
- <time> <what happened>
```

No separate specs, roadmaps or status files unless Nate asks; contracts live in code.
