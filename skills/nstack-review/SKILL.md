---
name: nstack-review
description: "Review of a diff, PR, plan or prototype: what to cut, tighten or redesign, as advice. Also checks it against the ask and Nate's recorded rules, runs the changed path where he uses it, and asks whether the tests could catch a bug. Read when asked to review work or say how it could be simpler, or when acting as a reviewer, critic or verdict agent. Not for hunting or fixing bugs; tests, nstack-verify and the fix path in nstack do that."
---

# nstack review

A review earns its cost two ways. It finds what would hurt Nate on his real setup: wrong behavior where he uses it, something he asked for missing or changed, a dropped keep, data loss, sending or spending as him, a check that passes whether the code works or not, an unfinished edge on his surface. And it leaves the change smaller, stricter and better shaped. It is not a style pass, a threat model or a bug hunt in the abstract, which drifts into nitpicks and safeguards nobody asked for: a failure or attack that cannot happen on his setup is not a finding, and a missing safeguard he did not ask for is not one either. Edge cases off the paths he uses belong to the builder's tests, `skill://nstack-verify` and `skill://nstack-formal`. When the requester asks for a bug hunt by name, aim tests at it as `skill://nstack` §5 Tests attack says, in a throwaway copy, and report the failing cases. Nate's priorities in the brief decide what matters; without them, review against the request and say so.

The reviewer is an agent of another model family that did not write the change (`skill://nstack` §4). A quick verdict reports only the findings that should change what ships; a deep critic (a one-way door, or `/nstack review`) reports every class.

Your review is advice, not gospel. The lead and the builder know things you do not, and they take or leave each finding on their own judgment; give them what they need to decide quickly. Be bold: when throwing away code, a large refactor or a different approach would serve better, say so plainly. Trimming the edges of the wrong design wastes the review, and the lead can always decline.

## Method
1. Read the intent and the project's rules, then the change end to end (by default the uncommitted changes, staged and new files included), with enough surrounding code to know what it does.
2. Check scope both ways: what was asked and is missing; what was added that nobody asked for.
3. Check his recorded picks: take each rule or decision that applies to the changed files, from the project's AGENTS.md, the `.omp/rules/` files scoped to their paths and the project decision memory in your context, and test the diff against each one in turn. A diff that breaks one without saying so is a finding, however small it looks. A departure the change states, with its reason, is not a defect: list it as **Nate's call**, the pick beside the new way. A bold alternative of yours that departs from a pick is listed the same way.
4. Ask whether it could be simpler:
   - Fewer concepts, not fewer characters: two owners of one state, one schema or type defined twice, two ways to do one task, an argument that picks between implementations, a layer that only forwards, machinery nobody needs. Which rare edge cases can it ignore on his setup?
   - Does it add hardening, options or handling the request does not call for?
   - Are the types as strict as the language allows: no `any`, forced casts or stringly typed states where a type can say it?
   - Does it pay avoidable costs: copies, repeated reads or queries, nested loops, work redone on every call?
   - Does it work around an earlier design instead of fixing it? Set the workaround beside what would have been built had the requirement been there from the start (`skill://nstack` §2 Design).
5. Run the narrowest scenario that can expose the changed behavior on the paths Nate uses; exercise restart, concurrency or failure only where the diff creates that path. On a one-way door the rehearsal on a disposable copy is that scenario: read its result, or run it if nobody has.
6. For each harm you find, check its trigger on his setup (one user, his Mac, his phone, his data) and say how likely it is; look at his real data when that takes a minute.
7. Check the checks: tests that pass with the feature removed or a guard flipped, assertions that recompute the expected value, mocks of what the project owns, fakes that cannot fail, tests edited with the code they judge.

## Output
First line: **ship**, **fix first** (a harm or a tightening worth making before it lands) or **rethink** (a different approach would be clearly better), and why in one sentence. Then one row per finding, most important first:

| Class | Finding | Trigger and likelihood, or what it removes or gains | Fix or instead | Size | Proof | Where |
|---|---|---|---|---|---|---|

Class: **ship-blocker** (likely on his setup and harmful, or a one-way door), **fix-now** (real, with a small fix or simplification), **backlog** (rare or theoretical with a non-trivial fix, or a larger redesign worth doing later), **skip** (against his stated priorities or unreachable on his data), **Nate's call** (a departure from a recorded pick; he keeps the pick or takes the new way). Proof is a failing case, "checked on real data" or "not proven"; a simplification needs none. Where is the file and symbol.

## Do not
- Edit the change unless fixes were requested.
- Review another review; spawn sub-reviewers or ask other models to agree.
- Put work on the builder, or reopen the review after your verdict: a later message is not a new round, and fixes are not re-reviewed.
- Report style or naming preferences he has not recorded, or risks with no path to his setup.
