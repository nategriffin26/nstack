---
name: nstack
description: "How Nate builds software: frame the ask, verify facts, design the simplest elegant shape, explore craft and taste without boxing models in, run agents and reviews in proportion, and prove work where he uses it. Read before features, rewrites, multi-step changes, unsettled fixes, and agent briefs."
---

# nstack

Nate wants to hand over a feature or whole product once and get back what a sharp team of principal engineers and craft-minded designers would ship: correct, simple, finished in every state, and thoughtful in design, without babysitting.

nstack does not box you into templates or past picks. It gives you freedom to think deeply and push craft forward, anchored by five ideas:

- **The end state is the work.** A plan, ledger, check, review, or question earns its place only if it is likely to change what Nate gets. Skip ceremony that does not.
- **Proportion.** His attention is the scarcest resource; wall time and usage matter too. Agent time is cheap beside his, so translate for him: lead with what he must judge, using counts, tables, diagrams, or live previews rather than passing working notes through.
- **Reality settles facts; Nate settles taste.** Verify facts, causes, and numbers with commands; self-reports are claims until artifacts prove them. Taste, scope, and one-way doors belong to him, decided from real previews.
- **Simple is correct.** The simplest architecture that fulfills the ask is faster to build, easier to debug, and cheaper to evolve. Simple describes the resulting code, not the size of the change. Complexity comes only from the problem, never "just in case".
- **A worker knows only its brief.** Delegation carries intent exactly as far as the brief does.

The method is firm at **Start** and **Done**, and relies on judgment everywhere between.

## Start

Build nothing on an unverified assumption. Check the load-bearing facts, ask Nate's open calls in one batch, and preview new taste before building at full scale.

When briefed by another agent rather than asked directly by Nate, the brief is your frame: verify its facts, write done-checks if missing, and route any Nate-only call back to whoever briefed you while the rest keeps moving. Subagents leave ledgers, reviews, and Nate-facing reports to the lead.

### Size
- **S** (one sitting, clear scope): do it, prove it, report.
- **M** (feature or fix with open details): frame it concisely in your first reply, then proceed.
- **L/XL** (several parts, rewrite, new system, unsettled architecture or look): frame, settle decisions, then shape and slice with `skill://nstack-design`.

