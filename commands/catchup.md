---
name: catchup
description: Catch Nate up, teach how or why something works, or re-explain your last message plainly. /catchup [how/why <thing> | what he wants clearer]
---
Follow `skill://nstack` §6 (Report). Do no new work, change no code, and change no conclusions.

- Empty, "catch me up" or "where are we": say first how many things need him, then what changed since his last message that matters to him, most important first, then each decision with options and your recommendation, and what is still running.
- How or why something works: answer in the first two sentences, grounded in the code or system you read or ran, with one concrete example running through it. The code shows what it does, not why; reasons come from history (commits, `git log -S`, PRs, the ledger, the agent session that made the change, his messages): cite what states a reason, label an inferred one, and say when the reason is unknown. Check any guess in his question like a hypothesis. End with what it means for the decision in front of him.
- Otherwise re-explain your most recent message in plain words, outcome first, centred on what he named.

Request: $ARGUMENTS
