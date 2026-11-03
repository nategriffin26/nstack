---
name: nstack-writing
description: "Write prose anyone reads beyond a few lines without the habits that read as generated. Covers reports, DONE.txt, research notes, docs, READMEs, commit messages, briefs and product copy, with plain replacements and a self-edit pass."
---

# Writing

The floor sets the register: write only what someone will act on, with no word Nate would not miss, in precise professional English, leading with what he must judge, in plain words he can read on a phone. This catalog names the habits that break those rules one sentence at a time.

The patterns are cues for editorial judgment, not bans or tests of authorship. Change one when it is repetitive, vague, overstated or distracts from the content; keep a contrast, parallel, count, technical term or dash that does real work. One "X, not Y" that heads off a likely misreading stays; five on a page go. Never trade precise technical language for simpler, wrong words, and never swap a habit for its synonym. Quotes, Nate's own words and source text are never edited.

## The pass

A short text (a reply, a commit message, a few lines) is written with the catalog in mind; it needs no separate pass. A long or saved text (a note, synthesis, report, DONE.txt, doc, README or brief) is drafted first, then edited once:

1. Read the draft against the catalog and mark each hit.
2. For each hit, write the plain claim it dressed up: the number, the cause, the source, the next step. A sentence with no claim underneath is deleted.
3. Reread for loss: every fact, qualification, number, link and confidence label is still there, and the required format (a DONE.txt's lines, a note's sections) is intact.

One pass. Polishing in loops flattens the voice and costs more than it returns.

## Catalog

### Framing and structure

1. **Counted symmetry.** Lines built to be memorable: "One app, two jobs"; "Two tiers of authority"; "one family, one differentiator". Say what the things are.
2. **Counted packages.** "Three reasons:"; "Four facts stand out"; "nbrain keeps five things on your machine:". A list shows its own length. State a count only when the count is the point.
3. **Slide slogans.** Headings and bold leads written as verdicts: "Verdict: pursue narrowly"; "Structure beats tuning"; "The shared secret is the boundary." A heading names its topic; the finding goes in a sentence with its evidence.
4. **A bold label on every item.** Each bullet opens with a bold headline that the sentence after it restates. Bold only what a skimming reader must find; otherwise the sentence opens with its subject.
5. **Headings that explain the explanation.** "Why"; "What this means"; "Who it's for"; "How it works". Name the content: "Users", "Network exposure".
6. **Exposition staged as questions.** "This raises a question: which store should own it?"; "So what changed?". State the answer. The question a research note was asked stays as its title.
7. **Recaps.** A table, box or "Summary" that repeats the paragraph above it. Keep one form: the table when the reader compares rows, the prose when it explains.
8. **Roadmaps and promises.** "Below I cover…"; "The next section shows…"; several "Later, only if…" items. Cut the roadmap; a deferred item states its trigger once.
9. **Tour-guide transitions.** "Back to the build."; "Now for the interesting part."; "With that settled,". Start with the next fact.

### Sentence moves

10. **Corrective antithesis.** "X, not Y" or "rather than" by reflex: "The work left is packaging it for strangers, not inventing it." Keep Y only when a reader would plausibly believe it; otherwise state X.
11. **A misconception set up to be corrected.** "The gap isn't a missing category. … The gap is quality and trust."; "It's tempting to think…". Say what is true and why.
12. **Answering an objection nobody raised.** "That is not an omission."; "Nothing new was claimed."; "(bugs, not user error)". Give the reason directly, or nothing.
13. **Compression claims.** "In one sentence:"; "The whole story fits in a line"; "Short answer:" followed by a paragraph. Give the short answer.
14. **Mirror sentences.** "The production standard sets a floor; topic demand and concept make the outcome." The symmetry makes the claim cleaner than the evidence. Write each half with its own qualification.
15. **Announced importance.** "This matters because"; "Crucially,"; "Notably,"; "The key insight is". Show the consequence; the reader judges what matters.
16. **Results turned into morals.** "A watcher is not a backup."; "More compute is not always better." after a specific finding. End on the finding and what to do about it.
17. **Decorative participle tails.** ", highlighting the need for…"; ", underscoring…"; ", making it ideal for…". State the causal link or cut the clause.
18. **Arrows and dashes as sentence glue.** "dictation phone → core → OpenRouter returned the right text"; a main point carried inside a pair of em dashes. Arrows belong in menu paths (Settings › Voice) and value changes (10.5% → 2.3%); a sentence uses verbs. An aside that matters becomes its own sentence. Punctuation is never a sign of authorship.

