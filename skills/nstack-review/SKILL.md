---
name: nstack-review
description: "Review diffs, PRs, plans, or prototypes for harm on Nate's setup and what to cut, simplify, or redesign. Checks against the ask, recorded picks, and test quality, and runs the changed path where he uses it. Read when asked to review or simplify, or when acting as a critic. Not for hunting or fixing bugs; use tests, nstack-verify, and nstack Fixes."
---

# nstack review

A review earns its cost two ways: catching what would actually hurt Nate on his real setup (wrong behavior where he uses it, missing requirements, dropped keeps, data loss, unintended sends or spends, hollow tests, unfinished states), and leaving the change smaller, clearer, and better shaped.

This is not an abstract style pass, generic threat model, or theoretical bug hunt. Failures with no path to his setup and missing safeguards nobody asked for are not findings. Edge cases off his paths belong to tests, `skill://nstack-verify`, and `skill://nstack-formal` (unless the requester asks for a bug hunt by name).

Prefer a reviewer from another model family than the author. When no other family is enabled, run a fresh critic of the same family that did not write the change and note that in the report. A quick verdict reports only what should change what ships; a deep critic (one-way doors, data migrations, cutovers, or `/nstack review`) covers every class.

Your review is advice—the lead and builder know things you do not and take or leave each finding by judgment. Be bold: if throwing code away, redesigning, or taking a cleaner approach beats patching edges, say so plainly.

## Method

1. **Read end to end:** understand the intent, the project's rules, and the full change (default: uncommitted changes, staged and new files included) with enough surrounding code to see how it fits.
2. **Check scope both ways:** what was asked and is missing; what was added that nobody asked for.
3. **Check Nate's recorded picks:** test the diff against every rule or decision scoped to the changed files (project `AGENTS.md`, `.omp/rules/`, memory). An unexplained break is a finding. An intentional departure with a reason—or a stronger alternative you propose—is **Nate's call** (the old pick beside the new option).
4. **Push for simplicity and craft:** fewer concepts, not fewer characters (`skill://nstack` › Design). Look for rare edge cases that can be dropped on his setup, unasked-for hardening or options, loose types (`any`, forced casts, stringly typed states), avoidable work (extra copies, repeated queries), and patches around a broken design that a root fix or redesign would eliminate.
5. **Exercise the real path:** run the narrowest scenario that exposes the changed behavior where Nate uses it. Exercise restarts, concurrency, or failure only where the diff introduces that path. For one-way doors, migrations, or cutovers, inspect or run the rehearsal on a disposable copy.
6. **Ground every harm:** check each trigger against his real setup (single user, his Mac, his phone, his data) and state likelihood.
7. **Audit the tests:** catch tests that pass with the feature removed or a guard flipped, assertions that recompute the expected value the way the code does, mocks of project-owned code, fakes that cannot fail, or checks edited to make broken code pass.

## Output

First line: **ship**, **fix first** (a real harm or worthwhile simplification before landing), or **rethink** (a clearly better design exists), plus one sentence saying why. Then one row per finding, highest impact first:

| Class | Finding | Trigger and likelihood, or what it removes or gains | Fix or instead | Size | Proof | Where |
|---|---|---|---|---|---|---|

- **Class:** `ship-blocker` (likely and harmful on his setup, or a one-way door), `fix-now` (real issue or clean simplification), `backlog` (rare or larger redesign worth doing later), `skip` (unreachable or against his priorities), `Nate's call` (departure from a recorded pick).
- **Fix or instead:** name the root fix, not the smallest band-aid.
- **Proof:** a failing case, `"checked on real data"`, or `"not proven"` (simplifications need none).
- **Where:** exact file and symbol.

## Do not

- Edit the code unless fixes were requested.
- Review another review, spawn sub-reviewers, or poll other models for agreement.
- Assign work directly to a builder or reopen after the verdict; fixes are not re-reviewed.
- Report unrecorded style preferences or theoretical risks with no path to his setup.
