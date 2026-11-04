Nate typed `/brief` before the request below. Do not do the task. Write the prompt that a fresh agent will receive as its first message and work from. That agent knows only what you write, and it will treat every line as Nate's instruction. Your job is to give it the best possible start toward the end state Nate wants: what he actually needs, the real situation, and what done looks like, without dictating how to get there.

1. Understand the ask. Read his words closely: the outcome he wants and why, what he will do with the result, and what he said not to do yet. Dictated text carries typos and filler; keep the meaning, and keep his exact words for the brief.

2. Look before you write; this is where your effort goes. Read the code, files, docs, git history and earlier work the request touches, and check with a command every fact the brief will state. Find what exists that he may not know about or may have forgotten (an earlier attempt, a related tool, a constraint written down in the repo), what will make the work hard, and what has gone wrong before. Stop when more reading would not change the brief. Do not start the work: no edits, installs or drafts of the deliverable.

3. Find the best route. Think through two or three ways to reach the end state, and what an excellent practitioner would do that the request leaves out. Sort what you know into settled (by his words or by facts you checked), defaults you chose (marked so he can override them), and open choices only he can make. Size the brief to the ask: a question gets a short brief; a multi-part build gets the frame nstack asks for.

4. Write the brief, addressed to the agent. Include each part only if it carries something:
   - Outcome: his words verbatim in quotes, then a sentence or two on what he needs and why.
   - What exists: the verified facts with paths, versions and the commands that showed them; mark anything unverified.
   - Settled: his decisions and your defaults, each marked as which.
   - Open: choices left to the agent's judgment, and the questions only Nate can answer, asked up front in one batch with a recommended default; only those that change the result.
   - Done means: the observable result where he will use it, the evidence to report, and the one-way doors that wait for his yes (spending, sending or publishing as him, deleting).

   Leave the method to the agent unless the method is the point. Add no step, check, deliverable or safeguard that he did not ask for and the work does not need. Do not restate rules the agent already loads (nstack, AGENTS.md); name a skill only where it changes what the agent does.

Your final message is the brief and nothing else: no preface and no notes to Nate. It is sent to the agent verbatim.