### Words and tone

19. **Agency verbs on things.** Code, models and services that "decide", "want", "prefer" or "insist": "the LoRA recipe wants 16 GPUs". Standard usage stays ("the server refuses the token"); repeated, the verbs give the system a personality instead of describing its behavior. "Needs 16 GPUs".
20. **A recurring metaphor.** "buys", "costs", "tax", "spends", "moat", "load-bearing", "lands", "quietly", applied to unrelated points. One apt metaphor is fine; the same device on every point is a habit.
21. **Consultancy vocabulary.** playbook, table stakes, leverage, unlock, north star, framework, operational, "audit" for a quick look. Name the procedure.
22. **Moralized precision.** "honest numbers", "honestly", "calibrated", "the real gap", "the real test". Name the property: measured on the device, a held-out set, the 95th percentile. "Real" stays when it contrasts with a simulator, a mock or a copy.
23. **Promotional and self-praising words.** seamless, robust, powerful, elegant, clean, solid, comprehensive, pivotal, game-changing, "a testament to". Replace with the evidence: tests passed, milliseconds measured, people who use it.
24. **Vague attribution.** "experts agree"; "hiring guides consistently say"; "community reports note"; "best practice is". Name and link the source, mark it as your inference, or cut it.
25. **Filler.** "It's worth noting that"; "In today's fast-moving landscape"; "Let's dive in"; "Great question"; "I hope this helps"; a closing "challenges and next steps" paragraph with no specific problem in it.

### Caveats and repetition

26. **Theatrical disclaimers.** "not a claim that installing every checklist tool makes this server safe"; "not a classification of every conceivable case". State the real limit plainly, once.
27. **Stacked hedges.** "may potentially", "likely could", a confidence tag on every line. One confidence label where it changes the decision.
28. **A repeated caveat or fact.** The same limitation or number in the summary, a section and the close. Say it where it applies.
29. **Process story and internal names.** How the work went (rounds, lanes, "I mined", "recomputed by me") and names only agents know (lane names, claim numbers, job numbers, ledger files) in prose for Nate. Lead with the result; give method only where it changes how far he can trust it, in his words. Citations and evidence paths stay.
30. **Mechanical uniformity.** Every paragraph or bullet the same length and shape, the same transition, a triad by default ("fast, reliable and simple"), ornate words where plain ones serve. Let the content set the shape; one template per list is right when the items are alike.

## Where each kind of text slips

- **Status reports and DONE.txt**: process story, self-praise, arrows, "the real", defensive asides, caveats repeated across lines.
- **Research notes and syntheses**: verdict slogans, counted packages, bold leads, theatrical disclaimers, vague attribution, recap tables, internal lane names.
- **Docs and READMEs**: slogan headings, explaining headings, promotional words, roadmaps.
- **Commit messages**: the subject says what changed; no "This commit…", no "cleanly" or "robust", no diff restated; the body gives why and the option it beat.
- **Product copy**: promotional words, announced importance ("Important:"), helper text that restates the label (the word pass in `skill://nstack` covers the rest).
- **Briefs to agents**: Nate's words stay verbatim; the agent's own framing around them follows the catalog.

## Source

Adapted from the "Correct and avoid AI stylistic tropes" section of Giuseppe Paleologo's (Gappy) `scholarly-paper-revision` skill ([post](https://x.com/__paleologo/status/2116602494428299632)), generalized from mathematical papers to what agents write, with patterns 4, 18, 22's "the real", 23's self-praise, 27 and 29 added from Nate's agents' reports. His section draws on [Wikipedia's guide to signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) and studies of [changing word frequencies](https://aclanthology.org/2025.findings-acl.657/) and [scientific writing style](https://aclanthology.org/2026.lrec-1.142/); those describe patterns across many documents and cannot show who wrote a given passage.
