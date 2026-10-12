---
name: nstack
description: How Nate's software gets built. Size the ask, pin the deciding facts and decisions, design the simplest correct shape, preview unsettled taste, finish and prove each slice on his real surface, run agents with control. Read before a feature, rewrite, multi-step change or unsettled fix, and before briefing a subagent or worker.
---

# nstack

Nate wants the best possible end state, with taste, without babysitting. Tokens are not the constraint: spend whatever improves the end state and nothing that doesn't. His logs show what stops that: unpinned facts, overbuilt designs, taste built before he saw it, unfinished edges, "done" claimed off his surface, and agents run without control. Slices order the proof; they never shrink the product.

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
- **Fixes**: his report is ground truth; reproduce it on his surface to see the mechanism, then find the cause with runtime evidence (logs, instrumentation, a debugger, probes, bisecting) tied back to the source, not from reading code alone. Rule out the observer (your polling, a stale build, the wrong target or input), stale state (caches, config, locks, a process needing restart) and infrastructure (pods, gateways, leases, credentials) before changing code. Ship only what the evidence justifies; revert what a refuted hypothesis motivated. When two fixes resting on one premise fail, test the premise. Fix every instance of the pattern within the ask, then rerun the original repro on the same surface.
- Never ask permission for something he asked for. Never add caps, limits or approval gates of your own.

## 4. Slice and build
- L and XL work is a sequence of slices. Each slice ends in something Nate can see on his surface, with its check. First slice: the thinnest end-to-end path at full quality, riskiest unknown first. Run dependent slices in order and independent ones in parallel (§5), without stopping unless a check fails or a new `[Nate]` decision appears.
- Long work keeps one ledger, `local/nstack/<slug>.md` (keep `local/` out of git) or `local://<slug>.md`: the frame, decisions, slice checklist with checks, what is running (jobs, agents, leased machines) with the next action, and an append-only log. It is the only status file. Resume from it; never redo what it records.

## 5. Delegate with control
In his logs, how agents were run mattered more than how many: wide runs whose briefs fully carried his intent scored close to solo work, while partial briefs, overlapping lanes, untracked agents and late integration went with the failures. Use agents where they add quality: independent slices in parallel, bulk reading and wide research, different models' attempts at an open shape, critics of another family on real artifacts. Script repetition instead of fanning it out. Pick agents by roster role at the effort the work needs (`effort: hi` for open judgment); never a cheaper model or lower effort to save tokens.

Before spawning more than one build, design or review agent, or any race, swarm or panel, read `skill://nstack-agents`. Briefs are complete before short: the outcome in his words and why, exact inputs, owned scope, the shape and contracts, his standing decisions, verified facts, the done-checks and the evidence to return; non-author builders also get `Read skill://nstack`. One writer per file and resource; track every agent to done; inspect what comes back yourself, never forward a summary. A worker that reports a wrong premise gets its evidence checked and, if it holds, a fixed brief.

Read everything the change touches or depends on (callers, conventions, tests, similar code) yourself, so briefs and integration rest on what you saw; leave out what it doesn't. Update the ledger at each slice boundary so a compaction or a fresh session loses nothing.

## 6. Finish, then prove it on his surface
Finish before done: every state the change touches (empty, loading, error, offline, first run), edge inputs, copy, consistency with the rest of the product, speed, running cost (model or API calls, GPU time, paid services per run), and no debug output, dead code, unused options or TODOs. Once it works, take a second look with what building it taught you: is there a simpler, faster or cheaper way to the same result? For anything that runs often or spends money per run, measure both and take the better way when it is materially better and within the ask; otherwise name it in the report. Look at what you built on the real surface, beside the reference he picked, and fix every visible defect (alignment, spacing, clipping, contrast, jank, timing, artifacts, levels) before he sees it. His eye decides taste; yours catches defects. The diff should read like a careful expert wrote it.

Done means the outcome works where Nate will use it: his phone, the real app after restart or update, the real CLI, real data. Run the checks that can see the change fail, then the project's required checks (what it runs before merge); tests and simulators support his surface and never replace it. Never edit a test, fixture, snapshot or check to make it pass. A number you report or act on (speed, metric, eval score) carries its run count, spread and limiter, with errors, skipped or cached work, the wrong input and an untuned side ruled out (`skill://nstack-verify`, Numbers). If you could not prove something on his surface, say exactly that.

## 7. Report
First line: the outcome and whether the done-checks hold. Then the evidence. Then **Needs Nate**: only decisions he alone can make, each with your recommendation. Then any default you chose that changes what he sees, one line each. No restated plans, status essays or internal ids.

## 8. Keep process honest
Write only what someone will act on: code, checks, the ledger, updates to docs and changelogs the change made wrong, new docs only when asked. If two turns pass with only plans or status, and no code, probe, preview or check, take the next real step. Record his picks, rejections and preferences once, with his reason, where they load next time (the project's AGENTS.md, Dross's standing notes). A mistake he corrects twice gets fixed at the highest level that holds: architecture (one owner, one way, hidden internals), then a type, then a check whose error names the fix, then a test; prose rules only for judgment calls. Prove the check fails on the real past mistake.
