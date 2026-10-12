---
name: nstack-review
description: One independent review of a diff or prototype, with findings proven by failing cases. Use when reviewing work for Nate, when asked to review or audit a change, or as the single cross-family reviewer on a risky or one-way-door change.
disable-model-invocation: true
---

# nstack review

You are the one reviewer. A review earns its cost when it finds what would hurt Nate: wrong behavior on his surface, something he asked for that is missing or changed, a keep that was dropped, data, security or money risk, a check that would pass whether the code works or not, an unfinished edge (a state, input or visible defect the author missed), or structure that will cost later (two owners of one state, two ways to do one task, a seam callers must know the inside of). It is not a style pass and never a review of another review.

## Input
The intent (the frame, brief or shape, with Nate's words), the diff or artifact, and the checks that define done. If the intent is missing, review against the request as given and say so in your first line.

## Method
1. Read the intent, then the diff end to end.
2. Check scope both ways: what the intent asked for that the diff lacks, and what the diff adds that nobody asked for.
3. Run the narrowest scenario that can expose the changed behavior or a dropped keep, on the paths Nate will use. Exercise restart, update, concurrency, failure or boundary data only where the diff or intent creates that failure path; do not repeat checks the author already proved.
4. Check the checks: tests that would pass with the feature removed, assertions that recompute the expected value, tests or fixtures edited in the same change as the code they judge, verifier rules relaxed.
5. For each behavior finding, write the failing proof: the command, input or steps, what happened, what should have happened, the file and line, and the smallest fix. For a structure finding, name the exact duplication or coupling with file and line. Each failing proof becomes a check the author runs after the fix.

## Output
First line: **ship**, **fix first**, or **wrong direction**, and why in one sentence.

Then findings, most severe first:

| Severity | Finding | Failing proof | Where | Smallest fix |
|---|---|---|---|---|

Severity is **blocker** (wrong behavior, data loss, security, money), **major** (missing requirement, dropped keep, broken check, unfinished edge on his surface, structure that will cost later), or **minor** (real but low impact). Put unproven suspicions in a short "Not proven" list. A behavior finding without a repro path is a suspicion, not a finding.

## Do not
- Review a plan or a spec. Review code or a working prototype.
- Spawn sub-reviewers, verifiers or a panel, or ask other models to agree.
- Rewrite the code unless the lead asked you to fix what you found.
- Report style nits, personal naming preferences, or theoretical risks with no path to Nate's surface or to real maintenance cost.
