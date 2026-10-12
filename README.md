# nstack

How Nate's software gets built, for omp sessions and for Dross's workers. Size the ask, pin the facts and decisions that change the result, design the simplest shape that meets every requirement, show taste before building it, prove each slice on Nate's real surface, and delegate only when it pays. The evidence behind every rule is in [audit/REPORT.md](audit/REPORT.md).

## Install

```sh
python3 install.py              # back up, then install (idempotent); ends with --check
python3 install.py --check      # verify links, generated files, rule blocks, skill sizes, roster models against omp's catalog, Context's contract and omp's config
python3 install.py --uninstall  # remove nstack and restore what the first install replaced
python3 install.py --no-dross   # leave Dross's home AGENTS.md alone (combines with the above)
```

The installed text points at `~/Projects/nstack`, so on another machine clone it there: `gh repo clone nategriffin26/nstack ~/Projects/nstack`.

The first install saved the pre-nstack state to `local/backups/baseline/` (with `manifest.json`); `--uninstall` restores from it and removes only what nstack generated or linked, so later edits elsewhere in the instruction files survive. Every install also writes a dated backup. Edit files here, not the installed copies: skills, commands and the extension are symlinks, and the agent files, the routing section and the two rule blocks are regenerated on each install.

## Changing models

`roster.toml` is the only place that names models. It maps roles (default author, hard systems work, taste-critical work, fully specified implementation, bulk reading, research and verification lanes) to agents, and each agent to a model, family, default effort and an optional note.

- New version of a model (say Fable 5.5): change that agent's `model` and `label`.
- A model now beats another at a job: move its agent into that role's `agents` (first choice first). An agent in no role runs only when Nate names it.
- New model family: add an `[agents.<name>]` entry and put it in a role.

Then run `python3 install.py`. It refuses to write anything if a model isn't in omp's catalog (`omp models`), a default effort isn't one the model supports, or `config.yml` pins a different model for that agent in `task.agentModelOverrides`. Otherwise it regenerates the agent files, the "Subagent routing" section of `~/.omp/agent/AGENTS.md` (roles, cross-family reviewers, default efforts) and the worker-model line in Dross's block.

omp's own model roles stay Nate's settings, changed with `/model`: `default` is the main session's model, an unset `slow` uses `default`, and an unset `task` or `plan` keeps the session's own model. Install and `--check` print a WARN when one of those roles (or `advisor`, if enabled) names a model no roster agent uses, so a swap that leaves one behind shows up.

Subagents top out at `xhigh` effort: `task.maxEffort: xhigh` caps a task's `effort: hi`, the roster refuses a `max` default, and install warns if the ceiling changes. `max` is for a main session Nate sets himself.

## Files

| File | Installed as | Reaches |
|---|---|---|
| `omp-rules.md` | marked block in `~/.omp/agent/RULES.md` | every omp session and subagent, always |
| `dross.md` | marked block in `~/.context/home/AGENTS.md` | Dross's main turn |
| `roster.toml` | `~/.omp/agent/agents/<name>.md` for every roster agent, the "Subagent routing" section of `~/.omp/agent/AGENTS.md`, the worker-model line in Dross's block | every omp session, every subagent, Dross |
| `agents/*.md` | bodies of the generated agent files: `author.md` for builders (load `skill://nstack`, may spawn only readers and research workers), `reader.md` for bulk readers (no spawning), `researcher.md` and `verifier.md` for research lanes | subagents |
| `skills/nstack` | `skill://nstack` | any build; Context's `implement` workers |
| `skills/nstack-design` | `skill://nstack-design` | rewrites, new systems, programs of features; `design` workers |
| `skills/nstack-review`, `-verify`, `-writing`, `-teach` | `skill://…` (read on request, not auto-invoked) | `/nstack` modes; Context's `review`, `verify`, `writing`, `teach` workers |
| `commands/nstack.md` | `/nstack <task> \| shape <ask> \| catchup \| review \| verify` | omp |
| `commands/bro.md` | `/bro [catch me up]` | omp |
| `extensions/nstack-guard.ts` | omp extension | one-line reminders when a session's build subagents reach 6/12/24/48 (research and verifier lanes not counted) or its first 5-wide task call, and at 6/15/30/60 markdown files written; never blocks |
| `audit/scripts/` | — | the extraction and metrics behind the report; `metrics.py --since <date>` measures sessions after a change; `research_scaling.py` measures what research lanes add |

Context's contract (`apps/core/src/factory/context.contract.json`, `standards`) maps task types to these six skill names and embeds the whole `SKILL.md` in a 32k-token worker pack, so each skill stays self-contained and under 9,000 characters (about 2.2k tokens); `install.py --check` enforces both.

## Credits

Built on ideas from [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT) and the no-process-porn skill from [helix](https://github.com/DocumentDrivenDX/helix).
