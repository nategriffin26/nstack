---
name: nstack-design
description: The shaping step for big asks. Turns a large, ambiguous, rewrite or new-system ask into a short shape (outcome, requirements, verified facts, Nate's decisions, the simplest correct architecture, contracts, slices with checks) before implementation starts. Read for L/XL work, architecture or taste forks, rewrites, and Dross design tasks.
---

# nstack design

The beginning decides the trajectory. Large asks go wrong far more often than small ones, and much of what goes wrong is set before the first line of code: a load-bearing fact assumed, taste built before Nate saw it, a design too broad to verify, a keep silently dropped. Each is cheap to catch here and expensive to unwind once a build rests on it. This step produces the **shape**: the short document the build runs on. It is not a prose spec, a plan document, or an audit.

## 1. Ground
- Read the code and system the work touches. Name the data shapes, who owns each piece of state, and the seams (APIs, processes, devices, deploy and restart paths).
- Write the requirements: what it must do, the numbers that matter (data size, rates, latency, devices, offline, uptime), and the invariants that must never break (money moves once, no typed text is lost, nothing starts twice). Mark each as Nate's, verified, or your assumption. "Later I might" is a wish, not a requirement.
- Check every load-bearing fact with a command: binary or repo actually used, versions, machine, hardware, data, model, where it runs, how it reaches Nate's surface. Write each one down with how you checked it.
- For a rewrite, list the **keeps**: behaviors and invariants that must survive. Each keep becomes an executable check before the rewrite starts.
- If the shape depends on outside evidence (prior art, vendors, models, standards), run one wide research wave through `skill://research`, briefing lanes on distinct questions.

## 2. Architecture: correct, then as simple as the requirements allow
Nate wants simple, unified systems that are fully correct where it counts. Models drift from that two ways: they add machinery nothing needs, and they under-build the parts that are truly hard. Guard both.
- **Start plain**: one process, one store, modules and direct calls, one owner and one source of truth per piece of state, one mechanism per job, the platform's and the codebase's own facilities, proven libraries over custom engines.
- **Add only what a requirement forces**, and name it: a separate process or service (it must outlive, be isolated from, or run apart from the rest), a queue (work must survive a crash or absorb bursts), a cache (a measured slow path), an interface or plugin point (two real implementations now), an option (a value that really varies), a new framework or store (a need the current one cannot meet). A wish gets a clean seam at most.
- **Build in full what the requirements force**: idempotency and transactions for money or "exactly once", durable state and recovery for anything that must survive a restart, one owner or a constraint for concurrent writers, a merge rule that keeps both sides for offline edits, a boundary for untrusted input and secrets, progress and resumption for long jobs. Put each in one place behind a small interface; use the proven tool (database constraints, a CRDT library, the OS supervisor) before inventing one.
- **Walk the failures**: take each invariant through every failure that applies (a crash between any two steps, a restart, the same message or command twice, two runs at once, a clock or time-zone change, a lost or reset server, a stale read) and say how the design keeps it. A step you cannot show keeps it is underbuilt.
- **Judge it by use**: the next feature touches one obvious place; state can be inspected and failures surface near their cause; it runs fast, fails small, and is cheap to change or delete. Prefer what is easy to change over what anticipates more.
- When the existing shape is the problem (one kind of bug keeps returning, a small change touches many places), say so and propose the simpler shape instead of patching around it; a large rework is a `[Nate]` decision.

Design twice, unless sound existing code dictates the shape (then use it and say so): the first design that comes to mind anchors you, and a real alternative shows which parts are essential. Sketch the plainest design that meets every requirement and the strongest alternative (a second model may draw it; `skill://nstack-agents`), each starting from how a caller uses it. Screen both against the lists below, choose the simpler unless a named requirement rules it out, and record why in three to five lines with the rejected alternative. For a one-way door, probe the riskiest difference before choosing.

Overbuilt (cut unless a requirement forces it): a layer or manager that only forwards; an interface, factory or registry with one implementation; options for values that never change; an event bus, queue or IPC inside one process; another service, daemon or store where a module or the existing store works; a cache nobody measured; the same state kept twice and synced; a framework, DSL or plugin system for one use; a custom engine where a proven library exists; documents in place of a working slice.

Wrong or underbuilt (fix before building): a requirement or invariant the design cannot meet; two writers of one state, or two ways to do one task; callers who must know internal rules or call several methods to finish one operation; one representation or policy repeated across modules or hand-synced lists; stages split by execution order instead of by the knowledge they own; state kept as loose flags, phases or optional fields where a state machine or sum type would make invalid states unrepresentable; external input used past the boundary without one parse into a typed model; types written by hand beside the schema or file that owns the shape; types that only compile with casts or escape hatches; a lock where the data could have one owner.

## 3. Settle the other forks
- Observable forks (`[run]`): settle with the cheapest probe and a go/no-go number. Probes come before matrices, datasets, training runs and fan-out.
- Taste (`[Nate]`), when new or unsettled: study his references, then build several genuinely different directions at real fidelity (rendered frames, mocks, an HTML lab, short clips, variants behind one switcher) on the surface where he will judge them. Different models may widen the range; this is exploration for his pick, not a panel asked to agree. Include a "none of these" option. Every pick goes into the slice checklist; a default he never reviewed is labelled a default.

## 4. Ask Nate once
Batch every `[Nate]` decision into one message (the `ask` tool in omp, an intent card in Dross): numbered, two to four options each, your recommendation, what each option changes, and the preview when there is one. Pin permissions and grants he must give now, so the run never waits on him later. Ask only what changes the result and no probe can settle.

## 5. Slice
- Order the work as slices. Each ends in something Nate can see or use on his real surface, plus the check that proves it. Slice 1 is the thinnest end-to-end path at full quality through every layer, riskiest unknown first.
- For a rewrite, migration or refactor, build the oracle first: golden outputs, conformance cases or recorded behavior from the old system, on the real topology. Without it, a rewrite cannot tell a regression from a change. Contracts and oracles are code (types, schemas, golden files, conformance tests).
- Each slice fits one fresh context and a reviewable diff. A slice that needs a different design than the shape sends you back to section 2; do not patch around a wrong shape. Code that shares files belongs to one owner; parallel slices need disjoint files and their own checks.

## 6. The shape (output)
Short and complete, every line a fact, decision, contract or check; in the reply and at the top of the ledger `local/nstack/<slug>.md`:

```
Outcome: <Nate's words> / <your reading>
Proof: <surface> — <done-checks>
Requirements: <requirement, number or invariant> — <Nate | verified | assumed>
Keeps: <each as a check>
Out: <deliberately excluded>
Facts: <fact> — <how verified>
Decided: <decision> — <by Nate | by probe: result | default>
Architecture: <chosen shape, 3-5 lines> (rejected: <alternative, why>)
Forced by: <each part beyond the plain design> — <the requirement that forces it>
Seams: <shared state and contracts each slice must honor; who integrates; how it reaches his surface>
Slices:
- [ ] 1 <slice> — check: <command or observation on his surface>
Log:
- <time> <what happened, what was learned>
```

The log is append-only. The ledger is the only plan or status file: no separate specs, roadmaps, per-agent status files or design docs unless Nate asks.

## 7. Do not
- Start overlapping or stacked audit waves, or a research wave before reading the code or before Nate has picked a scope its lanes depend on.
- Send a plan to reviewers. Review the prototype or the diff.
- Write a prose spec. Contracts belong in code and tests; everything else fits the shape.
- Hand a worker a program. One brief is one slice, carrying the shape and the contracts it must honor.
- Drop an explicit request because it was phrased casually, treat an offhand reaction as a hard requirement, or keep a reversed decision standing.
