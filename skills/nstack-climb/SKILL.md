---
name: nstack-climb
description: Make work match or beat exemplars Nate names, judged blind by models from other companies. In rounds, judges compare a screen, page, document, figure or film pairwise with each exemplar and check it against a list drawn from them; he picks the finalist. Not for raising a test or eval score, open redesigns or labs, or code review (nstack-review).
---

# Exemplar climb

A worker changes the work in rounds; after each round, fresh judges from other companies compare it blind with real exemplars and check it against a list drawn from those exemplars, until the verdicts stop improving. Nate chooses the exemplars and picks the finalist. The method gets work from rough to the exemplars' level on what can be checked; it cannot rank two polished versions or judge taste, sound or "is it mine".

## Use when
- "Make this as good as <app/page/film>", "match Grok Bot", "hill-climb the UI", "get it to beat Claude and ChatGPT".
- A screen, page, document, figure or film exists, and there are finished exemplars of the same kind to compare it with.
- A design lab or film brief has a pick, and the build should now close the gap to the references.

## Not for
- Reviewing a diff or plan for what to cut: `nstack-review`.
- Choosing among new directions when the look is unsettled: Nate picks from previews (`skill://nstack` › Taste; Dross's design lab). Run the climb after his pick.
- Work with a programmatic score (tests, an eval, a benchmark, a size budget): hill-climb that number directly; model judges add noise.

## The bar
- "Let's go deeper and make this a method we can use on anything we can get good exemplars on, likely as a skill?" (2026-11-05)
- "Grokbot is the actual exemplar for this field" (2026-10-19); he turned down six agent-made presets for "match Grok Bot… the actual exemplar".
- Video-taste run (2026-11-05): absolute model scores were useless (a reference film scored the same 6/10 as ours); pairwise against a reference, both orders, blind, caught the story gaps; Gemini could not judge sound.
- Theo Browne's council (2026-11-03): judged alone his UI reached 9/10; with Claude Code and Codex screenshots beside it the same work scored about 7.4. Don't tell judges the target.

## Steps

1. **Exemplars: 2–4 real, finished pieces Nate named or approved, plus the current version.** Pick ones that differ in what they do well; a set of near-identical exemplars teaches one house style. Never an agent-made mockup or generated image as an exemplar. Write in the ledger what each one is for.
2. **Capture the work and each exemplar on the same canvas, content and state.** Same window size, same theme, the same conversation or text where you can make it so; a deterministic capture script for the work, since every round recaptures. In the proof run, Grok Bot at 664 px wide lost to Dross for two of three judges because its sidebar crowded that window: the canvas decided the verdict. When two exemplars need different canvases, capture the work at each and pair them.
3. **Write 10–15 true/false checks from what the exemplars do, and show them to Nate before round 1.** Each check is something both exemplars do or the named one does ("a reaction sits on its message, not on its own row"). Binary checks were the most stable signal in the proof run: 90–94% agreement across three companies, 93–100% the same on rerun. A check that summarises the wrong exemplar steers the whole climb: "one accent colour" came from ChatGPT, contradicted Grok Bot's per-bot colours, and failed in every round. Freeze the list after his look.
4. **Measured checks are gates.** Anything a script can measure (contrast ratios, sizes against tokens, loudness and true peak, text length, load time, a reading-level number) is measured, not judged.
5. **Judge with `scripts/judge.py`, fresh and blind every call.** It runs `omp -p` on Nate's subscriptions (opus, sol or astra, gemini) with no tools, skills or history. `pairwise` compares the work with each exemplar in both orders and counts a verdict only when both orders agree (`split` otherwise); it returns per-dimension verdicts and the gaps each judge names. `checks` answers the list. `score` gives 1–10 scores as a readout only. `--context` says what the work is and what to weigh; never put a target score, a round number, earlier scores or which item is ours in it. Judges sharing the worker's conversation praise its revisions while people rate them lower ([arXiv 2407.04549](https://arxiv.org/html/2407.04549)).
6. **Two judges steer, a third company is held out.** At least one steering judge comes from a company other than the worker's, because a same-family judge shares the worker's taste (proof run: an Opus worker, opus and sol steering). A judge from a third company (gemini there) never steers and judges only the saved rounds at the end. When judges are slow, start each round with the fast judge alone and add the other once it stops finding gaps.
7. **Each round: fix the strongest agreed gaps in the real source, recapture, look at it yourself, judge, commit, log.** Gaps both judges name and agreed `exemplar` verdicts come first; `split` verdicts are noise. A change must be one Nate would get in the real product, never a special case for the capture. One ledger row per round: changes, verdicts per judge, checks passed.
8. **Stop at two rounds with no gain in agreed verdicts or checks, or when every steering verdict is a win or tie for two rounds.** Most of the gain comes in round 1 (proof run: checks 9 → 12 of 14, then about one more over seven rounds). A swing of about three checks between near-identical rounds is noise. Keep the best round, not the last.
9. **Nate picks the finalist blind.** One phone page: the current version and one or two finalists in shuffled order, then which is which, the exemplars, the before/after verdict table, and every place the climb changed one of his recorded picks, each as a choice. Serve it as a lab (`~/Projects/context-projects/<name>/lab/`, tailnet `/labs/<name>/`, Done button) so his picks come back to Dross. Nothing merges until he picks.

## What stays with Nate
Choosing exemplars and canvas; approving the checks; any change to a recorded pick (the proof run's link-icon reversal came from a check, not from him); taste between two good versions; sound and music; motion feel; humour; brand fit and "is it mine"; the final pick. Judges disagreed with his own exemplar in the proof run and pulled every wide round toward ChatGPT's look; his pick is the guard against that drift.

## Light version
For one screen, one page section or one short document: one exemplar he named, `pairwise` with two judges from different companies, the worker fixing agreed gaps for at most three rounds, then the before and after side by side for him. Skip the checklist, the held-out judge and the page; keep blind, both orders, fresh contexts and no target.

## By medium
- **Screens and pages:** screenshots at the real window size and theme from the real code. Judges find about 41% of single CSS changes ([arXiv 2605.29615](https://arxiv.org/html/2605.29615)); fine pixel differences need a pixel diff, not a judge.
- **Documents and prose:** attach text files; dimensions such as clarity, concision, structure, overall. Exemplars are finished documents of the same kind and length. Judges reward assertive and verbose styling, so add a length gate (step 4).
- **Figures:** render at final size; check every label against the data by script.
- **Films:** pair the cut with the reference film. `judge.py` was proven on images and text; for video, give it frame sheets of both, or have Gemini watch both files at 4 fps or more as the video-taste run did, still in both orders. Sound is measured (loudness, silences, beat alignment) and heard by Nate, never judged by a model. `video-brief` holds the film steps; when its brief has a reference film, judge the render against it this way.

## Pitfalls
- Absolute scores drift on unchanged inputs: Gemini scored the same ChatGPT screenshot 6.4 to 8.8 across fresh runs; Opus and Sol within 0.8. Order-agreed pairwise verdicts were identical on rerun (6 of 6). Never climb a score.
- Judges converge on what models like: on subjective rubrics they agree with each other as much as people do but reach only 58–66% of human agreement ([EMNLP 2026](https://aclanthology.org/2026.findings-emnlp.1696.pdf)). In the proof run they asked every wide round for ChatGPT's unboxed replies, grey user bubble and muted colours. Treat a gap that contradicts a recorded pick as a question for Nate, not a fix.
- A score with exemplars in context is a different measurement from a score alone: it moves toward the comparison in both directions (proof run: Opus 6.5 alone, 6.3 beside ChatGPT; 7.0 alone, 7.6 beside Grok Bot).
- Brand recognition: in a test Opus and Sol named Grok Bot from its screenshot alone; blind means unlabelled, not unrecognisable. Keep the held-out judge and Nate's pick as the check.

## Scripts
- `scripts/judge.py`: `pairwise`, `checks` and `score` over `omp -p` with blind, fresh judges that see their files under neutral names; `--help` lists the arguments. Judges are roster agent names (`--judges opus,sol`). Outputs JSON with every judge's reasons and gaps. A judge whose call fails prints `error` and makes the script exit 1, so rerun the round for that judge and never count it.

## References
- `references/evidence.md`: the studies and proof-run numbers behind each step, with links. Read it when a step seems wrong for your case.

## Provenance
- Research: `~/.omp/local/research/exemplar-climb-2026-11/SYNTHESIS.md` (2026-11-05).
- Proof run: `~/Projects/exemplar-climb/proof/` (CLIMB.md, judging/, page/), Dross branch `exemplar-climb/thread`, lab `exemplar-climb-lab`.
- Inputs: Theo Browne, "Agents Sucked At UI (Until Today)", 2026-11-03; video-taste-2026-11 SYNTHESIS.
