# nstack

How Nate's software gets built, for omp sessions and for Dross's workers. Size the ask, pin the facts and decisions that change the result, show taste before building it, prove each slice on Nate's real surface, and delegate only when it pays. The evidence behind every rule is in [audit/REPORT.md](audit/REPORT.md).

## Install

```sh
python3 install.py              # back up, then install (idempotent); ends with --check
python3 install.py --check      # verify links, rule blocks, skill sizes, Context's contract and omp's skill filters
python3 install.py --uninstall  # remove nstack and restore what the first install replaced
python3 install.py --no-dross   # leave Dross's home AGENTS.md alone (combines with the above)
```

The first install saved the pre-nstack state to `local/backups/baseline/` (with `manifest.json`); `--uninstall` restores from it and removes only nstack's own links and marked blocks, so later edits to the instruction files survive. Every install also writes a dated backup. Edit files here, not the installed copies: skills, commands and the extension are symlinks, and the two rule blocks are rewritten on each install. The "Combined use" section of `~/.omp/agent/AGENTS.md` was edited by hand to defer to nstack; its original is in the baseline.

## Files

| File | Installed as | Reaches |
|---|---|---|
| `omp-rules.md` | marked block in `~/.omp/agent/RULES.md` | every omp session and subagent, always |
| `dross.md` | marked block in `~/.context/home/AGENTS.md` | Dross's main turn |
| `skills/nstack` | `skill://nstack` | any build; Context's `implement` workers |
| `skills/nstack-design` | `skill://nstack-design` | rewrites, new systems, programs of features; `design` workers |
| `skills/nstack-review`, `-verify`, `-writing`, `-teach` | `skill://…` (read on request, not auto-invoked) | `/nstack` modes; Context's `review`, `verify`, `writing`, `teach` workers |
| `commands/nstack.md` | `/nstack <task> \| shape <ask> \| catchup \| review \| verify` | omp |
| `commands/bro.md` | `/bro [catch me up]` | omp |
| `extensions/nstack-guard.ts` | omp extension | one-line reminders when a session's build subagents reach 6/12/24/48 (research and verifier lanes not counted) or its first 5-wide task call, and at 6/15/30/60 markdown files written; never blocks |
| `audit/scripts/` | — | the extraction and metrics behind the report; `metrics.py --since <date>` measures sessions after a change; `research_scaling.py` measures what research lanes add |

Context's contract (`apps/core/src/factory/context.contract.json`, `standards`) maps task types to these six skill names and embeds the whole `SKILL.md`, so each skill stays self-contained and under 6,500 characters; `install.py --check` enforces both.

## Credits

Built on ideas from [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT) and the no-process-porn skill from [helix](https://github.com/DocumentDrivenDX/helix).
