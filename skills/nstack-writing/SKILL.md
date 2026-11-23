---
name: nstack-writing
description: "Write prose anyone reads beyond a few lines without AI tropes, working-dialect shorthand, or verbified nouns. Covers reports, DONE.txt, research notes, docs, READMEs, commit messages, briefs, and product copy, with an offline linter and one edit pass. Avoid when brevity suffices; not for code or site reviews."
---

# Writing

Write prose Nate or another person can scan on a phone: plain words, concrete facts, no internal agent shorthand, and no habits that read as generated.

The standing rules in `omp-rules.md` set the floor (write only what someone will act on, precise professional English, domain terms over slang). This skill carries the craft, the pass, and the offline linter (`scripts/prose_lint.py`).

## Core principles

1. **Front-load everything.** Use the inverted pyramid at every level: document, section, paragraph, sentence. Put the outcome, answer, or action first, then the evidence, then background only if it changes a decision.
2. **Two languages: working vs. reporting.** Agents compress long runs into internal shorthand (*"15/15 green"*, *"gate holds"*, *"lane 3 converged"*, coined nicknames). Keep that inside working notes and tool calls. Write human-facing output anew so a reader who never saw the session carries zero translation cost.
3. **Normal English parts of speech.** Never verbify nouns or stack noun/verb-ambiguous words (*"the root sizes the work"*, *"the check witnesses the invariant"*, *"fix flag check target"*). Use the ordinary verb (*"sets the size of"*, *"proves"*, *"blocks"*, *"affects"*).
4. **Every sentence earns its space with a fact.** A sentence that adds a new abstract noun without a new concrete fact (name, number, cause, quote, path, or next step) is hollow: supply the fact or cut it. Keep real proper names and exact numbers instead of *"a user"* or *"several"*. Repeat the same noun across adjacent sentences instead of synonym-cycling.
5. **Precision guardrail and escape hatch.** Prefer plain words over unexplained jargon, and test tough phrasing against a smart non-native English reader. Keep an established technical term when it is the most precise choice, and define it in one sentence if the reader may not know it. Never edit quotes, Nate's own words, code, identifiers, commands, or required formats for style. Break any rule here before writing something awkward or barbarous (Orwell).
6. **Formatting is structure, not emphasis.** Use sentence case in headings (under ~65 chars, naming the topic). Skip bold and italics for emphasis; bold only literal UI controls (`select Save`) or the one anchor a skimming reader must spot. Vary sentence length naturally (aim for ~15–22 words, rarely over 30) and keep one idea per short paragraph (1–4 sentences).

## The pass (tiered by stakes)

Heavy style rules during drafting flatten substance and create caricature. Separate substance from editing when the text is longer than a few lines:

- **Short text** (a chat reply, a commit message, a few lines): write directly in plain English with the core principles in mind. No separate pass needed.
- **Saved or long text** (report, `DONE.txt`, research note, doc, README, brief, email draft, product copy):
  1. **Draft for substance first** (facts, numbers, causes, links, decisions) without fussing over style.
  2. **Run the linter** on the file (or stdin):
     `python3 ~/Projects/nstack/skills/nstack-writing/scripts/prose_lint.py <file>`
     High-precision `[flag]` hits are almost always fixed; `[review]` hits are judgment calls.
  3. **Do one edit pass** against `references/catalog.md`: replace each real hit with the concrete claim underneath (number, cause, source, next step) or delete the sentence. Never swap a tell word for its synonym.
  4. **Check for loss:** every fact, qualification, number, link, confidence label, and required format is intact.
  One edit pass only; polishing in loops flattens voice.
- **High-stakes public prose** (blog posts, essays, launch copy, personal site pages):
  1. Write a style-stripped **brief** first (thesis, real facts, numbers, quotes, anecdotes; input substance > output length).
  2. Draft from the brief (for Nate's essay voice, also load `styles/clear-human` from nbrain).
  3. Run `prose_lint.py` plus one fresh-pass edit (or a separate editor subagent with only the draft, the brief, and this skill so working-session dialect cannot bleed through), and read it as if aloud for rhythm.

## Highest-frequency traps (quick list)

Full 28-item catalog with plain replacements lives in `references/catalog.md`. Watch these on every draft:

- **Uncommon verbifications & POS stacks:** *"sizes the work"*, *"witnesses the invariant"*, *"gates the merge"*, *"surfaces the gap"*, *"impacts latency"*, *"fix flag check target"*.
- **Working-dialect bleed:** *"all green"*, *"spine landed"*, *"the gate holds"*, *"as requested"*, *"used to be"*, internal lane/job/ledger names.
- **Hollowness & avoided nouns:** new abstract nouns with no new verifiable fact; *"several/many"* where you have the number; synonym cycling instead of repeating the real noun.
- **Reflexive contrasts & wind-ups:** *"It's not X, it's Y"*, *", not in 600 posts"*, *"Here's the thing:"*, *"This matters because"*, *"Crucially,"*, *"The result? ..."*, *"That's it."*
- **Participle tails & copula avoidance:** *", highlighting/underscoring/ensuring…"*; *"serves as / stands as"* → *"is"*.
- **Consultancy & promo filler:** `"delve"`, `"tapestry"`, `"leverage"`, `"utilize"`, `"seamless"`, `"robust"`, `"powerful"`, `"elegant"`, `"comprehensive"`, `"pivotal"`, `"testament"`, `"playbook"`, `"unlock"`, `"load-bearing"`, `"quietly"`, `"smoking gun"`, `"honest numbers"`.
- **Formatting tells:** bold-lead bullets restated by the next sentence, slogan/explaining headings (*"Why"*, *"How it works"*, *"Verdict: …"*), em dashes carrying main clauses, arrows replacing verbs in prose, uniform sentence lengths and default triads.

## References

- `references/catalog.md`: the full 28-item pattern catalog with plain replacements. Read during the edit pass on long or saved text.
- `references/genres.md`: rules by document type (Diátaxis + Google Dev Docs for documentation, reporting-layer rules, commit messages, the 5-question copy test + runtime lists, and brief-first / voice-skill guidance). Read before writing docs, copy, or public pieces.
- `scripts/prose_lint.py`: offline deterministic prose linter (`python3 scripts/prose_lint.py <file>` or `--json`).

## Provenance

Built from Nate's standing writing rules and complaints ("word salad… filled with llm-isms", 2026-11-14; "REMOVE ALL EXTRANEOUS TEXT", 2026-11-17). Draws on his X bookmarks: Misha Sinitcyn and Dmitry Rybin on verbified nouns and POS ambiguity, ungetsuli on working-dialect bleed, emubrigadier on LLM twins, Giuseppe Paleologo's `scholarly-paper-revision`, GOV.UK and Google Developer Docs, Orwell, Diátaxis, Peter Yang's `no-ai-slop`, Ian Nuttall's `seo lint`, Dan Shipper and hammer_mt on brief-first drafting and voice evals, and Dave Kiss and astral-sh/uv on zero chat-leak. Full links live in `README.md`.
