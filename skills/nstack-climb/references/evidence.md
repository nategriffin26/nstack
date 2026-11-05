# Evidence behind each step

From the exemplar-climb-2026-11 research run (`~/.omp/local/research/exemplar-climb-2026-11/SYNTHESIS.md`, verified claims and corrections there) and the proof run (`~/Projects/exemplar-climb/proof/judging/`), 2026-11-05.

## Pairwise against exemplars, both orders
- Pairwise grading beat single-answer grading by over 8% agreement with experts on 654 web builds; the best judge reached 70.34% ([WebDevJudge](https://arxiv.org/html/2510.18560v3)).
- Pairwise verdicts flip toward assertive or verbose styling more often than absolute scores do: 29–44% against 17–26% for text-output reasoning judges on MT-Bench ([arXiv 2504.14716](https://arxiv.org/html/2504.14716)). Hence both orders, a held-out family and Nate's pick.
- A single pairwise verdict flipped on 13.6% of reruns on average, about 11 repeats for a stable majority (two OpenAI mini judges, [arXiv 2606.13685](https://arxiv.org/html/2606.13685)).
- MT-Bench's rule: a win counts only when it wins in both orders ([arXiv 2306.05685](https://arxiv.org/html/2306.05685v4)).
- Proof run: order-agreed verdicts identical on a full rerun, 6 of 6.

## Checks drawn from the exemplars
- Binary checks: 0.72–0.76 macro-F1 with experts against 0.53–0.57 for ternary ([arXiv 2511.07685](https://arxiv.org/html/2511.07685)).
- CheckEval yes/no lists raised agreement among evaluator models by 0.45 ([arXiv 2403.18771](https://arxiv.org/html/2403.18771v3)).
- Criteria inferred from labelled examples beat a criteria-free GPT-4 judge by 10.4% Spearman ([AutoCalibrate](https://arxiv.org/html/2309.13308)).
- Proof run: 90–94% agreement between families per check; 78 of 84 answers the same on rerun.

## Scores are a readout
- One in-context example at a score level shifts unrelated scores ([arXiv 2506.22316](https://arxiv.org/html/2506.22316)); prior scores shown to a judge lower its acceptance by up to 22 points ([arXiv 2608.25869](https://arxiv.org/html/2608.25869)).
- Proof run: Gemini scored one unchanged ChatGPT screenshot 6.4–8.8 across fresh runs; Opus and Sol held unchanged exemplars within 0.8. Exemplars in context moved the work's score toward the comparison in both directions.

## Fresh, blind judges from other families
- Author and judge sharing a dialogue: judge scores plateau while human scores fall ([arXiv 2407.04549](https://arxiv.org/html/2407.04549)).
- A three-family panel beat one GPT-4 judge on agreement with people (kappa 0.763 vs 0.627) at a seventh of the cost, though not every single judge on every set ([PoLL](https://arxiv.org/html/2404.18796)).
- Self-preference rises with self-recognition ([arXiv 2404.13076](https://arxiv.org/html/2404.13076)); errors common to all judges survive averaging ([arXiv 2310.02743](https://arxiv.org/html/2310.02743)).

## Exemplars
- Competitive evaluations use 2–4 comparators ([NN/g](https://www.nngroup.com/articles/competitive-usability-evaluations/)).
- Fewer, less common examples gave the most novel and best work; quality rose with copying ([Sio et al. meta-analysis](https://www.cmu.edu/me/idig/pdfs/Design_meta_analysis_inspiration_fixation.pdf)).
- AI help made stories better and more alike ([Science Advances](https://www.science.org/doi/10.1126/sciadv.adn5290)).

## Limits
- Multimodal UI judges: about 60% pairwise agreement with people, near chance on close pairs ([arXiv 2510.08783](https://arxiv.org/html/2510.08783)); best of 13 models found 40.7% of single-CSS changes ([arXiv 2605.29615](https://arxiv.org/html/2605.29615)).
- Judges agree with each other as much as people do but reach 58–66% of human agreement on subjective rubrics ([EMNLP 2026](https://aclanthology.org/2026.findings-emnlp.1696.pdf)).
- Open audio judges correlate at best 0.31 with expert quality ratings against 0.61 for one expert ([arXiv 2610.13247](https://arxiv.org/html/2610.13247v1)).

## Human checkpoints
- Show 2–3 variants, order randomized ([NN/g](https://www.nngroup.com/articles/testing-visual-design/)); in larger sets picks drift to the middle ([arXiv 2607.09018](https://arxiv.org/html/2607.09018)).

## Tools considered
- LangWatch Comparison has shuffle plus swap-and-reconcile, Apache 2.0, but platform API judges ([docs](https://langwatch.ai/docs/evaluations/experiments/ui/pairwise-compare)). promptfoo select-best is one pass with no order swap ([docs](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/select-best/)). Inspect and DSPy/GEPA are API-key based. Hence the thin `scripts/judge.py` over `omp -p`.
