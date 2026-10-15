# nstack

How Nate's software gets built, for omp sessions and for Dross's workers. Size the ask, pin the facts and decisions that change the result, design the simplest shape that meets every requirement, show taste before building it, prove each slice on Nate's real surface, and run agents with control. The evidence behind every rule is in [audit/REPORT.md](audit/REPORT.md).

## Using it

Nothing to invoke. The standing rules ride on every request in every omp session and subagent. The agent reads `skill://nstack` itself before features and multi-step work (all 6 feature asks in a test at the default Opus max; quick fixes may skip it, as intended), `skill://nstack-design` for new systems, rewrites and unsettled architecture or look, `skill://nstack-agents` before it runs several agents, `skill://nstack-verify` when proof needs more than the project's tests or rests on a number, `skill://nstack-review` when reviewing, `skill://nstack-teach` for how and why questions, and `skill://nstack-writing` for catch-ups, reports that carry decisions, and docs. Builder subagents start with nstack loaded, and Dross's workers get it in their context pack.

| Command | Does |
|---|---|
| `/nstack <task>` | runs the task with the full process; use it when a session runs at lower effort or treats a real feature as a quick fix |
| `/nstack shape <ask>` | requirements, architecture with what forces each part, slices and checks, plus one batch of questions; builds nothing |
| `/nstack review` | reviews the current change against the ask, each finding with a failing case |
| `/nstack verify` | proves the current work on the real surface with every check that can see a failure, and vets any measured number |
| `/nstack correct <mistake>` | for a mistake that keeps coming back: finds every past instance and fixes it in structure (architecture, a type, a check whose error names the fix), proven against a real past instance |
| `/nstack catchup` or `/bro catch me up` | catches up on everything since the last message |
| `/bro` | re-explains the last reply plainly |
| `/improve <prompt>` | before running a prompt: names the practitioner best at the task, what they would do that the prompt does not ask for, the rawest material they would start from, their methods and tools, and an outside check that could show the result wrong, then rewrites the prompt to ask for exactly that (same goal, not more scope); with no prompt it takes the last request |
| `/skill:nstack-teach <question>` | explains how or why something works, grounded in the code |

A one-shot lands when the ask carries the outcome in Nate's words, where he will check it (phone, the Mac app after restart, the CLI), what must not change, and references for anything visual (or "show me directions"). For a long run, give a finish condition that can pass or fail; a duration is not one. For a bug, describe what you see rather than your theory of the cause, so the agent looks everywhere first. Multi-agent patterns can be asked for by name: "race opus and astra on this" (same brief, judged blind), "one worker per package" (a partition), "two critics" (independent reviews with different questions). The agent asks one batch of questions up front, only what he alone can decide, then does not stop again. Anything he says explicitly overrides nstack: models, number of agents, skipping a preview. Long work keeps a ledger at `local/nstack/<slug>.md` in the project, and a new session resumes from it ("continue <thing>" or `/nstack catchup`).

## Install

```sh
python3 install.py              # back up, then install (idempotent); ends with --check
python3 install.py --check      # verify links, generated files, rule blocks, skill sizes, roster models against omp's catalog, Context's contract and omp's config
python3 install.py --uninstall  # remove nstack and restore what the first install replaced
python3 install.py --no-dross   # leave Dross's home AGENTS.md alone (combines with the above)
```

The installed text points at `~/Projects/nstack`, so on another machine clone it there: `gh repo clone nategriffin26/nstack ~/Projects/nstack`.

The first install saved the pre-nstack state to `local/backups/baseline/` (with `manifest.json`); `--uninstall` restores from it and removes only what nstack generated or linked, so later edits elsewhere in the instruction files survive. Every install also writes a dated backup. Edit files here, not the installed copies: skills, commands and the extension are symlinks, and the agent files, the routing section and the two rule blocks are regenerated on each install. Prove a behavior change with a probe: a fresh omp session on an ordinary-looking task in a scratch repo, judged by what the agent actually read, ran and changed, not by what it says it followed.

## Changing models

Change models in **Context → Settings → Models**, or through Dross's `models` tool. One revisioned host policy owns the allowed-model list and one model/thinking choice for each Dross role, worker type and Mac model role. The page's Activity tab records who changed what and when. Reassign roles before disallowing a model they use.

