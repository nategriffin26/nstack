---
name: nstack-verify
description: Prove work is done where Nate will use it, and vet numbers before they count. Read when the proof needs more than the project's tests (a phone or Mac app, a deploy, a render, real data) and before reporting or acting on a speed, metric, eval or cost number.
---

# nstack verify

A check proves only what it can see: a fix can pass its tests and still be broken on his phone, his app or his data.

## Instruments, cheapest first
1. Typecheck and the targeted tests that can see the change fail.
2. The real thing: start the app, CLI, service or pipeline and drive the changed path with real inputs.
3. His surface after the real update path (restart, OTA, reinstall, reload), or the real file he will open. If you cannot reach it, say so and hand him the one action that lets him check.
4. Physical devices only for what nothing else shows (push, haptics, frame timing).

Look at every screen or output the change touches, in each state, beside his pick, and fix visible defects before he sees them; the taste verdict is his.

## Integrity
- Never edit a test, fixture, snapshot or verifier to make it pass; if the check is wrong, change it on its own and say so.
- When something looks broken, rule out the observer (your polling, a stale build, the wrong target), stale state and infrastructure before changing code.
- Watch long jobs by progress and errors, not only exit.

## Numbers
Before a number decides anything:
1. Did the work happen on the intended input? Count errors, skipped and cached work; a speedup that comes with more errors is failing faster, not running faster.
2. What else could it measure (the wrong input, a warm cache, a no-op, leakage)? Rule each out.
3. For speed, name the limiter from a profile or counters, not from reading code.
4. If it varies run to run and decides between close options, repeat both sides and report median and range; a gap inside the spread is no difference, and a change made only for speed that shows none is reverted. A number that decides nothing needs only 1 and 2.
5. State the end-to-end effect on what Nate waits on or sees.

## Evidence
Each done-check with its proof: the command and output, a screenshot or file path, a URL. Anything unproven is **not verified on <surface>**, with what would verify it. A surface that will be checked again and has no scripted way in gets a small verify script (launch from clean, drive the real path, capture state, clean up), named in the project's AGENTS.md.
