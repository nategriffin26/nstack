---
name: nstack-verify
description: "Prove work runs where Nate will use it, and audit numbers before they decide anything. Read when proof needs more than unit tests (phone or Mac app, deploy, render, real data), before reporting or acting on a speed, metric, eval, or cost number, or when speed is the goal."
---

# nstack verify

A check proves only what it can observe: code can pass its unit tests and still fail on the device, in the installed CLI, or on real data.

## Instruments, cheapest first

1. Typecheck and targeted tests that can fail when the change is broken.
2. The real program: start the app, CLI, service, or pipeline and drive the changed path on real inputs.
3. Nate's real surface after the real update path (restart, OTA, reinstall, reload), or the actual file he will open. If you cannot reach it, say so and give him the one step that verifies it.
4. Physical hardware or the bench only for what simulators cannot show (push notifications, haptics, frame timing, motors under load, board signals).

Match the check to the change: run the installed CLI for command changes; walk the running flow for UI changes; replay saved real inputs for parsers, importers, or migrations; compare before and after on identical inputs for speed work; read back persisted state for storage changes; open the rendered output for documents or figures.

Inspect every touched screen or output in every state beside Nate's pick and fix visible defects before he sees it; final taste stays with him.

## Integrity

- Never edit a test, fixture, snapshot, or verifier to make it pass. If a check itself is wrong, fix it explicitly on its own and say why.
- When something looks broken, rule out the observer (polling lag, stale build, wrong target), stale state, and infrastructure before changing product code.
- Monitor long-running jobs by progress and errors, not exit code alone.

## Auditing numbers

Before any speed, accuracy, eval, or cost number decides something:
1. Confirm the intended work actually ran: count errors, skipped items, and cache hits. Failing faster is not a speedup.
2. Rule out confounders: wrong input, warm cache, no-op path, or data leakage.
3. For speed work, identify the bottleneck from a profiler or counters—never by guessing from code.
4. When results vary run to run and decide between close options, repeat both sides and report median and range. A gap inside the spread is noise; revert any speed-only change that shows no real gain. (Informational numbers need only steps 1 and 2.)
5. State the end-to-end effect on what Nate waits on or sees.

## Speed loop

When speed is the goal, optimize one real number:
1. Pick the end-to-end time or throughput Nate waits on, measured from real traces/logs or timed on real inputs. Use OpenTelemetry only if the project already exports it or requests cross processes; single processes need a profiler and timers.
2. Each step: profile the bottleneck, make one change, measure both sides (Auditing numbers step 4), and keep or revert. Log one ledger row per step: change, before, after, kept or reverted.
3. Stop at the target, or once the last few steps stay inside the noise spread, and report where the remaining time goes.

## Evidence

Pair each done-check with its proof: command and output, screenshot or artifact path, or live URL. Label anything unreachable **not verified on `<surface>`** with the exact check that would prove it.

For a surface that will be checked repeatedly and lacks a scripted entry point, write a small verify script that launches cleanly, confirms the running build matches what you just built, drives the real path, saves evidence that outlives cleanup, and cleans up after itself. Run it once end to end and name it in the project's `AGENTS.md`.
