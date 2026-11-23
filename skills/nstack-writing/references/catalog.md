# Prose catalog (patterns and plain replacements)

Editorial cues, not hard bans. Keep a contrast, parallel, count, term of art, or dash when it does real work. One real correction stays; three on a page go. Never swap a tell word for its synonym without fixing the empty claim underneath.

## 1. Grammar, parts of speech, and working-dialect bleed

1. **Uncommon parts of speech (verbified nouns).** Models reward-hack LLM judges by turning nouns into verbs so a sentence stays compact and syntactically ambiguous: *"the root sizes the work"*, *"the check witnesses the invariant"*, *"it gates the merge"*, *"we surfaced the gap"*, *"this impacts latency"*. Use the normal English verb: *"the root sets the size of the fix"*, *"the check proves the invariant"*, *"it blocks the merge"*, *"we found the gap"*, *"this slows latency"*.
2. **Ambiguous noun/verb stacks.** Strings of words that could each be noun, verb, or adjective (*target, witness, claim, audit, check, flag, gate, patch, frame*): *"fix flag check target"*. Unpack into a plain actor, verb, and object so the reader never has to parse grammar twice.
3. **Working-dialect bleed ("agent creole").** Internal shorthand from a long session or subagent run leaking into prose for Nate: *"15/15 green"*, *"gate holds"*, *"spine landed"*, *"ledger clean"*, *"lane 3 converged"*, internal job IDs, or coined labels (*"the switch-back note"*). Write the final report anew for someone who never saw the process: state what changed, what was checked, and what it means, using real names and paths.
4. **Coined concepts explained immediately.** Inventing a catchy label just to define it in the next sentence (*"the comprehension-tax loop"*). State the concrete mechanism instead; coin a term only when the whole piece genuinely rests on one new idea.
5. **Stacked noun phrases and nominalizations.** *"config-validation failure recovery mechanism"* or *"the implementation of the migration"*. Turn the action back into a verb: *"how the config validator recovers when a check fails"*, *"migrating the table"*.
6. **Unclear pronouns and cataphors.** Leading with *"it"*, *"this"*, or *"that"* when the referent is two clauses back or hasn't appeared yet. Name the actual thing.

## 2. Structural hollowness (how LLM drafts differ from human ones)

7. **New nouns without new facts (hollowness).** Each sentence introduces another abstract noun (*"complexity"*, *"alignment"*, *"trust"*, *"velocity"*) without adding a verifiable fact (a number, name, quote, path, or event). Supply the fact or delete the sentence.
8. **Noun avoidance and synonym cycling.** Writing *"I stepped into a corridor. Dark. Narrow."* or rotating *"the agent… the assistant… the model… the system"* to avoid repeating one noun. Repeat the real noun across adjacent sentences; one term per concept.
9. **Dropped proper names and rounded numbers.** Writing *"a user"*, *"several engineers"*, *"many calls"*, or *"thousands"* when the draft has the actual name, file, or count. Keep the specific name and exact number.
10. **Mid-band thesaurus words.** Avoiding both plain everyday words and precise domain terms in favor of showy mid-frequency ones (*"stanza"* for section, *"plum-coloured"* for dark red, *"commence"* for start, *"utilize"* for use). Use the plain word, or the exact technical word defined once if the reader might not know it.

## 3. Structure and formatting

11. **Counting for effect.** *"One app, two jobs"*; *"Three reasons:"*; *"Four facts stand out."* A list shows its own length. State a count only when the number itself is the point.
12. **Headings as slogans or explanations.** *"Verdict: pursue narrowly"*, *"Structure beats tuning"*, *"Why"*, *"How it works"*, *"Key takeaways"*. Use sentence-case topic headings under ~65 characters (*"Network exposure"*, *"Retry limits"*).
13. **Bold lead-in on every bullet.** `**Latency:** Latency dropped from 400 ms to 90 ms.` Bold only literal UI controls (`select Save`) or the one anchor a skimming reader must spot. Open bullets with the subject or verb.
14. **Exposition staged as questions.** *"The result? Faster builds."*, *"So what changed?"* State the answer. Keep a real research question only as a note's title or an actual question for Nate.
15. **Recaps and roadmaps.** A summary box repeating the paragraph above, *"Below I cover…"*, *"With that settled,"*, or a generic *"Challenges and next steps"* close. Keep one form (prose or table, never both for the same facts) and start with the next fact.

