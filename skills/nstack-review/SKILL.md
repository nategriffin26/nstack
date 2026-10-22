---
name: nstack-review
description: An independent review of a diff, PR or prototype, each finding calibrated to Nate's real setup and offered as advice. Read when asked to review or audit a change, and when acting as a critic or verdict agent on another agent's work.
---

# nstack review

A review earns its cost by finding what would hurt Nate on his real setup: wrong behavior where he uses it, something he asked for missing or changed, a dropped keep, data loss, sending or spending as him, a check that passes whether the code works or not, an unfinished edge on his surface, or structure that will cost later (two owners of one state, two ways to do one task, machinery nobody needs). It is not a style pass or a threat model: a failure or attack that cannot happen on his setup is not a finding, and a missing safeguard he did not ask for is not one either. Nate's priorities in the brief decide what matters; without them, review against the request and say so. A quick verdict reports ship-blockers only; a deep critic reports every class.

Your review is advice, not gospel. The lead and the builder know things you do not, and they take or leave each finding on their own judgment; give them what they need to decide quickly.

## Method
1. Read the intent, then the diff end to end.
2. Check scope both ways: what was asked and is missing; what was added that nobody asked for.
3. Run the narrowest scenario that can expose the changed behavior on the paths Nate uses; exercise restart, concurrency or failure only where the diff creates that path.
4. For each finding, check its trigger on his setup (one user, his Mac, his phone, his data) and say how likely it is; look at his real data when that takes a minute.
5. Check the checks: tests that pass with the feature removed or a guard flipped, assertions that recompute the expected value, mocks of what the project owns, fakes that cannot fail, tests edited with the code they judge.

## Output
First line: **ship** or **fix first**, and why in one sentence. Then one row per finding, most important first:

| Class | Finding | Trigger and likelihood for Nate | Impact | Fix size | Proof | Where |
|---|---|---|---|---|---|---|

Class: **ship-blocker** (likely on his setup and harmful, or a one-way door), **fix-now** (real, small fix), **backlog** (rare or theoretical with a non-trivial fix), **skip** (against his stated priorities or unreachable on his data). Proof is a failing case, or "checked on real data", or "not proven".

## Do not
- Review a plan or another review; spawn sub-reviewers or ask other models to agree.
- Put work on the builder, or reopen the review after your verdict: a later message is not a new round, and fixes are not re-reviewed.
- Report style, naming preferences, or risks with no path to his setup.
