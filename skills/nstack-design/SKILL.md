---
name: nstack-design
description: The shaping step for big asks. Turns a rewrite, new system or ambiguous program into a one-page shape (requirements tagged by source, verified facts, Nate's decisions, the simplest correct architecture, contracts, slices with done-checks) before builders start. Read for L/XL work, architecture or taste forks, a plan Nate hands you, and Dross design tasks.
---

# nstack design

Most of what goes wrong in a big build is set before the first line of code: a fact assumed, taste built before Nate saw it, a design too broad to verify, a keep dropped, a wish built as a requirement. The shape is the one page the build runs on. A simple architecture matters more than anything else on it.

## 1. Ground
- Read the code and system the work touches: data shapes, who owns each piece of state, the seams (APIs, processes, devices, deploy and restart paths).
- Requirements: what it must do and the numbers that matter. Tag each **Nate** (he asked), **forced** (it cannot work at all on his setup without it) or **wish**. A wish gets nothing now; list it under Out.
- Check every load-bearing fact with a command and write down how. For a rewrite, list the keeps; each becomes an executable check (golden outputs, conformance cases, recorded behavior) before the rewrite starts.
- Outside evidence: one wide research wave through `skill://research`, after the code is read and any scope Nate must pick is pinned.

## 2. Architecture
The goal is the simplest architecture that does what Nate asked, well. Simple wins: it is quick to build, easy to read, and can be extended when a real need shows up. Nothing here requires a feature, safeguard or mechanism; every part of the design traces to something he asked for or something it cannot work without.

- **Start plain**: one process, one store, modules and direct calls, the platform's own facilities, proven libraries. Add a service, queue, cache, interface, option or framework only when he asked for it or the plain version has actually failed, and say why under `Forced by`.
- **One source of truth**: each piece of state has one owner and lives in one place; derive what can be derived instead of storing and syncing a copy.
- **Data model**: it is the hardest part to change later, so it gets the most thought; keep it as small as today's needs allow.
- **Changes stay local**: a feature's change lands in one obvious place. Slice 1 sets the patterns agents will copy, so keep it plain and give each job one way to do it. Prefer duplication to a wrong abstraction; extract on the third real use.
- **State machines when they simplify**: something with a real lifecycle (a job, an order, a session, a device mode) is often simplest as one status with its allowed transitions in one place, instead of flags scattered through the code. A plain enum and one function, no library; skip it for linear or few-branch logic.
- **LLM parts**: one model call or one simple tool loop; agents, graphs or frameworks only when he asks or the simple version fails.
- **Errors**: let them surface where they happen; catch only what the code can handle. No retries, timeouts, fallbacks, validation layers or security hardening nobody asked for.
- **Overbuilt** (cut it): a layer that only forwards; an interface, factory or registry with one implementation; options for values that never change; a bus or queue inside one process; another service or store where a module works; an unmeasured cache; the same state kept twice and synced; a framework, DSL or library for one simple flow; handling, checks or protection for failures and threats nobody named; design for scale, users or devices that do not exist yet.
- **Too thin** means only: something he asked for that the design cannot do, or one piece of state or one job owned in two places.
- **Judge it by use**: it does what he asked; the next feature touches one obvious place; it is easy to read, quick to change and cheap to delete.
- **Options**: think through two or three real designs, starting from the plainest, each from how it gets used; take the simplest that does the job and say why in a line. Never build or benchmark both to compare.

## 3. A plan Nate hands you
Read it against the code once and return one list: wrong facts, open decisions, and wishes written as requirements. Never an edit wave, and the plan does not grow. His picks in it stand; its mechanisms are judged like any design above. Distill it into the shape; briefs cite the shape, not the plan.

## 4. Ask once, then slice
Batch every `[Nate]` decision into one message (`skill://nstack` §2), each option with its time and usage estimate and your default, and pin the permissions the run will need. Then slice: each slice ends in something he can see on his surface with its check; slice 1 is the thinnest end-to-end path, riskiest unknown first; parallel slices own disjoint modules.

## 5. The shape
One page, in the reply and at the top of the ledger `local/nstack/<slug>.md`:

```
Outcome: <Nate's words> / <your reading>
Proof: <surface> - <done-checks>
Requirements: <requirement or number> - <Nate | forced | wish -> Out>
Keeps: <each as a check>
Out: <deliberately excluded>
Facts: <fact> - <how verified>
Decided: <decision> - <by Nate | default>
Architecture: <3-5 lines: the plain shape, its data and who owns it> (considered: <alternative, why not>)
Forced by: <each part beyond the plain shape> - <what he asked for, or why it cannot work without it>
Seams: <shared contracts each slice honors; who integrates; how it reaches his surface>
Slices:
- [ ] 1 <slice> - done when: <command or observation on his surface>
Log:
- <time> <what happened>
```

No separate specs, roadmaps or status files unless Nate asks; contracts live in code.
