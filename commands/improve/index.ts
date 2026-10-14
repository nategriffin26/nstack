/**
 * /improve <prompt>: deepen a prompt before running it. The model names the practitioner who is best at the task,
 * what they would do that the prompt does not ask for, the rawest material they would start from, their methods and
 * tools, and an outside check, then rewrites the prompt to ask for exactly that. With no prompt it takes Nate's most
 * recent request in the conversation.
 *
 * A TypeScript command rather than commands/*.md: markdown commands rebuild $ARGUMENTS from quote-aware splitting,
 * which drops every apostrophe and quote mark in the prompt. rawArgs carries the prompt byte for byte.
 */
import type { CustomCommandFactory } from "@oh-my-pi/pi-coding-agent";

const INSTRUCTIONS = `I want a deeper version of this task, not a bigger one. Don't start the task: give me the analysis and the rewritten prompt, then stop.

Deeper keeps my goal and my deliverable and gets there from better inputs, with better methods, checked by something outside this conversation. Bigger adds deliverables, scope or length; don't.

Open with one line naming the field and the specific practitioner who is best at exactly this kind of work: "a forensic accountant who audits early-stage startups", not "an expert". If the task crosses fields, pick the one whose judgment decides whether the result is good. Then, specific to this task and that person:

1. What would they do here that I'm not asking for? The move they make by default that my prompt leaves out: the question they settle first, the failure they guard against, the baseline they compare against.
2. What is the rawest material they would start from, instead of what has already been digested for me? The data, documents, code, logs, measurements, recordings or the thing itself, rather than summaries, reviews, rankings, dashboards, AI answers or my own paraphrase. Name it, where it lives, and whether this session can reach it.
3. What specific methods and tools would they use? Named techniques, instruments, software and standards, the way they would say them, not "analyze carefully".
4. What, other than you or me, would show the result is right? Something outside this conversation that could come back wrong: a test, a measurement, a reproduction, held-out ground truth, a market price, a standard it must meet, an independent reviewer, what happens when it meets the real world. Say what result would mean it failed.

When a fact you can check quickly would change an answer (whether a source exists, whether a tool is installed, what the repo or file actually contains), check it instead of guessing, and stop there: checking is not doing the task. Where my prompt already does one of these, say so in a line rather than inventing depth. Where the rewrite depends on something only I know (access, budget, deadline, a taste call), write it into the prompt as a stated assumption I can edit, not a question to me.

Keep the four answers to a few lines each: concrete nouns, no preamble.

Then rewrite my prompt to ask for exactly that. Keep my goal and deliverable, write it in my voice, and make it self-contained so it works pasted into a fresh session. It asks for the move from 1, starts from the material in 2, uses the methods and tools in 3, and is done when the check in 4 passes, saying what counts as failure. Make it as long as the depth needs and no longer. Put it last, in a fenced text block (a longer fence if the prompt contains one), so I can copy it or say "go" to run it here.`;

/** Fence the prompt with one more backtick than its longest run, so fences inside it cannot close the block. */
function fenced(text: string): string {
	const longest = Math.max(0, ...(text.match(/`+/g) ?? []).map(run => run.length));
	const fence = "`".repeat(Math.max(3, longest + 1));
	return `${fence}text\n${text}\n${fence}`;
}

const factory: CustomCommandFactory = () => ({
	name: "improve",
	description: "Deepen a prompt: the pro's move, rawest sources, methods and tools, an outside check, then the rewrite",
	execute(args, _ctx, rawArgs) {
		const prompt = (rawArgs ?? args.join(" ")).trim();
		const target = prompt
			? `My prompt, verbatim:\n\n${fenced(prompt)}`
			: "My prompt is my most recent request in this conversation; if there isn't one, ask me for it in one line.";
		return `${INSTRUCTIONS}\n\n${target}`;
	},
});

export default factory;
