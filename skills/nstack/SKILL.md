---
name: nstack
description: How Nate's software gets built. Size the ask, pin the deciding facts and decisions, preview unsettled taste, prove each slice on his real surface, delegate only when it pays. Read before a feature, rewrite, multi-step change or unsettled fix, and before briefing a subagent or worker.
---

# nstack

Nate wants the whole thing at full quality without babysitting. His logs show what stops that: unpinned facts, taste built before he saw it, "done" claimed off his surface, and fan-out. Slices order the proof; they never shrink the product.

## 1. Size the ask
- **S**: one sitting, clear outcome. Do it, prove it, report.
- **M**: one feature or fix with open details. Frame it in your first reply, then proceed.
- **L**: several parts, or the architecture or the look is unsettled. Frame, settle decisions, slice.
- **XL**: rewrite, new system, or a program of features. As L, and read `skill://nstack-design` first.

If you were given a brief (subagent or worker), the brief is your frame: build to its shape and contracts and do not re-scope it. A decision only Nate can make goes under "Needs Nate" in your report, with your recommendation; carry on with everything else.

## 2. Frame (M and up)
At most eight short lines:
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
- `[mine]`: reversible choices. Take the boring default; report it only if it changes what Nate sees or a real tradeoff.
- **Taste** (visual, motion, audio, UX, naming, voice): preview anything new or unsettled before building it at scale (rendered frame, screenshot, mock, variants side by side) and build exactly his pick. A pick or reference he already gave stands; copy fixes and applying an approved style need no preview. Never judge his taste for him.
- Never ask permission for something he asked for. Never add caps, limits or approval gates of your own.

## 4. Slice and build
- L and XL work is a sequence of slices. Each slice ends in something Nate can see on his surface, with its check. First slice: the thinnest end-to-end path at full quality, riskiest unknown first. Run the slices back to back unless a check fails or a new `[Nate]` decision appears.
- One author for code that shares files. Parallel writers only on disjoint files, each with its own check.
- Long work keeps one ledger, `local/nstack/<slug>.md` (keep `local/` out of git) or `local://<slug>.md`: the frame, decisions, slice checklist with checks, and an append-only log. It is the only status file. Resume from it; never redo what it records.

## 5. Delegate only when it pays
Fan-out repeats context and adds coordination (one measurement: 2.6 to 5.9 times the input tokens for the same work). Nate's sessions with 20 or more subagents took about 55% of his spend and scored lowest. Delegate only:
1. bulk reading, extraction, summarizing or research lanes, to a cheap model (muse), returning compressed results;
2. a slice with disjoint files and its own check, to one owner with a fresh context;
3. one independent review of a prototype or diff that is a one-way door, risky (security, data loss, money, migration), or requested, by a different model family.

Never: two writers on the same files, reviews of reviews, QA or simulator sweeps beyond the slice's check, research waves for what code, a quick run or one lookup can answer. A decision that needs outside evidence gets a wide wave through `skill://research`; lanes cost cents and nearly all get used.

A brief carries the outcome, Nate's words, owned scope, the shape and contracts it must honor, keeps, the checks that define done (and an instruction to run them), facts already verified, and `Read skill://nstack`. Under a page. You own what comes back: inspect the diff or artifact yourself; never forward a summary.

Read and map the code you change yourself, and only what the change needs. At each slice boundary, update the ledger so a compaction or a fresh session resumes without rereading finished work. Stay the author through compaction; hand a slice to a fresh owner only when it is independently owned (case 2).

## 6. Prove it on his surface
Done means the outcome works where Nate will use it: his phone, the real app after restart or update, the real CLI, real data. Tests and simulators support that and never replace it. Never edit a test, fixture, snapshot or check to make it pass. When infrastructure misbehaves (pods, gateways, leases, credentials, caches), check it before changing code. If you could not prove something on his surface, say exactly that.

## 7. Report
First line: the outcome and whether the done-checks hold. Then the evidence. Then **Needs Nate**: only decisions he alone can make, each with your recommendation. Then any default you chose that changes what he sees, one line each. No restated plans, status essays or internal ids.

## 8. Keep process honest
Write only what someone will act on: code, checks, the ledger, updates to docs and changelogs the change made wrong, new docs only when asked. If two turns pass without touching the real artifact, do the smallest real step now. When Nate corrects a preference or a repeated mistake, record it once where it loads next time (the project's AGENTS.md, Dross's standing notes) or turn it into a check.
