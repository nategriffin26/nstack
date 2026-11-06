---
name: nstack-writing
description: "Write prose anyone reads beyond a few lines without the habits that read as generated. Covers reports, DONE.txt, research notes, docs, READMEs, commit messages, briefs and product copy, with plain replacements and a self-edit pass."
---

# Writing

The register is set by the floor: write only what someone will act on, with no word Nate would not miss, in precise professional English, leading with what he must judge, in plain words he can read on a phone. This catalog names the habits that break those rules one sentence at a time.

The patterns are cues for judgment, not bans. Change one when it is repetitive, vague, overstated or distracts from the content; keep a contrast, parallel, count, technical term or dash that does real work. One "X, not Y" that heads off a likely misreading stays; five on a page go. Never trade a precise technical word for a simpler wrong one, and never swap a habit for its synonym. Quotes, Nate's own words and source text are never edited.

## The pass
A short text (a reply, a commit message, a few lines) is written with the catalog in mind. A long or saved text (a note, synthesis, report, DONE.txt, doc, README or brief) is drafted, then edited once:

1. Read the draft against the catalog and mark each hit.
2. For each hit, write the plain claim it dressed up: the number, the cause, the source, the next step. A sentence with no claim underneath is deleted.
3. Reread for loss: every fact, qualification, number, link and confidence label is still there, and the required format is intact.

One pass. Polishing in loops flattens the voice and costs more than it returns.

## Catalog

### Structure
1. **Counting for effect.** "One app, two jobs"; "Three reasons:"; "Four facts stand out". A list shows its own length; state a count only when the count is the point, and say what the things are.
2. **Headings as slogans or explanations.** "Verdict: pursue narrowly"; "Structure beats tuning"; "Why"; "How it works". A heading names its topic ("Users", "Network exposure"); the finding goes in a sentence with its evidence.
3. **A bold label on every item**, restated by the sentence after it. Bold only what a skimming reader must find.
4. **Exposition staged as questions.** "So what changed?"; "Which store should own it?". State the answer. A research note's own question stays as its title.
5. **Recaps.** A table, box or summary that repeats the paragraph above it. Keep one form: the table when the reader compares rows, the prose when it explains.
6. **Roadmaps, promises and tour-guide transitions.** "Below I cover…"; "Now for the interesting part."; "With that settled,"; several "Later, only if…" items. Start with the next fact; a deferred item states its trigger once.

### Sentence moves
7. **Corrective framing by reflex.** "The work left is packaging it, not inventing it"; a misconception set up to be knocked down ("It's tempting to think…"); an answer to an objection nobody raised ("That is not an omission."). State what is true and why; keep the contrast only when a reader would plausibly believe the other side.
8. **Announced importance and compression claims.** "This matters because"; "Crucially,"; "The key insight is"; "In one sentence:" before a paragraph. Show the consequence, or give the short answer.
9. **Mirror sentences.** "The standard sets a floor; demand and concept make the outcome." Write each half with its own qualification.
10. **Results turned into morals.** "A watcher is not a backup." after a specific finding. End on the finding and what to do about it.
11. **Decorative participle tails.** ", highlighting the need for…"; ", making it ideal for…". State the causal link or cut the clause.
12. **Arrows and dashes as sentence glue.** "phone → core → OpenRouter returned the right text"; a main point carried inside a pair of dashes. Arrows belong in menu paths (Settings › Voice) and value changes (10.5% → 2.3%); a sentence uses verbs, and an aside that matters becomes its own sentence.

### Words and tone
13. **Agency verbs on things.** Code, models and services that "decide", "want" or "insist": "the recipe wants 16 GPUs". Standard usage stays ("the server refuses the token"); write "needs 16 GPUs".
14. **A recurring metaphor.** "buys", "tax", "moat", "load-bearing", "lands", "quietly" on unrelated points. One apt metaphor is fine; the same device on every point is a habit.
15. **Consultancy and promotional words.** playbook, table stakes, leverage, unlock, north star; seamless, robust, powerful, elegant, clean, comprehensive, game-changing. Name the procedure, or give the evidence: tests passed, milliseconds measured, people who use it.
16. **Moralized precision.** "honest numbers", "honestly", "calibrated", "the real gap". Name the property: measured on the device, a held-out set, the 95th percentile. "Real" stays when it contrasts with a simulator, a mock or a copy.
17. **Vague attribution.** "experts agree"; "best practice is". Name and link the source, mark it as your inference, or cut it.
18. **Filler.** "It's worth noting that"; "Let's dive in"; "Great question"; "I hope this helps"; a closing "challenges and next steps" with no specific problem in it.

### Caveats and repetition
19. **Theatrical, stacked or repeated caveats.** "not a claim that every checklist tool makes this server safe"; "may potentially"; the same limitation in the summary, a section and the close. State the real limit once, where it applies, with one confidence label where it changes the decision.
20. **Process story and internal names.** How the work went ("I mined", rounds, lanes) and names only agents know (lane names, job numbers, ledger files) in prose for Nate. Lead with the result; give method only where it changes how far he can trust it. Citations and evidence paths stay.
21. **Mechanical uniformity.** Every paragraph the same length and shape, a triad by default ("fast, reliable and simple"), ornate words where plain ones serve. Let the content set the shape; one template per list is right when the items are alike.

## Where each kind of text slips
- **Status reports and DONE.txt**: process story, self-praise, arrows, "the real", defensive asides, caveats repeated across lines.
- **Research notes and syntheses**: slogan headings, counted packages, bold leads, theatrical disclaimers, vague attribution, recap tables, internal lane names.
- **Docs and READMEs**: slogan and explaining headings, promotional words, roadmaps; in a README or AGENTS.md, what the project used to do or the conversation behind a change (a CHANGELOG records history by design).
- **Commit messages and PR descriptions**: the subject says what changed; the body gives why and the option it beat. No "This commit…", no diff restated, and no conversation ("as requested", "per our discussion"), because a reader of the log never saw it.
- **Product copy**: promotional words, announced importance ("Important:"), helper text that restates the label. In lists and feeds, including text a model writes at runtime (titles, summaries, digest rows, cards), each item opens with the words that set it apart, subject then verb, or the verb alone when every item shares the subject; every item follows one template and one term per concept, so a difference in length, structure or wording always means something; a prompt that generates such items states that template.
- **Briefs to agents**: Nate's words stay verbatim; the framing around them follows the catalog.

## Source
Adapted from the "Correct and avoid AI stylistic tropes" section of Giuseppe Paleologo's `scholarly-paper-revision` skill ([post](https://x.com/__paleologo/status/2116602494428299632)), which draws on [Wikipedia's guide to signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) and studies of word frequencies; generalized from mathematical papers to what agents write, with patterns added from Nate's agents' reports. Those studies describe patterns across many documents and cannot show who wrote a given passage.
