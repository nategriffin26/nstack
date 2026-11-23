# Subagents, ledgers, reviews, and done-checks

Load this reference when coordinating multiple agents, running a multi-sitting build with a ledger, commissioning a review, or finishing a complex surface.

## Long work and ledgers

Work longer than one sitting keeps one ledger at `local/nstack/<slug>.md` (out of git). Keep only the **current state** in it, edited in place:
- frame (outcome, proof, keeps, out, verified facts)
- settled decisions
- slice checklist
- what is running now and its next action

Move finished detail and the chronological log to `<slug>.archive.md` before the ledger passes ~12 KB. Resume from the ledger; never redo what it records.

## Delegating to agents

Use subagents for genuinely independent slices, bulk reading, and parallel research; script repetition instead of spawning agents for it. Read everything the change touches yourself.

Before spawning builders:
1. Settle every shared dependency (interfaces, data shapes, files, names, done-checks) with shared contracts in code.
2. Give each module, branch, port, device, and data directory one owner.
3. Run a new kind of unit end to end once before fanning out more.

A brief is complete before it is short:
- Nate's outcome in his own words, and why
- exact inputs (paths, revisions, upstream results)
- owned scope and non-goals
- shared contracts and verified facts
- what is settled vs. left to the worker's judgment
- Nate's standing decisions verbatim (including no self-imposed deadlines, freezes, or change-size caps)
- done-checks and the evidence to return
- delegation grant (readers and research lanes only unless you grant more)

Never invent deadlines, checkpoints, time targets, change-size caps ("smallest fix"), partial drafts, or "X first, the rest later" in a brief.

Judge each unit by its commits and artifacts, never its self-report; inspect every diff yourself. A unit or loop that stops producing new evidence across its last few attempts is stalled: stop it, record why, test its premise, or re-brief it. A confirmed wrong premise updates every brief sharing it; a changed decision from Nate re-briefs every affected agent at once.

Reuse an agent while it is mid-task or idle under an hour; after an hour its cache is cold, so hand off to a fresh agent from the ledger unless only the old context holds what is needed. Unrelated work always gets a fresh agent. Races (2–4 attempts on one problem) and extra critics run only when Nate asks by name.

## Reviews

Review only core, important changes: shared contracts, data and state models, the main path Nate uses, or anything sending or spending as him. Routine slices rely on their tests.

- **Who reviews:** an agent of another model family when enabled in the roster; otherwise a fresh agent of the same family that did not write the change (note in the report that it was same-family).
- **Depth:** one quick verdict under `skill://nstack-review` for normal core work. For a one-way door, data migration, or cutover, run one deep critic carrying Nate's priorities verbatim, beside a live rehearsal (on a disposable copy of his data, or against a local server replaying recorded responses).
- **Closure:** a review closes at its verdict; fixes are not re-reviewed and are trusted once tests pass. Findings are advice: triage each in one line (`take`, `backlog`, or `skip`, and why) by likelihood and impact on Nate's setup against its cost. A critic never messages a builder or puts work on one; the lead decides.

## Finishing, craft, and tests

- **Finish every state** the change touches, plus edge inputs, copy, speed, and running cost:
  - Screen: empty, loading, error, offline, first run, stale data after a failed refresh.
  - Command, job, or pipeline: no input, bad input, second run, interrupted run, missing key or dependency, piped output.
  - Represent each state explicitly in an exhaustive switch with no catch-all default, so adding a state fails the build or type check until handled. An empty result is loaded data, not a loading state. Remove all debug output, dead code, and `TODO`s. Once it works, ask whether fewer concepts would do the same job.
- **Craft on the surface:** inspect every changed screen or output beside Nate's pick and fix defects he would notice before he sees it. Layouts hold still through async states (keep data visible while refreshing; show progress on the triggering control). Every permanent heading, control, and status line earns its space; each intent has one control. For multi-screen changes, list every state and its reaching path from code and capture them in one proof sheet. For CLIs and APIs, pick guessable names, actionable errors, and output that is clean for a person and parseable for a script.
- **Words:** cut every string he would not miss (eyebrow labels, subtitles restating titles, captions under numbers or controls, helper paragraphs, empty banners, noisy logs). Keep short labels, one unit, actionable errors, and comments that explain why. Runtime model text (lists, feeds, cards) follows `skill://nstack-writing`. Comments and docs describe the code as it is for a reader who never saw the chat.
- **Tests:** each test names the bug it catches and aims where code breaks (boundaries, empty/hostile input, failing dependencies, retries, concurrency). Hardcode expected values from the contract instead of recomputing them the way the code does. Use real project code and stores; fake only external boundaries (local replay servers for third-party APIs), with failure paths tested. Assert outcomes, stored state, and error kinds rather than internal calls. Give universal invariants property tests with printed, replayable seeds. Every test must be seen failing once before passing.
- **Upgrades and instruction changes:** run data upgrades on a disposable copy of real data and verify surviving values and relationships. Test changed prompts, skills, or routing rules on 1–2 real tasks in fresh sessions (the failure it fixes and one behavior it preserves), judged by what the agent did.
- **Test cadence:** builders run targeted tests and report runtime; run one full gate per landed batch and before deploy. A flaky test gets one retry, then its root cause fixed. Never edit a check to make it pass.
