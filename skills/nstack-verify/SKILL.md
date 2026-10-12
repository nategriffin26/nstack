---
name: nstack-verify
description: Prove that work does what Nate asked, finished and on the surface where he will use it, with every check that can see a failure and none that can't, and vet any number before it is reported or acted on. Use when verifying a change, deciding what "done" needs, measuring speed, metrics or eval results, or for Dross verify tasks.
disable-model-invocation: true
---

# nstack verify

Done means the outcome works where Nate will use it. A recurring correction in his logs is a reported fix that was not fixed on his phone, his app or his real data. Tests and simulators support the proof; they never replace it.

## Pick the instrument that can see the failure
1. **Cheap checks first**: typecheck and the targeted tests that can see the changed failure; before calling it done, the project's required checks (what it runs before merge), so nothing else broke.
2. **Run the real thing**: start the app, CLI, service or pipeline and exercise the changed path with real inputs.
3. **His surface**: the phone or Mac app after the actual update path (restart, OTA, reinstall, reload), the deployed service, the real file or output he will open. If you cannot reach it, say so and hand him the one action that lets him check.
4. **Physical only for what nothing else shows**: real push, haptics, keyboard feel, frame timing, hardware.

**Taste is Nate's call; craft is yours.** Look at every screen, frame or sound the change touches on the real surface, in each state it can be in, beside the reference he picked, and fix visible defects (alignment, spacing, clipping, contrast, jank, timing, artifacts, levels) before showing him. Then put the screenshot, clip, render or file in front of him; never claim a taste verdict from a metric or your own eye.

## Checks that can see the failure
Run every check that can see a failure in what changed or what it touches. Skip only what cannot: sweeps or matrices beyond the change, re-runs of what already passed on the same code, and QA after Nate says he will check it himself. A check that cannot fail is not a check.

## Integrity
- Never edit a test, fixture, snapshot, golden file or verifier to make it pass. Fix the product, or prove the check is wrong and change it on its own, saying so.
- When a change touches tests and the code they judge together, say so in the report.
- When something looks broken, rule out the observer first (your polling, a stale build, the wrong target, input or reference), then infrastructure (pods, gateways, leases, credentials, caches) and stale state (config, locks, a process needing restart), before changing code. Confirm what is actually running before diagnosing it.
- Watch long jobs by their progress and errors, not only their exit, so nothing fails silently.

## Numbers
A number you report, compare or act on (a speedup, a latency, an eval or quality score, a training or identity metric, a count, a cost) is a claim about a run. Before anything rides on it:
1. **Did the work happen?** The measured region did the real work on the intended input: the request reached the server, the rows were written, the model saw the right clip, the result was used. Count errors and wrong outputs; failures, cached and skipped work are fast.
2. **What else could it measure?** List the alternatives (the wrong input or reference, a cache or warm state the claim doesn't intend, a no-op, code that never ran, look-ahead or leakage, a side left on defaults) and rule each out with evidence.
3. **What limits it?** For speed and throughput, name the limiter (a core, a lock, the disk, the network, the GPU, the load generator) from a profile or counters taken during a run, not from reading code; a result past a physical limit measured something else. For a score or metric, show it separates a known good case from a known bad one.
4. **Does it reproduce?** For anything that varies run to run, repeat each side enough to see the spread: about five alternating runs when runs are cheap; for costly ones (GPU jobs, long renders) as many as the decision needs, stated. Same versions, data, settings and warmth on both sides; report the median and range. A gap inside the spread is no difference, and a single run of a noisy measurement says so and doesn't decide between close options. A deterministic count or a recorded cost needs only 1 and 2.
5. **Does it matter?** Report the end-to-end effect on what Nate waits on or sees beside any micro result. A metric that disagrees with his eye is the metric's failure: say so and fix the metric before optimizing it; never optimize a proxy for his taste over his eye.

Verdict: better, worse, no measurable difference, or inconclusive, with the number, its unit, runs, range and limiter where they apply. Inconclusive when a side ran untuned or question 1 or 2 is open.

Sustained work on one metric: first freeze a harness proven to tell the bad case from the good, with a baseline and the regression checks green. Then one change per measurement: keep it only if it beats the spread with the checks green, revert it otherwise, and log every attempt (hypothesis, before, after, kept or reverted) in the ledger. Re-measure the combination of kept changes. A run of many hours schedules fork-and-flush rounds (`skill://nstack-agents`): one long run settles into one family of ideas. Stop at the target, never by relaxing it.

## Evidence
Report each done-check with its proof: the command and the relevant output, the screenshot or file path, or the URL. Mark anything unproven as **not verified on <surface>** and name what would verify it. The first line of the report states whether every done-check holds.

## Make it repeatable
Use existing tools or one manual run on the real surface first. When a project's surface will be verified again and has no scripted way in, build a small verify script in the repo, starting with the journey you are checking, that a cold agent can run: launch from a clean state (ready means usable, not just a process answering), doctor (right build, account, data and port), drive the real user path by stable handles, capture the action, the resulting state and side effects, and clean up only what it started while the evidence survives. Prove it once end to end and name its command in the project's AGENTS.md; a step no script can drive gets one line there with the exact commands. Never a document in place of running the check.
