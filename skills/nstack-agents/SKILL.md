---
name: nstack-agents
description: How to run subagents, swarms, races and critics so they improve the result. When agents add quality, which pattern fits, complete briefs that relay Nate's current decisions and exact inputs, one owner per file and resource, a pilot for an untried unit, every agent tracked to an evidenced result, continuous integration, and judging from artifacts. Read before spawning more than one build, design or review agent, or any swarm, race or panel.
---

# nstack agents

How agents are run matters more than how many. A worker starts blank: it knows only its brief, sees none of its siblings, and cannot ask what Nate meant. A wide run whose briefs carry his intent in full does as well as solo work at any width; partial briefs are where the cost goes and the quality drops. Runs fail in recognizable ways: the same brief spawned twice, a sibling or an old session editing the same tree, a decision (a provider, a model, a pick) lost on the way to a worker, the wrong input handed to an experiment, agents frozen in waits nobody noticed, integration left to the end, and review stacked on review. Runs that land have file-owned slices against a frozen contract, a probe or harness before spend, builder and critic split on real artifacts, independent first passes from different model families, and a lead that takes no agent's word. One owner stays accountable for the integrated result; everything below keeps that owner in control.

## 1. Decide the decomposition
Before spawning, write one line each in the ledger or your reply:
- **First**: what runs before any fan-out: Nate's scope pinned, the probe, the shared contract or scaffold.
- **Parallel**: units with disjoint files, data and resources.
- **Shared**: what more than one agent would write (a config, a branch, a simulator, a GPU node, a port, a data directory, a provider lease, billing). Split it so each agent owns its own, or serialize.
- **Shape**: the topology that fits the job and who integrates; if one agent is best, say why.

Agents add quality through parallel independent work, reading and research width, genuinely different attempts, and independent critics. Repetition is a script's job: do the first unit by hand, write the codemod or script, rerun it on that unit and diff, then let the script do the rest; agents can build and challenge the tool. Never spawn before the scope Nate must pick is pinned, or for what one read, lookup or quick run answers.

## 2. Pick the pattern
- **Slices**: one owner per slice with disjoint files and its own checks; you integrate each as it lands.
- **Partition**: one unit of coverage per worker (package, feature, source, host, subsystem), no overlaps. Each returns PASS, ISSUES or BLOCKED with evidence. A missing or empty result is a gap, never a pass: respawn it once, then report the gap.
- **Race**: the same brief to two to four models or approaches when one attempt would lock in a shape (an architecture, a hard algorithm, a prompt). Declare a three-to-six-point rubric first. A judge of another family scores the candidates blind by label while you read every one; take as base the one the next maintainer can extend most easily, and graft the best parts of the others by hand. Converging candidates confirm the shape. When they diverge, find the requirement or decision that splits them: a decision only Nate can make goes to him; an underspecified brief gets fixed and rerun.
- **First to qualify**: several hosts, providers or approaches started at once when any one that passes a declared check will do. Take the first that passes, then stop and release the rest at once.
- **Taste directions**: several models may each make a direction for Nate's pick (`skill://nstack` §3). Nobody judges or grafts them; he picks.
- **Critic**: an independent reviewer of another family on a real artifact (prototype, diff, run output, renders), returning findings with failing proofs and a verdict (`skill://nstack-review`). A second critic only when it asks a different question (correctness, maintainability, the real surface), run in parallel. Same-family pairs share blind spots, so their agreement proves little.
- **Research**: `skill://research` lanes on distinct questions after the scope is pinned; verifiers re-fetch the load-bearing claims.
- **Hypotheses**: for a metric, independent hypotheses in parallel, each isolated in its own worktree, output and hardware slot (or interleaved), compared to the same baseline on one frozen harness (`skill://nstack-verify`, Numbers). Re-measure the combination of kept changes.

