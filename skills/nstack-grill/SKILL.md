---
name: nstack-grill
description: Getting on the same page with Nate before work starts, in rounds of numbered questions, each with your recommended answer. Read only when he calls for it (`/nstack grill`, "grill me", "grill this plan"); never start one yourself.
---

# nstack grill

A grill gets Nate and you to one understanding of the important things before anything is built. He calls for one when a wrong reading would cost more than a few rounds of questions; you never start one on your own. For this conversation it replaces nstack's one-batch rule: questions come in rounds until he confirms.

## Before the first round
Read what the topic touches: the code, the ledger, his earlier picks. Facts are your job: anything the code, tools, his data or a quick probe can answer, look up yourself or with a reader, and never ask him. Draft the frame from `skill://nstack` §1 (Outcome, Proof, Keeps, Out, Facts, Decisions); the questions are its gaps.

## Rounds
Lay the open decisions out as a tree: settling one opens the ones that hang off it. A round asks every important decision whose prerequisites are settled; one that depends on a question still open waits for a later round. Important means it changes what he gets: the outcome and how he will judge it, what must not change, what is out, the data that is hard to change later, one-way doors, taste, and the name for a thing when you and he use different words for it. Reversible details are yours: decide them and list them as defaults when you close, not as questions.

Each round is one plain message, not an `ask` or an intent card:

```
**1. <title>**: the question; where there are options, each with what it changes and costs.
→ <your recommended answer, and why in a line>
```

Word each question so "yes" takes your recommendation, so he can answer a round in one line ("1 yes, 2 b, 3 no: …"). A lookup still running holds back only the questions that depend on it; ask the rest now. When an answer conflicts with a fact, a keep or an earlier answer, show the evidence and ask once in the next round. Each round's answers reshape the tree: drop the branches they closed, open the ones they unlocked, then ask the next round.

## Close
Stop when the important branches are settled; details stay yours, and so does anything he waves off ("your call"). Send the frame back in his words: a Decided line for each of his answers, your defaults, and the names you agreed. Wait for his yes. Record the frame at the top of the ledger `local/nstack/<slug>.md` when the work is bigger than one sitting; no glossary, ADR or spec files unless he asks. Agreed names go into the code as written.

Build nothing during a grill. After his yes, carry on with the task under nstack if he gave one (a shape for L/XL work starts from the confirmed frame and does not re-ask it); otherwise stop.