## 4. Sentence moves

16. **Corrective framing by reflex.** *"It's not X, it's Y"*; *"The fix is in the template, not in 600 posts"*; *"It's tempting to think…"*; *"That is not an omission."* State X directly. Keep *"not Y"* only when a reader would plausibly assume Y.
17. **Announced importance and faux insight.** *"This matters because"*, *"Crucially,"*, *"The key insight is"*, *"What nobody tells you"*, *"The best part: it learns"*, *"In one sentence:"* before a paragraph. Show the consequence; cut the wind-up.
18. **Mirror sentences and results turned into morals.** *"The standard sets a floor; demand makes the outcome."*; *"A watcher is not a backup."* Write each half with its own evidence and end on the finding or next action, not an aphorism.
19. **Decorative participle tails.** *", highlighting the need for…"*, *", underscoring…"*, *", making it ideal for…"* End the sentence before the comma, or write the actual causal link in its own clause.
20. **Verbless punchline fragments and brachylogy.** *"That's it. That's the whole thing."*, *"Fast. Clean. Simple."* Reserve short fragments for a real turn or emphasis, not default texture.
21. **Copula avoidance and false ranges.** *"serves as"*, *"stands as"*, *"boasts"* → *"is"*, *"has"*. *"From X to Y"* when X and Y aren't endpoints of a real scale → list the items plainly.
22. **Arrows and em dashes as sentence glue.** *"phone → core → OpenRouter returned the text"*; carrying main clauses inside pairs of em dashes. Use verbs in sentences, periods or commas for asides; keep arrows for menu paths (`Settings › Voice`) and value changes (`10.5% → 2.3%`).

## 5. Words, tone, and caveats

23. **Agency verbs on things.** *"The recipe wants 16 GPUs"*, *"the cache decides to evict"*. Standard technical usage stays (*"the server refuses the token"*); otherwise write *"needs 16 GPUs"*, *"evicts after 60 s"*.
24. **Pet metaphors and consultancy/promo words.** Repeated *"buys"*, *"tax"*, *"moat"*, *"load-bearing"*, *"lands"*, *"quietly"*; words like *delve, tapestry, leverage, utilize, seamless, robust, powerful, elegant, comprehensive, pivotal, testament, playbook, unlock, north star*. Replace with the procedure or measurement (tests passed, ms measured, user count).
25. **Moralized precision and confidence tricks.** *"honest numbers"*, *"calibrated"*, *"the real gap"*, *"this is the smoking gun"*. Name the actual property: measured on device, held-out set, p95, verified cause. *"Real"* stays only against a mock, simulator, or copy.
26. **Vague attribution, filler, and chatbot leftovers.** *"experts agree"*, *"studies show"*, *"best practice is"*, *"It's worth noting"*, *"Let's dive in"*, *"Great question"*, *"I hope this helps"*, filler intensifiers (*"genuinely"*, *"truly"*, *"actually"*). Name and link the source, or cut.
27. **Theatrical, stacked, or repeated caveats and UI disclaimers.** *"may potentially"*, *"not a claim that every tool makes this server safe"*, repeating the same limit in the opener, body, and close, or spraying defensive footnotes under charts, cards, and page footers (*"It is not a probability, and neither side is a proof."*, *"No result here is a proof unless…"*, *"Every line is X. Nothing here is Y."*). State a real limit once where it actually changes a decision; keep UI captions and footers free of defensive disclaimers.
28. **Mechanical uniformity and monotone rhythm.** Every sentence 16–18 words, every paragraph three lines, triads by default (*"fast, reliable, and simple"*). Vary sentence length naturally; read high-stakes prose as if aloud to catch cadence collisions.
