---
name: nstack-skills
description: Writing, updating, merging or retiring an agent skill in any of Nate's stores (nstack and omp, Dross, brain, Claude), with the routing check that proves the right requests still load it. Read before skill_create, skill_update, skill_save or editing any SKILL.md, and when a skill loaded wrongly or not at all. Not for using a skill.
---

# Skills

A skill tells a future agent how Nate wants one kind of work done. Its description is the only part a router reads before choosing, so a skill has two jobs: load for the requests it covers and for no others, then carry what an agent would not get right on its own (his bar, his corrections, the steps that worked, the traps that cost time). Generic know-how costs context and changes nothing; most public coding skills change nothing at all (`references/evidence.md`).

## Where skills live

| Store | Files | Write with | Old versions | What the router sees |
|---|---|---|---|---|
| nstack and omp | `~/Projects/nstack/skills/<name>/` and other repos, linked into `~/.omp/agent/skills` | edit the repo file; omp shows only names matching `skills.includeSkills` in `~/.omp/agent/config.yml` | git; a skill directory outside any repo (`cua`, `remote-auth` in `~/.omp/agent/skills`) has none | a hint of at most 12 words that omp's small model compresses from the description; when the compression is unusable, the first sentence or first 99 characters |
| Dross | Postgres `agent_skills` (the repo copies in `infra/dross/skills` are seeds) | `skill_create`, `skill_update` | every update and delete keeps the old row in `dross.skill_versions` (commands below) | the full description |
| brain | `~/.brain/context/{skills,styles}` | `skill_save`, after `skill_get {"name":"write-skill"}` for the brain's own steps | git, a signed commit per save | the first sentence, cut at 200 characters |
| Claude Code | `~/.claude/skills` | edit the file | git for linked skills; none for plain directories | the full description |

Dross's versions, from `~/Projects/dross` with its environment loaded (`set -a; . infra/dross/env; . ~/.dross/secrets.env; set +a`): `node --import tsx apps/core/scripts/team.ts skill-history <name>` lists them, `skill-history <name> <version>` prints one, `skill-restore <name> <version>` makes it current again.

## Decide what to write

1. **Only from finished work.** Write from this session's trace (requests, corrections, failures, the accepted result), never before the work or from general knowledge: skills a model wrote before the task scored below no skill at all. A one-off gets a `remember` note; a look gets a brain style.
2. **Read the neighbours.** `skill-eval catalog <store>` prints the store's skill list as its router sees it. Pick the one to three skills nearest to yours and read their bodies.
3. **Then choose**:
   - A skill already covers this job: update it. Merge your change into the body you read; a rewrite from memory drops rules that took sessions to learn.
   - Two skills would load for the same request: merge them into one. Two same-job skills loaded together each lose a third of their rules.
   - It is a distinct job: create it.
   - A skill nobody loads in real use, or one a newer skill replaced: retire it: delete the Dross row or a directory inside a git repo (their history keeps it); move a directory outside git to `~/Projects/nstack/local/backups/` instead.

## The name and description

- **Lead with the job, in Nate's words, in a first sentence under 100 characters.** It says what the skill does, with the nouns and verbs he uses ("PCB", "KiCad", "his Chrome", "design lab"), and stands alone: omp asks a small model for a 12-word hint and shows that first sentence instead when the hint runs long (it often does), the brain shows only the first sentence, and Codex and Claude Code shorten long lists. The sentences after it say when, and what sets it apart.
- **Contrast with the nearest neighbour.** Say what this skill covers that the neighbour does not. Add an exclusion ("Not for X; that is `<other>`") only against a neighbour that real requests confuse with it. In Skill++'s ablation, differentiation from the nearest skill mattered most, then the name, then exclusions.
- **Claim only what the body does.** An overclaiming description pulls requests the body cannot serve.
- **Name**: lowercase with hyphens, the kind of work (`design-lab`, `release-notes`), not the project; when its first word matches a neighbour's, add a qualifier that says the difference (`nstack-writing`, `nstack-skills`).
- Length: about 200 to 350 characters; the format allows 1,024.

## The body

Fill `references/template.md`. The bar:

- **Rule, why, exact value.** "Keep each step under 300 ms because Nate called slower ones sluggish (2026-10-20)", not "keep it snappy".
- **His words, quoted with the date**, for every request and correction that defined done.
- **Compact.** About 200 lines at most (500 is the format's limit); long detail goes in `references/` with a line saying when to read each file.
- **Boundaries and a light path**: when it applies, when it does not, and the two or three steps for a small version. Failing skills pushed one heavyweight pipeline onto tasks that needed less.
- **Exemplars, not templates to paste.** A finished artifact goes in `examples/` with what to learn from it and what not to copy; agents copy an example's values verbatim.
- **Provenance**: the project, session and files it came from.
- Nothing a capable agent does unprompted, no project's values written as universal, no secrets or private details of other people, and no limits Nate did not set (deadlines, checkpoints, time targets, partial drafts, "X first, the rest later"); keep only his constraints and the real one-way doors (spending, sending as him, deleting, publishing).

## Check routing before saving

1. Add the cases this change is for to `~/Projects/nstack/local/evals/skill-routing/cases.jsonl`, one JSON line each: the real request that prompted it (expect your skill) and a near miss that belongs to another skill or none.
   `{"id": "dross-lab-duo", "store": "dross", "request": "<Nate's message, verbatim>", "expect": ["design-lab"], "allow": ["launch-omp-worker"], "source": "dross thread <id> (2026-11-03)"}`
   `expect` is what must load (`[]` when nothing fits); `allow` lists extra loads that are not wrong.
2. Write the new SKILL.md to a file and run `skill-eval --propose <store>:<file>` (add `--drop <store>:<name>` for a merge). It scores the store's cases with the current list and with yours, three runs each, and prints every case that changed. For omp, `skill-eval catalog omp --propose omp:<file>` shows the hint omp will display.
3. Save when the proposed score is at least the current one and no case that passed before now fails. A one-case drop that comes back on a rerun is noise. Fix a real regression at its cause and run once more; never keep rewording until the score passes, which tunes the description to these few cases and inflates the score.

## Save and tell Nate

- nstack and other repos: commit (nstack: push after the personal-information check). A skill directory outside git: copy it to `~/Projects/nstack/local/backups/` before editing. Dross: `skill_update`, which keeps the old version. Brain: `skill_save` with the digest you read as `base`.
- Tell Nate in one line: the skill, what it now says or does differently, and how to undo it.

## When a skill misfires

The agent that sees a skill load wrongly, fail to load, or lead an agent astray fixes it then, with the steps above: the request becomes a case, a routing miss gets a description fix, a misleading rule gets a body fix. A description fix lands once the check passes. A body change that alters behavior Nate relies on (what gets built, sent or asked) goes to him as a proposal with the diff. Dross's weekly `transcript-healthcheck` does the same for misfires across the bots' chats.

## References

- `references/template.md`: the SKILL.md skeleton. Read it before writing the body.
- `references/evidence.md`: the studies behind each rule, with links. Read it when a rule seems wrong for your case.
