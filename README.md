# nstack

How Nate's software gets built, for omp sessions and for Dross's workers. Size the ask, settle the facts and decisions that change the result, design the simplest correct shape, show taste before building it, prove each slice on Nate's real surface, and spend agents, reviews and tests in proportion to what they change. The rules come from his picks on the v3 rewrite audit (2026-10-19); the earlier evidence is in [audit/REPORT.md](audit/REPORT.md).

## Using it

Nothing to invoke. A short floor of standing rules rides on every request in every omp session and subagent. The agent reads `skill://nstack` itself before features and multi-step work (it holds the process, including agents, reviews and reports), `skill://nstack-design` for new systems, rewrites and unsettled architecture or look, `skill://nstack-verify` when proof needs more than the project's tests or rests on a number, and `skill://nstack-review` when reviewing. Builder subagents start with nstack loaded, and Dross's workers read it from disk.

| Command | Does |
|---|---|
| `/nstack <task>` | runs the task with the full process; use it when a session runs at lower effort or treats a real feature as a quick fix |
| `/nstack shape <ask>` | requirements, architecture with what forces each part, slices and checks, plus one batch of questions; builds nothing |
| `/nstack review` | reviews the current change against the ask, each finding with a failing case |
| `/nstack verify` | proves the current work on the real surface with every check that can see a failure, and vets any measured number |
| `/nstack correct <mistake>` | for a mistake that keeps coming back: finds every past instance and fixes it in structure (architecture, a type, a check whose error names the fix), proven against a real past instance |
| `/bro catch me up` | catches up on everything since the last message |
| `/bro` | re-explains the last reply plainly; `/bro how/why <thing>` explains how or why something works, grounded in the code and its history |
| `/improve <prompt>` | before running a prompt: names the practitioner best at the task, what they would do that the prompt does not ask for, the rawest material they would start from, their methods and tools, and an outside check that could show the result wrong, then rewrites the prompt to ask for exactly that (same goal, not more scope); with no prompt it takes the last request |

A one-shot lands when the ask carries the outcome in Nate's words, where he will check it (phone, the Mac app after restart, the CLI), what must not change, and references for anything visual (or "show me directions"). For a long run, give a finish condition that can pass or fail; a duration is not one. For a bug, describe what you see rather than your theory of the cause, so the agent looks everywhere first. Races and extra critics run only when asked for by name ("race opus and astra on this", "two critics"). The agent asks one batch of questions up front with a default for each and keeps running agents moving while it waits. Anything he says explicitly overrides nstack: models, number of agents, skipping a preview. Long work keeps a ledger at `local/nstack/<slug>.md` in the project, and a new session resumes from it ("continue <thing>" or `/bro catch me up`).

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
| `roster.toml` | `~/.omp/agent/agents/<name>.md` for every roster agent and the "Subagent routing" section of `~/.omp/agent/AGENTS.md` | every omp session and subagent |
| `agents/*.md` | bodies of the generated agent files: `author.md` for builders (load `skill://nstack`; spawn only readers and research workers unless the brief grants more), `reader.md` for bulk readers (no spawning), `researcher.md` and `verifier.md` for research lanes | subagents |
| `skills/nstack` | `skill://nstack` | any build: sizing, framing, decisions, agents, reviews, tests, reports |
| `skills/nstack-design` | `skill://nstack-design` | rewrites, new systems, programs of features; `design` workers |
| `skills/nstack-review`, `-verify` | `skill://…` | reviews and critic verdicts; proof beyond the project's tests and number vetting; `/nstack` modes |
| `commands/nstack.md` | `/nstack <task> \| shape <ask> \| review \| verify \| correct <mistake>` | omp |
| `commands/bro.md` | `/bro [catch me up]` | omp |
| `commands/improve/index.ts` | `/improve <prompt>` (a TypeScript command, so the prompt arrives verbatim; markdown commands drop its quote marks) | omp |
| `extensions/nstack-guard.ts` | omp extension | the rules prose did not hold in v3, as one-line notes where they fire: the lead writing to a critic that already reported (reviews close at their verdict) or a builder messaging one; a long brief to an agent that already exists, and "finish and report" to a subagent past 250K tokens of context; an `ask` while agents run (omp's `ask.timeout` bounds the wait itself); after compaction, a pointer back to the ledger and the skill |
| `audit/scripts/` | — | the extraction and metrics behind the report; `metrics.py --since <date> [--until <date>]` measures the sessions in a window, including the control indicators (briefs spawned twice, subagents that never ran, build agents spawned by subagents); `research_scaling.py` measures what research lanes add |

Dross's workers run omp with Nate's own setup, so the `omp-rules.md` block and the skills reach every worker, and Context opens each worker's first prompt with a line to read `skill://nstack`. Keep `omp-rules.md` under 2,000 characters and each skill under 12,000; `install.py --check` enforces both.

## Credits

Built on ideas from [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT): the multi-agent control now in `skills/nstack` §4 (from its orchestrate, swarm and interrogate material), the measurement checks (benchmark-checklist, explain-the-number, hillclimb), the verify script (create-verification-skill), the debugging rules (bug-fix, attack-the-premise, fix-root-causes), the safety-fact review step (blast-radius) and `/nstack correct` (correct), each adapted to omp, Dross and Nate's logs. Also the no-process-porn skill from [helix](https://github.com/DocumentDrivenDX/helix).
