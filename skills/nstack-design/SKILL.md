---
name: nstack-design
description: The shaping step for big asks. Turns a large, ambiguous, rewrite or new-system ask into a short shape (outcome, verified facts, Nate's decisions, chosen architecture, contracts, slices with checks) before implementation starts. Read for L/XL work, architecture or taste forks, rewrites, and Dross design tasks.
---

# nstack design

The beginning decides the trajectory. Nate's large and huge asks drew four to eight times the corrections of small ones, and the session analyses judged 182 of 421 corrections preventable at this step: a load-bearing fact assumed, taste built before he saw it, a design too broad to verify, a keep silently dropped. This step produces the **shape**: the short document the build runs on. It is not a prose spec, a plan document, or an audit.

## 1. Ground
- Read the code and system the work touches. Name the data shapes, who owns each piece of state, and the seams (APIs, processes, devices, deploy and restart paths).
- Check every load-bearing fact with a command: binary or repo actually used, versions, machine, hardware, data, model, where it runs, how it reaches Nate's surface. Write each one down with how you checked it.
- For a rewrite, list the **keeps**: behaviors and invariants that must survive. Each keep becomes an executable check before the rewrite starts.
- If the shape depends on outside evidence (prior art, vendors, models, standards), run one wide research wave through `skill://research`. Lanes cost cents and nearly every lane's findings reach the answer; the expensive part is your synthesis, so brief lanes on distinct questions rather than trimming them.

## 2. Settle forks
- Observable forks (`[run]`): settle with the cheapest probe and a go/no-go number. Probes come before matrices, datasets, training runs and fan-out.
- Architecture: unless existing code dictates the shape, sketch two structurally different designs, each starting from how a caller uses it. Screen both against the red flags below, pick one, and record why in three to five lines with the rejected alternative. For a one-way door, probe the riskiest difference between them before choosing. If the shape follows existing code, pick that and say so.
- Taste (`[Nate]`), when new or unsettled: study his references, then build several genuinely different directions at real fidelity (rendered frames, mocks, an HTML lab, short clips, variants behind one switcher) on the surface where he will judge them. Different models or approaches may widen the range; this is exploration for his pick, not a panel asked to agree. Include a "none of these" option. Every pick he makes goes into the slice checklist. A default he never reviewed is labelled a default, never recorded as his decision.

Red flags (reject or revise the shape):
- Two modules write the same state, or two ways exist to do one task.
- Callers must know internal rules or call several methods to finish one operation.
- One representation or policy is repeated across modules or hand-synced lists.
- Stages split by execution order instead of by the knowledge they own.
- Types only compile with casts, optional fields that are always set, or escape hatches.
- The design needs a lock where the data could instead have one owner.

## 3. Ask Nate once
Batch every `[Nate]` decision into one message (the `ask` tool in omp, an intent card in Dross): numbered, two to four options each, your recommendation, what each option changes, and the preview when there is one. Pin permissions and grants he must give now, so the run never waits on him later. Ask only what changes the result and no probe can settle.

## 4. Slice
- Order the work as slices. Each slice ends in something Nate can see or use on his real surface, plus the check that proves it.
- Slice 1 is the thinnest end-to-end path at full quality through every layer, riskiest unknown first.
- For a rewrite or migration, build the oracle first: golden outputs, conformance cases or recorded behavior from the old system, on the real topology, so every slice is judged against it. Contracts and oracles are code (types, schemas, golden files, conformance tests) and run as long as they need to.
- Each slice fits one fresh context and a reviewable diff. A slice that needs a different design than the shape says sends you back to section 2. Do not patch around a wrong shape.
- Code that shares files belongs to one owner. Parallel slices need disjoint files and their own checks.

## 5. The shape (output)
Short and complete, every line a fact, decision, contract or check; in the reply and at the top of the ledger `local/nstack/<slug>.md`:

```
Outcome: <Nate's words> / <your reading>
Proof: <surface> — <done-checks>
Keeps: <each as a check>
Out: <deliberately excluded>
Facts: <fact> — <how verified>
Decided: <decision> — <by Nate | by probe: result | default>
Architecture: <chosen shape, 3-5 lines> (rejected: <alternative, why>)
Seams: <shared state and contracts each slice must honor; who integrates; how it reaches his surface>
Slices:
- [ ] 1 <slice> — check: <command or observation on his surface>
- [ ] 2 ...
Log:
- <time> <what happened, what was learned>
```

The log is append-only. The ledger is the only plan or status file. No separate specs, matrices, roadmaps, status files per agent, or design docs unless Nate asks for one.

## 6. Do not
- Start audit waves, or a research wave before reading the code or before Nate has picked a scope its lanes depend on.
- Send a plan to reviewers. Review the prototype or the diff.
- Write a prose spec. Contracts belong in code and tests; everything else fits the shape.
- Hand a worker a program. One brief is one slice, carrying the shape and the contracts it must honor.
- Drop an explicit request because it was phrased casually, treat an offhand reaction as a hard requirement, or keep a reversed decision standing.
