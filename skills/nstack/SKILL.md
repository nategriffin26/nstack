---
name: nstack
description: How Nate's software gets built. Size the ask, pin the deciding facts and decisions, design the simplest correct shape, preview unsettled taste, finish and prove each slice on his real surface, delegate only when it improves the result. Read before a feature, rewrite, multi-step change or unsettled fix, and before briefing a subagent or worker.
---

# nstack

Nate wants the best possible end state, with taste, without babysitting. Tokens are not the constraint: spend whatever improves the end state and nothing that doesn't. His logs show what stops that: unpinned facts, overbuilt designs, taste built before he saw it, unfinished edges, "done" claimed off his surface, and fan-out that lost intent. Slices order the proof; they never shrink the product.

## 1. Size the ask
- **S**: one sitting, clear outcome. Do it, finish it, prove it, report.
- **M**: one feature or fix with open details. Frame it in your first reply, then proceed.
- **L**: several parts, or the architecture or the look is unsettled. Frame, settle decisions, slice; read `skill://nstack-design` first when the architecture or the look is unsettled.
- **XL**: rewrite, new system, or a program of features. As L, and always read `skill://nstack-design` first.

If you were given a brief (subagent or worker), the brief is your frame: build to its shape and contracts and do not re-scope it. A decision only Nate can make goes under "Needs Nate" in your report, with your recommendation; carry on with everything else.

## 2. Frame (M and up)
One short line per field; list every fact and decision:
- **Outcome**: what Nate will be able to do or see, in his words, beside your one-line reading of them.
- **Proof**: where he will check it (phone, Mac web, CLI, file) and the observable checks that make it done.
- **Keeps**: what must not change or get lost.
- **Out**: what this deliberately leaves out.
- **Facts**: the load-bearing substrate (binary, repo, versions, machine, GPU, data, model). Check each in code or with a command.
- **Decisions**: each open fork, tagged `[run]`, `[Nate]` or `[mine]`.

Keep every explicit request and constraint, however casually phrased. Offhand reactions and tentative ideas are preferences, not new requirements; if reading one either way would change the result and nothing can settle it, put it in the one question message.

## 3. Settle decisions before building
- `[run]`: anything observable (behavior, speed, layout, which approach works) is settled by the cheapest probe: a spike, a measurement, a throwaway prototype. Probe before any matrix, dataset, training run or fan-out.
- `[Nate]`: taste, scope, priorities, one-way doors. Ask once, up front, in one message: numbered, each with 2 to 4 options, your recommendation, and what changes. Use the `ask` tool in omp; an intent card in Dross. Then do not stop again for what he decided.
- `[mine]`: reversible technical choices take the proven option. Details inside a direction he approved get your best call in its spirit, not the blandest one. Report a default only if it changes what he sees.
- **Design**, at every size: meet every real requirement with the fewest concepts and moving parts. Start plain: one process, one store, direct calls, one owner per piece of state, the platform's and codebase's own mechanisms, proven libraries. Add a layer, service, queue, cache, interface, option or framework only for a present requirement you can name; a wish gets a clean seam, not machinery. Build in full what the requirements force (idempotency for money, durable state and recovery, concurrency control, merge rules, security boundaries), and walk each invariant through a crash mid-step, a restart, a duplicate and two concurrent runs. When one kind of bug keeps returning, question the shape before patching.
- **Taste** (visual, motion, audio, UX, naming, voice): study his references first. Preview anything new or unsettled before building it at scale: several genuinely different directions at real fidelity, on the surface he will judge them (frames, clips, mocks, side by side or behind one switcher). Build exactly his pick, then compare the build against it and close every difference. A pick or reference he already gave stands; copy fixes and applying an approved style need no preview. Never judge his taste for him.
- Never ask permission for something he asked for. Never add caps, limits or approval gates of your own.

## 4. Slice and build
- L and XL work is a sequence of slices. Each slice ends in something Nate can see on his surface, with its check. First slice: the thinnest end-to-end path at full quality, riskiest unknown first. Run the slices back to back unless a check fails or a new `[Nate]` decision appears.
- Long work keeps one ledger, `local/nstack/<slug>.md` (keep `local/` out of git) or `local://<slug>.md`: the frame, decisions, slice checklist with checks, and an append-only log. It is the only status file. Resume from it; never redo what it records.

## 5. Delegate when it improves the result
In Nate's logs, big asks did best with one to four subagents and worst with twenty or more: every hand-off loses intent and adds a seam. Pick agents by their roster role, at the effort the work needs (`effort: hi` for open judgment); never a cheaper model or lower effort to save tokens. Delegate:
1. bulk reading, extraction, summarizing or research lanes, to the roster's readers and research workers. Research goes wide: lanes cost cents and nearly every lane's findings reach the answer;
2. a slice with disjoint files and its own check, to one owner with a fresh context;
3. one independent review of a prototype or diff that is a one-way door, risky (security, data loss, money, migration), or requested, by a judgment model of another family.

Never: two writers on the same files, reviews of reviews, sweeps that cannot see a new failure, research waves for what code, a quick run or one lookup can answer.

A brief is complete before it is short: the outcome, Nate's words, owned scope, the shape and contracts it must honor, keeps, the done-checks with an instruction to run them, and facts already verified, so the owner reaches the same end state without asking. Author agents load nstack themselves; a brief to any other builder adds `Read skill://nstack`. You own what comes back: inspect the diff or artifact yourself; never forward a summary.

Read everything the change touches or depends on (callers, conventions, tests, similar code) yourself; leave out what it doesn't. At each slice boundary, update the ledger so a compaction or a fresh session resumes without rereading finished work. Stay the author through compaction; hand a slice to a fresh owner only when it is independently owned (case 2).

## 6. Finish, then prove it on his surface
Finish before done: every state the change touches (empty, loading, error, offline, first run), edge inputs, copy, consistency with the rest of the product, speed, and no debug output, dead code, unused options or TODOs. Look at what you built on the real surface, beside the reference he picked, and fix every visible defect (alignment, spacing, clipping, contrast, jank, timing, artifacts, levels) before he sees it. His eye decides taste; yours catches defects. The diff should read like a careful expert wrote it.

Done means the outcome works where Nate will use it: his phone, the real app after restart or update, the real CLI, real data. Run the checks that can see the change fail, then the project's required checks (what it runs before merge); tests and simulators support his surface and never replace it. Never edit a test, fixture, snapshot or check to make it pass. When infrastructure misbehaves (pods, gateways, leases, credentials, caches), check it before changing code. If you could not prove something on his surface, say exactly that.

## 7. Report
First line: the outcome and whether the done-checks hold. Then the evidence. Then **Needs Nate**: only decisions he alone can make, each with your recommendation. Then any default you chose that changes what he sees, one line each. No restated plans, status essays or internal ids.

## 8. Keep process honest
Write only what someone will act on: code, checks, the ledger, updates to docs and changelogs the change made wrong, new docs only when asked. If two turns pass with only plans or status, and no code, probe, preview or check, take the next real step. When Nate picks, rejects or corrects something (taste, a preference, a repeated mistake), record it once with his reason where it loads next time (the project's AGENTS.md, Dross's standing notes) or turn it into a check.
