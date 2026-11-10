---
name: nstack-verify
description: Prove work is done where Nate will use it, and vet numbers before they count. Read when the proof needs more than the project's tests (a phone or Mac app, a deploy, a render, real data), before reporting or acting on a speed, metric, eval or cost number, and when speed is the goal of the work.
---

# nstack verify

A check proves only what it can see: a fix can pass its tests and still be broken where he uses it: on the device, in the installed command, on his data.

## Instruments, cheapest first
1. Typecheck and the targeted tests that can see the change fail.
2. The real thing: start the app, CLI, service or pipeline and drive the changed path with real inputs.
3. His surface after the real update path (restart, OTA, reinstall, reload), or the real file he will open. If you cannot reach it, say so and hand him the one action that lets him check.
4. A physical device or the bench only for what nothing else shows (push, haptics, frame timing, a motor under load, a signal on a board).

Match the check to the change: a command change runs the real command; a screen change walks the changed flow in the running app; a parser, importer or migration replays a saved input; a speed change compares before and after on the same input; a storage change reads back what was written; a document or figure is opened as rendered.

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

## Speed loop
When speed is the goal, run it as a loop on one number:
1. The number: time or throughput on the path he waits on, from his real use where the project records it (its traces, metrics or logs), otherwise timed around that path on real inputs. OpenTelemetry only where the project already exports it or a request crosses processes; a single process needs its profiler and timers.
2. Each step: name the limiter from a profile, make one change, measure both sides as in Numbers 4, then keep it or revert it. Each step is one ledger row: the change, before, after, kept or reverted.
3. Stop at his target, or when the last few steps stay inside the spread, and report where the remaining time goes.

## Evidence
Each done-check with its proof: the command and output, a screenshot or file path, a URL. Anything unproven is **not verified on <surface>**, with what would verify it. A surface that will be checked again and has no scripted way in gets a small verify script (launch from clean, drive the real path, capture state, clean up), named in the project's AGENTS.md.