`roster.toml` remains the only file in this repository that names models, but it is a **generated input**, not a second settings store. Context writes it and the managed model fields of `~/.omp/agent/config.yml`, then runs `python3 install.py --no-dross`. Do not hand-edit those fields or the installed agent files. For isolated projections, `--roster <path>` selects another roster and `--catalog <path>` supplies a previously discovered native catalog.

Every roster type is enabled and uses its own saved model and thinking level. Astra is an ordinary type assigned Sol; Researcher uses Muse. The installer renders agent files and the “Subagent routing” section of `~/.omp/agent/AGENTS.md`, checking models and thinking against omp's catalog. Context always uses `--no-dross`, leaving Dross's home `AGENTS.md` alone.

Mac roles share the policy; optional roles can use Native default. An interactive `/model` pick changes that session, not the policy. Native omp's explicit per-call model can override its type assignment. New Context workers use the current assignment; running processes continue normally, and native child preflight reloads global settings as usual.

Agent thinking choices use the levels that model offers, including `max` when supported. Native `task.maxEffort` separately caps a task's per-spawn `effort` hint; it does not restrict the saved model choice.

## Files

| File | Installed as | Reaches |
|---|---|---|
| `omp-rules.md` | marked block in `~/.omp/agent/RULES.md` | every omp session and subagent, always |
| `dross.md` | marked block in Context's home `AGENTS.md` (`$DROSS_HOME/home/AGENTS.md`, by default `~/.context-dross/home/AGENTS.md`) | Dross's main turn, read from disk on every turn |
| `roster.toml` | `~/.omp/agent/agents/<name>.md` for every roster agent, the "Subagent routing" section of `~/.omp/agent/AGENTS.md`, the worker-model line in Dross's block | every omp session, every subagent, Dross |
| `agents/*.md` | bodies of the generated agent files: `author.md` for builders (load `skill://nstack`; spawn only readers and research workers unless the brief grants more), `reader.md` for bulk readers (no spawning), `researcher.md` and `verifier.md` for research lanes | subagents |
| `skills/nstack` | `skill://nstack` | any build; Context's `implement` workers |
| `skills/nstack-design` | `skill://nstack-design` | rewrites, new systems, programs of features; `design` workers |
| `skills/nstack-agents` | `skill://nstack-agents` | any session or worker about to run several agents, a race, a partition or critics |
| `skills/nstack-review`, `-verify`, `-writing`, `-teach` | `skill://…` | reviews; proof beyond the project's tests and number vetting; catch-ups, decision reports and docs; how and why questions; `/nstack` modes; Context's `review`, `verify`, `writing`, `teach` workers |
| `commands/nstack.md` | `/nstack <task> \| shape <ask> \| catchup \| review \| verify \| correct <mistake>` | omp |
| `commands/bro.md` | `/bro [catch me up]` | omp |
| `commands/improve/index.ts` | `/improve <prompt>` (a TypeScript command, so the prompt arrives verbatim; markdown commands drop its quote marks) | omp |
| `extensions/nstack-guard.ts` | omp extension | one-line reminders, never blocking: a pointer to `skill://nstack-agents` the first time a session runs several build agents without a successful read of it, a note when a later call repeats a brief an earlier call spawned (race candidates spawned together are not flagged), a prompt to account for every agent at 12/24/48/96 build agents, and a note at 6/15/30/60 markdown files written |
| `audit/scripts/` | — | the extraction and metrics behind the report; `metrics.py --since <date> [--until <date>]` measures the sessions in a window, including the control indicators (briefs spawned twice, subagents that never ran, build agents spawned by subagents); `research_scaling.py` measures what research lanes add |

Dross's workers run omp with Nate's own setup, so the `omp-rules.md` block and the skills reach every worker, and Context opens each worker's first prompt with a line to read `skill://nstack` (the old `apps/core` contract and its 32k worker pack are gone since Context's rewrite to `apps/dross`). Keep each skill self-contained and under 12,000 characters (about 3k tokens); `install.py --check` enforces it.

## Credits

Built on ideas from [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT): the multi-agent control in `nstack-agents` (from its orchestrate, swarm, arena and interrogate material), the measurement checks (benchmark-checklist, explain-the-number, hillclimb), the verify script (create-verification-skill), the debugging rules (bug-fix, attack-the-premise, fix-root-causes), the safety-fact review step (blast-radius) and `/nstack correct` (correct), each adapted to omp, Dross and Nate's logs. Also the no-process-porn skill from [helix](https://github.com/DocumentDrivenDX/helix).
