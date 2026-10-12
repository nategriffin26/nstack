---
name: nstack-verify
description: Prove that work does what Nate asked, on the surface where he will use it, with the smallest set of checks that can actually see the failure. Use when verifying a change, deciding what "done" needs, or for Dross verify tasks.
disable-model-invocation: true
---

# nstack verify

Done means the outcome works where Nate will use it. A recurring correction in his logs is a reported fix that was not fixed on his phone, his app or his real data. Tests and simulators support the proof; they never replace it.

## Pick the instrument that can see the failure
1. **Cheap checks first**: typecheck and the targeted tests for the code you touched, when they can see the changed failure.
2. **Run the real thing**: start the app, CLI, service or pipeline and exercise the changed path with real inputs.
3. **His surface**: the phone or Mac app after the actual update path (restart, OTA, reinstall, reload), the deployed service, the real file or output he will open. If you cannot reach it, say so and hand him the one action that lets him check.
4. **Physical only for what nothing else shows**: real push, haptics, keyboard feel, frame timing, hardware.

Visual, audio and taste quality is Nate's call. Put the screenshot, clip, render or file in front of him; do not grade it with a metric or your own eye and call it done. Measured numbers get explained: what limits them, and proof they measured the work you think.

## Minimal time set
Run the smallest set of checks that proves the done-checks. No full matrices, sweeps or repeated suites after the change is proven, and none after Nate says he will check it himself. A check that cannot fail is not a check.

## Integrity
- Never edit a test, fixture, snapshot, golden file or verifier to make it pass. Fix the product, or prove the check is wrong and change it on its own, saying so.
- When a change touches tests and the code they judge together, say so in the report.
- When infrastructure misbehaves (pods, gateways, leases, credentials, caches, stale builds), check it before changing code. Confirm what is actually running before diagnosing it.
- Watch long jobs by their progress and errors, not only their exit, so nothing fails silently.

## Evidence
Report each done-check with its proof: the command and the relevant output, the screenshot or file path, or the URL. Mark anything unproven as **not verified on <surface>** and name what would verify it. The first line of the report states whether every done-check holds.

## Make it repeatable
Use existing tools or one manual run on the real surface first. Add a small script that drives the surface only when the assignment calls for it or the proof cannot be had otherwise; never a document describing how to check.
