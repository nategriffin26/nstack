# nstack

How I build software with coding agents: a short set of standing rules, skills that load when the work calls for them, and a few slash commands for [omp](https://github.com/can1357/oh-my-pi).

Coding agents fail in predictable ways on real work. They start building before the facts and decisions that decide the result are pinned down. They build more than was asked, in more parts than the problem needs. They build a look at full scale before anyone has seen it. They call it done because the tests pass, not because it works where it will be used. And they keep spending agents, reviews and tests long after more of it stops changing the outcome. nstack aims every step at the end state: the simplest correct design, finished in every state and crafted, proven where it is used.

It is written for one person, me (Nate), and tuned against an audit of about a thousand of my own agent sessions. The rules name me, my Mac and my phone on purpose: an agent does better with a specific person and a specific setup than with "the user". It is published as a reference. Fork it and make it yours.

## The ideas

Every rule follows from five ideas, and agents reason from them wherever no rule fits:

- **The end state is the work.** A plan, check, review or question earns its place by being likely to change what the person gets.
- **Proportion.** The person's attention, wall time and usage are all costs. Agent time is cheap next to theirs, so agents do the translating: what the person reads or decides from is built for them.
- **Reality settles facts; the person settles taste.** Facts, causes and numbers get checked, not assumed. Taste, scope and one-way doors are decided by the person from real previews.
- **Simple is correct.** The simplest architecture that does what was asked is quick to build, easy to debug and cheap to change, and it extends when a real need shows up.
- **A worker knows only its brief.** Delegation carries intent exactly as far as the brief does.

## How a task runs

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/nategriffin26/nstack/master/docs/task-flow-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/nategriffin26/nstack/master/docs/task-flow-light.svg">
  <img alt="How a task runs: ask, size, frame, decide, design, build, prove, report. A one-sitting task goes straight from size to build. You answer one batch of questions and pick the look from real previews." src="https://raw.githubusercontent.com/nategriffin26/nstack/master/docs/task-flow-light.svg" width="600">
</picture>

Each question comes with a recommended default, and work that does not depend on the answer keeps moving while you think. The frame's facts are checked with a command, never assumed. Done means it works where you will use it: your phone, the app after a restart, the real CLI, real data.

## What's in it

| Piece | Loads | What it does |
|---|---|---|
| `omp-rules.md` | every session and subagent, always | The floor: twelve standing rules in under 4,000 characters |
| `skills/nstack` | before features, multi-step changes and agent briefs; autoloaded into author agents | The method: size, frame, decide, design, taste, fixes, build, agents, review, prove, report |
| `skills/nstack-design` | big asks: rewrites, new systems, unsettled architecture or look | Ground the facts, walk the failures that would cost you, write the one-page shape with slices |
| `skills/nstack-review` | reviews and critic verdicts | By a model of another family: what would hurt on the real setup, judged by its likelihood there, and what to cut, tighten or redesign, as advice |
| `skills/nstack-verify` | when proof needs more than the tests, a number decides something, or speed is the goal | Proof on the real surface, a number checked before it counts, a speed loop with each change kept or reverted |
| `skills/nstack-writing` | before prose anyone reads beyond a few lines | Twenty-one habits that make agent prose read as generated, each with its plain replacement, and one edit pass |
| `skills/nstack-research` | whenever outside facts are needed | Sizes the work as a Look up, a Dig (a short cited note), a Wave (research lanes, verification, a synthesis) or a Trail (a reading map walked out from seeds), checks earlier research first and saves what it finds |
| `skills/nstack-research-worker` | autoloaded into the `researcher` and `verifier` agents | Their field guide: searching and reading, the note, dossier, map and verification formats, confidence rules |
| `skills/nstack-climb` | when work should match or beat chosen exemplars | Rounds of changes judged blind by fresh models from other companies against your exemplars; `scripts/judge.py` runs the judges through `omp -p` |
| `skills/nstack-grill` | only when asked | Rounds of questions to get on the same page before work starts |
| `skills/nstack-formal` | only when asked | Formal verification of the promise where a bug costs most, left behind as a check that reruns with one command |
| `skills/nstack-skills` | before writing, updating, merging or retiring a skill | When a skill is worth writing, a description that routes, the body's bar, and the routing check |
| `skills/schematic-figure`, `skills/patent-drawing` | drawing a schematic, concept figure, block diagram or patent sheet | [LGW Lab's](https://github.com/lgwrightlab/schematic-figure) vendored skills (MIT, see `skills/schematic-figure/UPSTREAM.md`) |
| `skills/video-brief` | making a short film, app demo or motion piece from a one-line idea | The brief, three directions as stills to pick from, the render on the right renderer per beat, and a fresh critic's review |
| `tools/web.py` | on PATH as `web` | Search, read, GitHub and Reddit readers, a page store and a citation log that `web check` scores; `web mcp` serves it over MCP, and `tools/executor-web` is that server as an Executor app |
| `tools/skill_eval.py` | on PATH as `skill-eval` | Scores real past requests against each store's skill list as its router sees it, current beside proposed; cases stay private in `local/evals/skill-routing/` |
| `extensions/nstack-guard.ts` | always, as an omp extension | One-line notes where written rules did not hold: a message to a critic after its verdict, a question while agents run, a ledger past 12 KB, a comment about earlier code or the conversation, and a pointer back to the ledger after compaction |
| `extensions/brief.ts`, `extensions/brief.md` | when typed, as `/brief` | A briefing agent reads the request and the code, docs and history it touches, then sends the brief as your prompt in the same session |
| `tools/brief_eval.py` | by hand | Measures `/brief` on real past requests, briefed against direct, judged by a model of another family |
| `roster.toml`, `agents/` | at install | Which model does which job; generates omp's agent files and the routing section in `~/.omp/agent/AGENTS.md` |
| `audit/scripts/` | by hand | The session metrics the rules were tuned against, read from omp's local session store |

## Commands

| Command | Does |
|---|---|
| `/nstack <task>` | Runs the task under the full method; useful when a session treats a real feature as a quick fix |
| `/nstack shape <ask>` | The one-page shape and one batch of questions; builds nothing |
| `/nstack grill [topic]` | Rounds of numbered questions on the important things only, each with a recommended answer; "grill me" works too |
| `/nstack review` | One deep review of the current change by a model of another family |
| `/nstack verify` | Proves the current work on the real surface and checks any measured number |
| `/nstack formal [area]` | Formally verifies the riskiest promise in the repo or the named area; `formal maintain` realigns an existing check |
| `/nstack correct <mistake>` | Fixes a recurring mistake in structure (a type, a check whose error names the fix, a test), proven against a real past instance |
| `/nstack simplify [area]` | Makes an area smaller without changing what it does, one commit per change, with the files touched per commit recorded for the next pass |
| `/brief <request>` | A briefing agent investigates first and writes the prompt: your words quoted, the facts and decisions that bear on them, the questions only you can answer, and what done looks like |

## Asking well

- Give the outcome in your own words, where you will check it, what must not change, and references for anything visual (or "show me directions").
- For a long run, give a finish condition that can pass or fail. A duration is not one.
- For a bug, describe what you see rather than your theory of the cause, so the agent looks everywhere first.
- Races between models and extra critics run only when you ask for them by name ("race opus and astra on this").
- Anything you say explicitly overrides nstack: models, number of agents, skipping a preview.
- Long work keeps one ledger at `local/nstack/<slug>.md` in the project; "continue <thing>" resumes from it.

## Install

Needs omp and Python 3.11 or newer. Used on macOS.

```sh
gh repo clone nategriffin26/nstack ~/Projects/nstack
cd ~/Projects/nstack
python3 install.py              # back up, install, then run --check
python3 install.py --check      # verify links, generated files, rule blocks, sizes and roster models
python3 install.py --uninstall  # remove nstack and restore what the first install replaced
```

The installer symlinks the skills, commands and extensions into `~/.omp/agent/`, `tools/web.py` to `~/.local/bin/web` and `tools/skill_eval.py` to `~/.local/bin/skill-eval`, generates one agent file per roster agent, and writes marked blocks into `~/.omp/agent/RULES.md` and `~/.omp/agent/AGENTS.md`. The first install backs up everything it touches to `local/backups/baseline/`, and `--uninstall` restores from there; every later install writes a dated backup and removes links to files the repository no longer has. Edit files in the repository, never the installed copies, and rerun the installer.

`web` reads its keys from the environment or `~/.omp/agent/keys.env`: `EXA_API_KEY` for search, `TINYFISH_API_KEYS` (comma-separated free keys) for reading and as the search fallback, optionally `BRAVE_API_KEY` and `SERPER_API_KEY`, and `OPENROUTER_API_KEY` for the support score `web check` gives each claim (without it, check skips the score and says so). `web save` and `web prior` keep research in [nbrain](https://github.com/nategriffin26/nbrain) when its CLI is on PATH.

`--check` validates every roster model against your `omp models` catalog, so on a different setup edit `roster.toml` before the first install.

## Make it yours

1. **Fork and clone** it anywhere; the installer links from wherever the repository sits. My path (`~/Projects/nstack`) and my model settings page appear only in the routing text `install.py` generates.
2. **Put your name in.** `git grep -n Nate` finds every mention. Swap my phone, Mac and data for the places you check your own work.
3. **Pick your models.** `roster.toml` maps roles (author, systems, taste, implementer, reader, research, verify) to agents and agents to models from `omp models`; `family` decides which models review each other.
4. **Install and probe.** Run a fresh omp session on an ordinary-looking task in a scratch repo, and judge it by what the agent actually read, ran and changed, not by what it says it followed.

`--check` holds `omp-rules.md` under 4,000 characters and each skill under 20,000: the rules ride on every turn of every session, so the floor stays short and the detail loads on demand.

## Credits

- [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT, 0.15.29): agent control in `skills/nstack` › Agents (orchestrate, swarm, interrogate), the measurement checks and verify script in `nstack-verify` (benchmark-checklist, explain-the-number, hillclimb, create-verification-skill), the rules in › Fixes (bug-fix, attack-the-premise, fix-root-causes), `/nstack correct`, and `nstack-formal` (create- and maintain-formal-verification-skill).
- [Specula](https://github.com/specula-org/Specula) (Apache-2.0): `nstack-formal`'s history-mined targets and trace validation.
- [mattpocock/skills](https://github.com/mattpocock/skills) (MIT): the grilling behind `nstack-grill`, and the deletion test and history-read targets in `/nstack simplify`.
- [helix](https://github.com/DocumentDrivenDX/helix): the no-process-porn skill.
- [Planning with Agents](https://maggieappleton.com/planning-agents) by Maggie Appleton: agents doing the translating, the shape kept for builders while I read a version built for me, options shown by what they do to the real code, live controls for a continuous taste value, and short grill rounds with "show me".
- [U.S. Graphics Company](https://x.com/usgraphics/status/2114413710395720182): the floor's line on language and names, from their specification-register naming rule; a reply's critique kept the register and traded the persona for its rules.
- [0xdef1](https://x.com/0xdef1/status/2114384292780589327): the ledger kept to its current state with history archived, the guard's 12 KB note, rules in the narrowest file that loads, and repeated commands turned into a small tool.
- [How I work with Agents](https://x.com/thorstenball/status/2114386050638336082) by Thorsten Ball: checking every plausible cause in one pass (`skills/nstack` › Fixes).
- [codetesla51/skills](https://github.com/codetesla51/skills): tests aimed where code breaks, fakes at the wire and outcome assertions (› Prove), the review's check-the-checks step, starting a fix from the last version that worked and fixing the same mistake elsewhere (› Fixes), fewer concepts and no silent defaults (› Design), reverting speed changes inside the noise, and the rejected option in the commit body (› Decide). No license, so these are paraphrased ideas; no text was copied.
- [Traits](https://traits.sh/) by Harry Solovay: the review's pass over my recorded picks, one at a time.
- [system-design-skills](https://github.com/proyecto26/system-design-skills) by J.D. Nicholls (MIT): naming the signal that would call for the next step up beside the plain architecture, never "if needed".
- [How I Design with AI, part 2](https://x.com/reactiverobot/status/2115075879923765615) by Matt Dailey: crux screens that get the taste work, and the craft pass's sheet of every state listed from the code (his [ui-sweep](https://github.com/ref-tools/marketplace/tree/main/plugins/ref-skills/skills/ui-sweep) skill, MIT).
- [ub-mode](https://github.com/unclebob/ub-mode) by Robert C. Martin: setting a bolt-on beside the design that would have been built had the requirement been there from the start. No license, so the idea is paraphrased; no text was copied.
- [Babysitting AI Agents](https://arxiv.org/abs/2610.34748) by Mittal, Kim, Counts, Neville, Das and Laban (Microsoft Research, Georgia Tech): stopping a unit that has stopped producing new evidence, and the report's list of actions the diff will not show.
- [Alpha generation p1](https://docs.google.com/document/d/14qXSLPBZENOTmYJMJPQ7xFRtMzm00qCF9foTKqque70/edit) by snbafana: the Trail in `nstack-research`.
- [schematic-figure](https://github.com/lgwrightlab/schematic-figure) by LGW Lab (MIT): `skills/schematic-figure` and `skills/patent-drawing`, vendored at commit 09d8b6e, unchanged except one setup note.
- [scholarly-paper-revision](https://x.com/__paleologo/status/2116602494428299632) by Giuseppe Paleologo: `nstack-writing`, from its section on AI stylistic tropes, generalized beyond mathematical papers.
- [AI loops](https://x.com/meln1k/status/2116961861845287349) by Nikita M.: deterministic simulation in `nstack-formal`, the speed loop in `nstack-verify`, and `/nstack simplify`, run on command rather than on a schedule.
- [deslop](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/deslop) from Cursor's team kit (MIT): the leftovers `/nstack simplify` removes.
- [nando-skill](https://github.com/nandorojo/nando-skill) by Fernando Rojo: the call site before the interface, one operation per behavior, configuration read once and one definition per schema (› Design), exhaustive state switches (› Prove), and a layout that holds still with every control earning its space (› Prove). No license, so these are paraphrased ideas; no text was copied.
- [Panta's reviewer prompt](https://x.com/thepanta82/status/2117542858907337121): the review's simplify questions, "be bold", uncommitted changes as the default, and abstract bug hunting kept out of the review.
- [Lauren Tan on adversarial reviews](https://x.com/poteto/status/2117437607940681849): harm findings that need a path to the real setup, and the rehearsal beside the one-way-door critic.
- [Dave Kiss](https://x.com/davekiss/status/2118094079879794894) and [astral-sh/uv's AGENTS.md](https://github.com/astral-sh/uv/blob/main/AGENTS.md): comments and docs written for a reader who never saw the conversation, and the guard's note on wording about earlier code, as a note rather than a block.

## License

[MIT](LICENSE)
