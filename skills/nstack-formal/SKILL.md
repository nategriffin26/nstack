---
name: nstack-formal
description: Formal verification on request. Finds the promise in a repo where a bug costs most and tests reach least, checks it with a model checker or verifier, and leaves a project skill that reruns the check with one command; or brings an existing formal check back in line with code that changed. Read when Nate asks to formally verify, model-check or prove code (`/nstack formal`), or asks whether a formal check still matches the code.
---

# nstack formal

A test checks the cases someone thought to write. Formal verification checks every case in a stated scope: every order of steps in a model, every input up to a bound, or every input. Its weak point is the gap between the model and the code. A model an agent wrote from reading the code can drop a path or assume an order the code never promises, then pass while the code is broken. Most of what follows exists to keep that gap closed.

Two passes: **create** (no formal check exists, or Nate names a new target) and **maintain** (one exists and the code moved under it).

## Create

### Target
Answer from the code; ask Nate only what you cannot observe. If he named an area or a bug, start there. Choose a promise the code makes where a break harms him and tests rarely reach the case that breaks it: overlapping retries, a lease that expires mid-write, a state change that arrives out of order, a crash between two writes. Take the strongest such target, not the easiest to verify. One property per run. Check a promise the code or its docs state; where it is unclear what the code should promise, list that for Nate as a question rather than guessing a property.

### Tool
Pick the tool that answers the question at the lowest cost. Whether events can happen in a bad order suits a model checker over a small model of the design; TLA+ with TLC is the default for that in any language. Whether the code itself behaves for every input (memory safety, overflow, a data-structure invariant) suits a verifier that runs on the code, such as Kani for Rust. If no verifier runs on the language, say so and test the real code with generated inputs, not a hand model of the function. A property that must hold at every size, where a bound is not enough, can need a proof. Pin the tool by version and checksum (some release tags are republished), have the repo's own command fetch or find it (downloads cached under a gitignored path), and say why you chose it.

### What makes it good
- **True to the code.** Every action, variable and branch in the model points to a file and function a reviewer can open. What the model treats as one indivisible step is one indivisible step in the code (one statement, one transaction, one lock hold, one synchronous run of an event loop up to an `await`); anything else is split. Names come from the repo.
- **Able to fail.** A check never seen failing proves nothing; see Prove it, below.
- **Findings stay findings.** When the current code breaks the property, report the counterexample as steps in the code's words. Never weaken the property or the model until it passes, and never change product code in this pass; the fix is Nate's scope call. A checker stops at the first counterexample, so a red check cannot see a new break of the same property: give the finding its own config and keep the main check green on everything else.
- **Honest about scope.** Say what is verified, under which bounds and assumptions, and what is left out. List every fairness assumption (timers keep firing, calls finish, messages arrive): an "eventually" property rests on them, and one that is too strong assumes the bug away. A pass covers the model and its bounds, not the system.
- **Readable without the tool.** The property and the harm in one plain sentence each.
- **Cheap to rerun.** One command and a run of seconds to a minute, so the next agent runs it on every relevant change. A rerun is a local process and spends no model tokens. Get there by abstraction, not by dropping behavior: model what the code compares (a newer-than check as a flag, not raw counters), bound faults with one shared budget, and use the checker's cheaper modes (TLC's `-lncheck final`).
- **Kept in step.** Record which files and functions each check covers, and the commit at which the model was last confirmed to describe them.

### The project skill
Model, config and runner live in the repo (for example `formal/`). Write `.omp/skills/<area>-formal/SKILL.md` with frontmatter that names the area and says when to use it: any change to the covered code. Without frontmatter it never loads. From that skill alone, an agent who reads it cold mid-change must be able to:
- tell whether a change touches the verified code (the coverage list: each model action and variable beside the file and function it stands for);
- run the check with one command and read the result;
- tell a real bug from a modeling error: replay the counterexample against the code, and a step the code cannot take means the model is wrong;
- update the model when a change is intended, and move the sync commit forward only after confirming the model describes the code at the new commit.

It also states the property, the harm, the bounds and assumptions, and what is not covered. Use the repo's real commands, paths and nouns; no placeholders. Committed files carry repo-relative paths only, with no machine paths, hostnames or personal data, since the repo may be public.

### Prove it before handing off
Follow the project skill once, as the next agent would, on a scratch change that breaks the property in the real code. Make scratch changes in a worktree when the checkout is live (a CLI or service installed from it). The check must catch the break. Drop the scratch change and confirm the check is back where it started: passing, or failing only on the findings you report. If the skill misses the break or a step does not run, fix the skill or the model, not the scratch change. Commit the verification on its own, apart from any product change.

## Maintain
For changes that skipped the project skill: merges, edits made without it, drift across many commits. A stale model that still passes is the dangerous case, because it looks like proof. Edit only the verification (models, harnesses, properties, the project skill); never product code unless Nate asks.

1. **Find the checks** by what they do: a project skill that runs a model checker, prover or verifier against named code. Collect each one's property, covered code, bounds, command and sync commit. With no sync commit recorded, use the last commit that changed the verification files and say so. With no check at all, run create instead.
2. **Run each as it is** and record the result. A pass says only that the old description still holds; do not judge a failure until step 5.
3. **Read every change to covered code** from the sync commit on, with its commit message, including covered code that was moved, renamed or split, and new code that writes the guarded state. Judge each change against the model, not the message:
   - **no effect** on anything the model describes;
   - **the model no longer describes the code**: a step became two, a branch was added or removed, a check moved, a new path reaches the guarded state, a value has a new range;
   - **the promise changed on purpose**, with evidence in the change (doc comment, tests, changelog, commit message);
   - **the promise may be broken**: the code changed and nothing says the promise did.
4. **Update from the code, not from the result.** Write the model change from the code before rerunning, never shaped by what makes it pass. Change a property only for a promise that changed on purpose, recording old wording, new wording and the evidence. Keep the bounds; a reduced bound goes in the report.
5. **Rerun and judge.** A pass: break the new code the way the property guards against, confirm the check catches it, drop the break. A failure: replay the counterexample against the code step by step. A step the code cannot take means the model is wrong; fix it and say what was wrong. Every step possible means a bug; name the commit that introduced it. A cheap repro against the real code goes in the report as evidence, not into product code.
6. **Update the project skill**: coverage, command, bounds, assumptions and the sync commit, which stays put for a blocked check. Follow it once as the next agent would.

Each check ends **in sync**, **updated**, **bug** (the model describes the code and the code breaks the property) or **blocked** (say exactly why); updated and bug can both hold. A check that passed before the update and fails after it was passing on a stale description; say so.

## Report
Plain words, for Nate on a phone:
- what was verified and the harm it guards against, the tool and why, the bounds and assumptions;
- each finding as a short sequence of steps in the code's words, its harm in one sentence, and the evidence (counterexample, repro);
- for maintain, each check's outcome, the commits read, and every failure named as drift in the model or a bug in the code;
- the command that reruns it, how long it takes, and the break that showed it can fail;
- what it does not cover; a second target only if you found a close one.