## 3. Brief
Complete before short: the brief you would want to receive cold. A field you cannot fill is a unit you have not scoped yet.
- **Outcome**: one sentence a stranger could execute, with Nate's words, and the why: what the result feeds and the reason behind each constraint, so the worker can decide the cases the brief did not foresee.
- **Inputs**: the exact files, clips, datasets, revisions and upstream results it works from, pasted or pinned by path; workers cannot see their siblings, and "A is done" is not a handoff.
- **Scope**: what it may write (files, state, resources) and must not touch; its own worktree, branch or output directory when others run beside it.
- **Contract**: the shape and interfaces it must honor and the facts already verified.
- **Decisions**: what you settled (approach, interfaces, data shapes, files, names, what counts as done) and what is left to the worker, all inside its own unit. Anything a sibling or a later unit depends on is settled before the spawn, by you, a probe or Nate; work whose shape is still open is a design, probe or race task whose result you decide before briefing builders. Workers that each settle a shared shape on their own build halves that do not fit.
- **Standing**: Nate's current decisions that apply (models, providers, machines, picks, ways of working), from the ledger, in every spawn and re-spawn.
- **Done**: the finish condition as checks that pass or fail, and the evidence it returns (command output, screenshot, file path, commit).
- **Waits**: bounded. It never blocks indefinitely on another agent, a message or a job; when it cannot proceed, it reports what blocks it. There is no deadline on productive work.
- **Report**: status, what it ran and on which revision, evidence, deviations, any premise it found wrong (an input, a fact, the approach, a check that cannot pass honestly) instead of working around it, anything only Nate can decide.
- **Delegation**: readers and research lanes only, unless you grant more.

Size the brief to the unit: a one-command unit gets a paragraph that still names outcome, inputs, scope, check and report. Author agents load nstack themselves; a brief to any other builder adds `Read skill://nstack`.

## 4. Run
- **Pilot** an untried kind of unit, or a risky shared contract, end to end (brief, work, check on the real surface, integration) before spawning the rest of that kind: an untried brief is a guess, and a pilot turns it into a recipe before its mistakes are multiplied. Then fix the brief, the check and the unit size from what it showed. Units on a recipe already proven need no pilot.
- **Ownership**: one writer per file, branch, piece of state and resource. Simulators, devices, GPU nodes, ports and leases get one owner, who releases them when the unit is done or stopped. An earlier session or a sibling never edits the same tree.
- **Track** every unit in the ledger as running, passed, failed or blocked, with its artifact and the revision it was checked at. Judge progress by side effects (commits, files, logs, outputs), not silence. When results arrive, finish the edit in hand, reconcile each against its unit, integrate what is ready, and dispatch what is newly unblocked. Never wait on agents that already finished, and never start a second agent on a unit that is still running (a race starts its candidates on purpose, together).
- **Changed decisions**: when Nate changes one, update the ledger and stop or re-brief every running agent it affects at once; accept their output only after they reconcile.
- **Integrate continuously** from the first verified unit, with one named owner. Shared contracts live in code (types, schemas, golden files) before the first spawn. After each integration, re-run the checks and confirm earlier picks still hold; a pass on a worker's branch is not a pass on the integrated result.

## 5. Judge
- Inspect every diff, artifact or render yourself. A self-report is a claim, not proof.
- Each unit is VERIFIED, NOT VERIFIED or INCONCLUSIVE against its done-checks; inconclusive is not a pass.
- Critic findings: one with a failing proof or a concrete path to harm stands however many models raised it. Dismiss preference ("I would have done it differently") and hypotheticals the callers rule out, each with a one-line reason.
- Pushback is information. When a worker reports a wrong premise, check its evidence; if it holds, fix the brief and the ledger for every unit that shares the premise. Never re-spawn the same brief over it.
- A healthy owner with live state (uncommitted work, a running process) keeps its follow-up fixes. Replace an owner that failed, stalled or lost the thread with a fresh one carrying the original brief, every later decision and its partial results.

## Do not
- Run overlapping lanes, or repeat a wave because results were thin; fix the brief.
- Stack audits (audit, fix, re-audit, final audit). One critic pass per artifact, then the checks.
- Fan out agents to hand-apply what a script can do.
- Let workers spawn further unless their brief grants it.