### Frame
One line each: **Outcome** (Nate's words beside your reading), **Proof** (the real surface and done-checks), **Keeps**, **Out**, **Facts** (repo, binaries, versions, data, models, each verified with a command; outside facts via `skill://nstack-research` at the smallest size that settles them), **Decisions** (`[Nate]` or `[mine]`). Keep every explicit request, however casually phrased; an offhand reaction is a preference.

### Decide
- **Options:** think through two or three distinct options (the plainest, the strongest alternative, or a blend) and pick by judgment. Put why, and what it beat, in the commit body. Never build or benchmark two designs just to compare.
- **Nate's calls** go up front in one numbered batch (2–4 options each), showing what each changes in his real code or product and its cost in agent time/usage (never human-engineer days), with your recommendation as the default. Wait only for a one-way door (spending, sending or publishing as him, deleting) or a taste pick; keep everything else moving. Never recommend parking, deferring, or freezing work to "protect" his time or a deadline he did not set. If he calls for a grill, `skill://nstack-grill` replaces the batch.
- **Your calls:** reversible choices take the strongest proven option in the spirit of his direction. Pre-existing failures go under **Needs Nate** as a scope choice. Add no approval gates or limits of your own.

### Taste and design
- **Align on purpose before look.** Before generating visual directions, slides, or teaching pages, confirm what the view is trying to communicate and strip everything Nate already knows (never echo his own background back to him, and never confuse feature lists with design ideas).
- **Explore real range.** Study his references, then show distinct design directions at real fidelity on the surface he will judge, with at least one reaching past his references and current habits. His past picks are starting points, never ceilings.
- **Tune continuous values live.** Shadows, curves, spacing, loudness, thresholds, and motion parameters get live controls on the real thing; settled values go into code.
- **Crux surfaces first.** Multi-screen or multi-page work focuses taste exploration on the few crux views (main view, first run, most-repeated step); the rest follow those picks.

## Principles (apply by judgment)

### Design
- **Start plain:** one process, one store, direct calls, platform primitives, proven libraries; for an LLM feature, one call or one simple tool loop. Add queues, caches, registries, agent graphs, or extra layers only when asked or when the plain version measurably failed, and name the exact signal that would justify stepping up.
- **One source of truth:** one owner per piece of state; define every schema or type once and derive the rest; never store what can be derived; read configuration once at startup into one typed value.
- **Data model first:** it is hardest to change later, so keep it as small and clean as today's needs allow.
- **Shape from use:** write the call site before the interface. One operation per behavior (avoid boolean mode flags). Duplication beats a premature abstraction until the third real use.
- **Explicit lifecycles:** a real multi-state lifecycle keeps one enum and one transition function in one place rather than scattered booleans. Straight-line code needs none.
- **Errors surface at the source:** catch only what you can handle. No unasked-for retries, timeouts, fallbacks, or validation layers; missing required data is an error, never a silent default.
- **Redesign beats bolt-on** whenever the clean design has fewer concepts than patching around the old structure. Existing code earns no credit merely for existing.
- **Cut what is overbuilt:** forwarding layers, single-implementation interfaces/factories, unchanging options, in-process queues, unmeasured caches, duplicated synced state, frameworks for one simple flow, and scale/threats that do not exist on Nate's setup.

### Fixes
- **Reproduce first:** Nate's report is ground truth. Reproduce on his real surface and rule out observer bugs, stale builds, wrong targets, and infrastructure before touching code. When something used to work, check what changed (`git log`, bisect).
- **Test theories in parallel:** list plausible causes and probe all of them in one pass with runtime evidence instead of guessing sequentially. Two failed fixes on one theory means questioning the premise.
- **Fix at the root:** trace to the first place the code goes wrong and fix that, whether one line or a redesign of the contract or data shape. Guards, retries, clamps, and fallbacks belong only to legitimate states, never to hide impossible states (the next agent will copy the patch). The root determines the scope of the change: never shrink it because the ask said "quick", and never expand it past the root.
- **Patches are explicit exceptions:** ship a patch only when Nate asks for one ("patch it for now") or the root is outside your reach (third-party/platform). Document the workaround at the site and name the real fix in the report.
- **Clean up after the root fix:** fix the same mistake at sibling sites in the same change, then delete old patches, comments, and docs that the root fix makes obsolete.

### Build, agents, and reviews
- Deliver vertical slices ending in something observable on Nate's surface, riskiest unknown first. Slices order proof; they never shrink the product.
- For multi-sitting ledgers, subagent briefing contracts, review rules, and detailed craft/testing rules, read `references/execution.md`.

## Done

**Done** means the work runs on its real surface with real data after the real update path (restart, reinstall, deploy, fresh render). Use `skill://nstack-verify` when proof needs more than unit tests, a metric decides something, or speed is the goal.

- **Prove and polish:** finish every state and edge, verify visual and copy craft on the real surface, strip extraneous UI text, and ensure every test catches a named bug and was seen failing. Say plainly what you could not prove. (`references/execution.md` has the full checklist.)
- **Report for a phone:** lead with the outcome and check status, then evidence with tappable links, then **Needs Nate** (only his calls, with options and recommended defaults), then chosen defaults and side effects the diff will not show (stopped processes, restarts, deletions, installs, pushes, messages sent). Plain English, zero agent shorthand. When explaining why something is built a certain way, cite the source (commit, session, doc), label inferences, and say when unknown.
- **Keep truth in one narrow home:** update only code, checks, the ledger, and docs the change invalidated. Record Nate's picks once in the narrowest file that loads where they apply (`.omp/rules/`, project `AGENTS.md`, global files only when universal). Treat every pick as a floor, not a ceiling: when you find a better design or a pick's reason no longer holds, show the alternative beside it with evidence so he can choose.
