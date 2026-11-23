# Genres, docs structure, and voice work

Load this reference when writing a specific document type (docs, README, copy, public essays) or building/tuning a personal voice skill.

## Documentation (Diátaxis + Google Developer Docs)

Pick the reader and their job before writing a line. Do not mix types on one page:

- **Tutorial** (learning): walk a beginner through one working result from start to finish; omit edge cases and alternatives.
- **How-to** (doing a task): numbered steps for one concrete goal, condition before command (*"To reset the cache, run..."*, not *"Run ... to reset the cache"*).
- **Reference** (looking up): exact flags, fields, signatures, defaults, and return shapes, matching the code. Check the working system before writing; separate implemented behavior from proposals.
- **Explanation** (understanding): why the system is built this way, tradeoffs, and mental models.

Standing doc rules:
- Write for someone reading cold a year from now who never saw the chat. Never write *"used to be"*, *"now uses"*, *"as requested"*, or *"preserve existing behavior"* (state the actual compatibility constraint instead). History belongs in commit messages and `CHANGELOG.md`.
- Restraint beats erudition: make the next step obvious without proving how much the author knows.
- Formatting mechanics: sentence case on all headings (under ~65 chars, no trailing period); numbered lists only for ordered sequences; descriptive link text (never *"click here"*); American English.

## Reports, catch-ups, and DONE.txt

- **Two registers:** internal agent shorthand stays in scratchpads and tool calls. The report for Nate is written anew in plain English, restoring causality and real names so he carries zero translation cost.
- **Inverted pyramid:** outcome and whether the checks hold first, then evidence with tappable links, then **Needs Nate** (only his decisions, with options and recommended defaults), then defaults chosen and side effects the diff won't show.
- **Quick-reference / call sheets for Nate:** only what he does not already know (numbers, names, questions, their product terms) in a few large visual items. Never echo his own background back to him.

## Commit messages and PR descriptions

- Subject: what changed, in plain imperative English. No *"This commit..."*, no *"cleanly"* or *"robust"*.
- Body: why this change was made and what option it beat, citing the failure or evidence. Never restate the diff or reference the chat (*"per our discussion"*).

## Product copy and runtime model text

Apply the **5-question completeness test** before tweaking wording (most copy problems are clarity problems):
1. What changed?
2. Who cares?
3. What pain gets solved?
4. What proof makes it believable?
5. What should the reader do next?

Runtime lists, feeds, cards, and digests (titles, summaries, status rows):
- Cut every string the user would not miss (eyebrow labels, subtitles restating titles, helper text restating labels).
- Open each item with the words that set it apart: subject then verb, or verb alone when every item shares the subject.
- Hold one template and one term per concept across every row so a difference in length or wording always signals meaning. State that template explicitly in any prompt that generates the rows.

## Public essays, posts, and personal voice

- For long-form human prose Nate wants in his preferred essay register (articles, talk scripts, project pages, explainers, long emails), also check `styles/clear-human` in nbrain (`skill_get {"name": "styles/clear-human"}`).
- **Brief-first drafting:** never prompt a model with one line to produce a full essay ("plausible filler in a fake voice"). Put the real thesis, facts, numbers, quotes, and anecdotes into a style-stripped brief first, draft from that brief, then run the edit pass. Rule of thumb: input substance should exceed output length (distillation ratio > 1).
- **Named arcs beat generic five-paragraph structure:** open on friction, show the messy middle with real artifacts, name the pattern, and end on a usable takeaway; or open on frustration, show why the standard fix failed, describe the breakthrough with exact numbers, and list adoption steps.
- **Personal voice skills (when building or tuning one):**
  - Train from 12–25 recent pieces in **one** format; recency beats volume, and short tweets/emails harm long-form transfer.
  - Keep a **rejection graveyard** (*"sounds like me, but I'd never publish this"*) beside positive exemplars—sharp rejection criteria prevent caricature better than longer positive prompts.
  - Hand-written style guides often score *worse* than no skill by over-performing tics. Evaluate changes with order-swapped pairwise comparison against real pieces from the same style-stripped brief on a held-out set, and re-tune when changing model families.
  - When drafting social posts or short copy in a personal voice, offering 3–5 materially different angles (closest polish, punchier hook, conversational, proof-led) forces real choice instead of accepting the model's first voice.
