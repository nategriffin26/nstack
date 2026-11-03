# Evidence behind nstack-skills

Each rule in SKILL.md, the finding behind it, and where to read it. Writing rules gathered 2026-10-20 (from nbrain's write-skill); routing rules from the skill-refine Wave, 2026-11-03 (`SYNTHESIS.md` in `~/Projects/skill-refine`).

## Write after the work, from its trace

- **Self-generated skills hurt.** Agents that wrote their own skill pack before a task, then solved with it, landed below no skills at all: −8.1 (Claude Code + Opus 4.7), −11.3 (Codex + GPT-5.5), −11.5 points (Gemini CLI). Curated skills added +18.2 to +24.8 on the same setups. The authors attribute it to packs never found, authoring displacing the work, and confidently wrong content. SkillsBench, https://arxiv.org/html/2602.12670
- **Skills distilled from execution traces help.** Trace2Skill gained +17.5 to +21.5 points from consolidated trajectories; a draft from parametric knowledge alone scored about the same as no skill (26.17% vs 27.67%). https://arxiv.org/html/2603.25158v3
- Corroborated by AWM (+51.1% relative on WebArena) https://arxiv.org/pdf/2409.07429 and SkillWeaver (+31.8% / +39.8%) https://arxiv.org/pdf/2504.07079.

## Descriptions that route

- **Neighbour-aware rewriting.** Skill++ rewrote only each new skill's name and description against its most similar existing skill (a body-grounded description leading with what the neighbour lacks, then "Does not cover" exclusions, 298 characters at most). With Claude Haiku 4.5 routing, full selection at 731 skills went from 36.4% to 76.3%. Without differentiation it fell to 56.6%, without name clarification to 61.6%, without exclusions to 64.6%. Contrast with the nearest skill beat contrast with a random one by 9.5 points. With randomly sampled additions the original metadata degraded much less (97.0% to 84.3%) and the gain was 8.9 points: the method fixes interference between similar skills. 18 of 85 audited descriptions overclaimed their body. https://arxiv.org/html/2611.00544v1
- **What the router sees is short.** omp shows each skill as a hint of at most 12 words that its smol model compresses from the description (prompt: "WHEN to use; WHEN NOT only if it prevents confusion. Retain recognizable trigger words"), cached in `~/.omp/agent/skill-descriptions.db`; an unusable compression falls back to the first sentence or 99 characters (omp v18.15). nbrain's MCP instructions list the first sentence, cut at 200 characters. Codex caps the skill list at 2% of context and shortens descriptions first, so its docs say to front-load the key use case. https://learn.chatgpt.com/docs/build-skills
- **Agents under-load skills.** A skill was never invoked in 56% of Vercel's eval cases; explicit trigger wording raised its pass rate from 53% to 79%. https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals. Anthropic's skill-creator: "Claude has a tendency to undertrigger skills". https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md

## Merge same-job skills

- A skill's rules were followed 93 to 99% of the time loaded alone and 61 to 62% beside a same-job skill; telling the model which has priority did not help. One merged file with a worked example restored 96 to 99% of the achievable rules. https://arxiv.org/html/2610.25064
- AutoSkill compares each candidate with its single most similar skill and keeps, merges (with a version bump) or discards it. Selm admits an update only if a held-out selection set improves. (SelfEvolving dossier, skill-refine Wave.)

## Routing check without tuning to it

- Anthropic's trigger evals: about 20 queries, half near misses that should not trigger, 3 runs each, a 0.5 trigger-rate threshold, a 60/40 train and held-out split. https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
- Keep-if-better loops on small sets overstate: with 16 selection items the final score ran 13 to 20 points above held-out accuracy (1 to 5 points at 256). https://arxiv.org/html/2610.09239. Hence one check per change, not a rewording loop.

## Compact core, boundaries, a light path

- Compact and standard skills gained +19.0 and +21.5 points; comprehensive documentation +0.7. SkillsBench, https://arxiv.org/html/2602.12670
- 68.8% of 125 skill-induced functional failures came from on-topic skills prescribing wrong specifics, and 62.6% of efficiency regressions from excess procedure. https://arxiv.org/html/2608.11888v1
- About 80% of 49 public coding skills changed nothing (+1.2 points on average). https://arxiv.org/html/2603.15401v1
- Body under 500 lines; supporting files load on demand. https://agentskills.io/specification

## Update by merging, not rewriting

- ACE: incremental updates beat monolithic rewrites; one rewrite collapsed a context from 18,282 to 122 tokens and accuracy from 66.7 to 57.1, below the no-adaptation baseline. https://proceedings.iclr.cc/paper_files/paper/2026/file/8a94ff6f922d995d7d3f4ebf4143e442-Paper-Conference.pdf

## Exemplars anchor

- Agents copied a template's concrete values verbatim instead of adapting them. https://arxiv.org/html/2603.15401v1
- Craft transfers as an articulated why plus an exact value. https://emilkowal.ski/ui/agents-with-taste
