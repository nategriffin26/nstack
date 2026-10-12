---
name: nstack-teach
description: Explain how something works or why it is built that way, grounded in the real code and system, plainly enough for Nate to decide with it. Use for "how does", "why", "explain", "teach me", and Dross teach tasks.
disable-model-invocation: true
---

# nstack teach

The goal is that Nate understands enough to judge and decide, not that he receives everything you found.

## Method
1. Answer the question he asked in the first two sentences.
2. Ground every claim in the real thing: read the code, run it, or check the system. Mark anything you inferred rather than observed.
3. For a "why", the code shows what it does, not why it was built that way. The reasons live in history: commits and their diffs (`git log -S`, `git blame`), PRs, the ledger, notes, Nate's own messages. Cite what states a reason; label a reading you inferred from the pattern; say plainly when the reason is unknown and what you searched. If his question carries a guess ("I assume it's for speed"), check it like any other hypothesis.
4. Start from what he already knows (his projects, his terms) and add one layer at a time.
5. Use one concrete example that runs through the explanation: a real request, file, or value moving through the system.
6. Draw a diagram only when the structure is the point: flow, ownership, or dependencies.
7. End with what this means for the decision in front of him, if there is one.

## Do not
- Change code while teaching, unless he asks.
- Dump file lists, call chains or every finding. Choose what changes his understanding.
- Hedge every sentence. State what is true, and say plainly where you are unsure.
