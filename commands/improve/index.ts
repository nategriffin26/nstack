/**
 * /improve <prompt>: deepen a prompt before running it, sized to what the result is worth. The model weighs the stakes,
 * names the practitioner Nate would hire for them, the one move the prompt leaves out, the rawest material, the plainest
 * method and one outside check, then rewrites the prompt with that check as evidence to report, a budget and a stop
 * point. With no prompt it takes Nate's most recent request in the conversation.
 *
 * The rewrite is written as Nate's words, which override nstack's proportion rule, so every line it adds is an order:
 * the instructions cap it at one move and one check (an unbounded list of pro moves and validations once ran overnight).
 *
 * A TypeScript command rather than commands/*.md: markdown commands rebuild $ARGUMENTS from quote-aware splitting,
 * which drops every apostrophe and quote mark in the prompt. rawArgs carries the prompt byte for byte.
 */
import type { CustomCommandFactory } from "@oh-my-pi/pi-coding-agent";

const INSTRUCTIONS = `I want a deeper version of this task, sized to what the result is worth. Don't start the task: give me the analysis and the rewritten prompt, then stop.

Deeper means a better starting point, a better method and one real check, for the same goal and deliverable. It does not mean more steps, more checks or more rigor. Every line of the rewrite becomes an order, and my orders override the agent's own sense of proportion, so add only what changes the result.

Open with two lines:
- Stakes: what the result feeds (a decision, something I'll use, something that ships) and what it costs if it's wrong. A reversible choice is cheap to get wrong, so the rewrite settles it quickly and leaves me free to change course later; rigor is for what is costly or hard to undo.
- Practitioner: the specific person I'd hire for exactly this at these stakes, named by what they do ("a staff engineer deciding whether to change their team's review rule"), not "an expert", and not a researcher writing a paper unless the result is a paper.

Then, specific to this task and that person, a few lines each:
1. The move: the one thing they would do that my prompt leaves out and that most changes the result. One, not a list. If my prompt already has it, say so.
2. The material: the rawest source they would start from instead of what has been digested for me (data, code, logs, measurements, the thing itself, rather than summaries, rankings, AI answers or my paraphrase). Name it, where it lives, and whether this session can reach it.
3. The method: the plainest way they would settle it, in their words. Name a tool or technique only when it changes the answer.
4. The check: one thing outside this conversation that could come back wrong, the cheapest one whose result would change what I do. Say what result means it failed.

When a fact you can check quickly would change an answer (whether a source exists, whether a tool is installed, what the repo or file contains), check it instead of guessing, and stop there: checking is not doing the task. Where the rewrite depends on something only I know (access, budget, deadline, a taste call), write it in as an assumption I can edit, not a question to me.

Then rewrite my prompt. Keep my goal, my deliverable and my voice, and make it work pasted into a fresh session. It says what the result is for, points at the material from 2, asks for the move from 1, and ends with the check from 4 as evidence to report, not a gate to clear: if the check fails or comes back mixed, the agent reports that and stops instead of adding analyses until it passes. Leave the method to the agent unless the method is the point. Give it a budget that fits the stakes (time or spend, as an assumption I can edit) and say where it stops and reports. Add no other verification (second reviewers, replays, pre-registered thresholds, held-out data, frozen scripts) and no extra deliverables unless the stakes line calls for them, and then say why in one line. Keep it about as long as my prompt plus the few lines that 1, 2 and 4 add. Put it last, in a fenced text block (a longer fence if the prompt contains one), so I can copy it or say "go" to run it here.`;

/** Fence the prompt with one more backtick than its longest run, so fences inside it cannot close the block. */
function fenced(text: string): string {
	const longest = Math.max(0, ...(text.match(/`+/g) ?? []).map(run => run.length));
	const fence = "`".repeat(Math.max(3, longest + 1));
	return `${fence}text\n${text}\n${fence}`;
}

const factory: CustomCommandFactory = () => ({
	name: "improve",
	description: "Deepen a prompt in proportion to its stakes: one pro move, the rawest source, one outside check, a budget",
	execute(args, _ctx, rawArgs) {
		const prompt = (rawArgs ?? args.join(" ")).trim();
		const target = prompt
			? `My prompt, verbatim:\n\n${fenced(prompt)}`
			: "My prompt is my most recent request in this conversation; if there isn't one, ask me for it in one line.";
		return `${INSTRUCTIONS}\n\n${target}`;
	},
});

export default factory;
