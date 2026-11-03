# SKILL.md skeleton

Fill every section from the session's trace. Delete a section only when it truly has nothing; never pad one.

## Frontmatter

- **name**: the kind of work, lowercase with hyphens: `explainer`, `release-notes`, `bug-triage`. Not the project (`kino2-explainer`) unless it only applies there. Add a qualifier when the first word collides with a neighbour's name.
- **description** (the only part a router reads): what it does and when, in Nate's words, in an opening clause that stands alone; what it covers that its nearest neighbour does not; "Not for …" only against a neighbour that real requests confuse with it. About 200 to 350 characters.
  - Weak: `Guidelines for explainers.`
  - Strong: `Build an interactive explainer page that teaches one system by letting the reader poke it. Use when Nate asks to "explain how X works", "make a teaching page" or "walk me through X visually". Not for reference docs or READMEs; those are nstack-writing.`
- Store extras: the brain's `skill_save` writes `kind`, `source` and `default` into `metadata`; omp reads `hide: true` and `disable-model-invocation: true` (both keep the skill out of the router's list).

## Body

```markdown
# <Title: the kind of work>

<One paragraph: what this produces and the standard it is held to.>

## Use when
- <request shape 1, in Nate's kind of words>
- <3-5 in all>

## Not for
- <adjacent work and the skill or path that handles it>

## The bar
<Nate's own words, quoted, with dates: every request and correction that defined "done".>
- "<quote>" (YYYY-MM-DD)

## Steps
1. <rule>: <why>. <exact value, command or file where there is one>.
<5-15 rules. Each one would have saved real time in the session it came from.>

## Light version
<What to do when the request is small: the two or three steps that matter, and what to skip.>

## Pitfalls
- <what failed in the trace>: <the verified cause>; <what to do instead>.

## Examples
- `examples/<name>.md`: <what it shows>. Load the closest one, not all.

## References
- `references/<file>.md`: <what it holds>. Read it when <condition>.

## Provenance
- <paths of the finished work, the session, the date Nate accepted it>
```

## Exemplars

Each file in `examples/` holds: what it is and where it came from (the request, the path, the date, what Nate said about the result); the artifact or a pointer to it, with screenshots in `assets/` for anything visual; 5 to 15 rules it teaches, each with why and where it does not apply; one to three contrast pairs (the generic default against what was done on the same brief); and a do-not-copy list (its content, names, data, copy, brand values, anything true only for that project).

## Checks before saving

- Body under about 200 lines (hard limit 500); detail moved to `references/`.
- Every rule has a why; every value that matters is exact.
- Every quote is Nate's verbatim words with a date.
- Nothing in it is something a capable agent does without being told.
- Boundaries and the light version are there.
- The routing check in SKILL.md passed.
