/**
 * /brief <request>: a briefing agent reads Nate's request and the code, docs and history it touches, and writes the
 * first message for the agent that does the work; that message is then sent in this session as his prompt.
 *
 * The briefer is a headless `omp -p` on this session's model and thinking level, in this session's directory, with
 * the instructions in brief.md beside this file. tools/brief_eval.py runs the same instructions the same way
 * (`--arm brief:shipped`) against replays of Nate's past requests; local/evals/brief holds the measurements behind
 * this version of the instructions. Its steps show in the status line while it works; it keeps no session of its own.
 */
import { readFileSync, realpathSync } from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

const STATUS = "brief";
const INSTRUCTIONS = path.join(path.dirname(realpathSync(fileURLToPath(import.meta.url))), "brief.md");

/** Fence the request with one more backtick than its longest run, so fences inside it cannot close the block. */
function fenced(text: string): string {
	const longest = Math.max(0, ...(text.match(/`+/g) ?? []).map(run => run.length));
	const fence = "`".repeat(Math.max(3, longest + 1));
	return `${fence}text\n${text}\n${fence}`;
}

type Block = { type: string; text?: string; arguments?: { i?: unknown } };
type Message = { role?: string; content?: string | Block[] };

function textOf(message: Message): string {
	if (typeof message.content === "string") return message.content;
	return (message.content ?? []).flatMap(b => (b.type === "text" && b.text ? [b.text] : [])).join("\n");
}

/** A brief that arrives as one fenced block is sent as its contents. */
function unwrap(brief: string): string {
	const m = /^(`{3,})[\w-]*\n([\s\S]*)\n\1$/.exec(brief.trim());
	return m ? m[2] : brief.trim();
}

export default function brief(pi: ExtensionAPI) {
	pi.registerCommand("brief", {
		description: "Have an agent investigate and write the brief for your request, then work from that brief",
		async handler(args, ctx) {
			const request = args.trim();
			if (!request) {
				ctx.ui.notify("Usage: /brief <request>", "warning");
				return;
			}
			const model = ctx.models.current();
			if (!model) {
				ctx.ui.notify("/brief needs a model selected in this session", "error");
				return;
			}
			const prompt = `${readFileSync(INSTRUCTIONS, "utf8").trim()}\n\nNate's request, verbatim:\n\n${fenced(request)}`;
			await ctx.waitForIdle();
			ctx.ui.setStatus(STATUS, "Briefing");
			const child = Bun.spawn(
				[process.execPath, "-p", "--no-session", "--mode", "json", "--wait-async", "--model",
					`${model.provider}/${model.id}`, "--thinking", pi.getThinkingLevel() ?? "off", prompt],
				{ cwd: ctx.cwd, stdout: "pipe", stderr: "pipe" },
			);
			let text = "";
			let pending = "";
			const decoder = new TextDecoder();
			try {
				for await (const chunk of child.stdout) {
					pending += decoder.decode(chunk, { stream: true });
					let newline = pending.indexOf("\n");
					while (newline >= 0) {
						const line = pending.slice(0, newline);
						pending = pending.slice(newline + 1);
						newline = pending.indexOf("\n");
						if (!line.startsWith("{")) continue;
						const event = JSON.parse(line) as { type?: string; message?: Message };
						if (event.type !== "message_end" || event.message?.role !== "assistant") continue;
						const content = Array.isArray(event.message.content) ? event.message.content : [];
						const intent = content.findLast(b => b.type === "toolCall" && typeof b.arguments?.i === "string");
						if (intent) ctx.ui.setStatus(STATUS, `Briefing: ${intent.arguments?.i}`);
						if (textOf(event.message).trim()) text = textOf(event.message);
					}
				}
				const code = await child.exited;
				if (code !== 0 || !text.trim()) {
					const stderr = (await new Response(child.stderr).text()).trim().split("\n").slice(-3).join(" ");
					ctx.ui.notify(`/brief: the briefer ${code !== 0 ? `exited ${code}` : "wrote no brief"}${stderr ? `: ${stderr}` : ""}`, "error");
					return;
				}
			} finally {
				child.kill();
				ctx.ui.setStatus(STATUS, undefined);
			}
			pi.sendUserMessage(unwrap(text));
		},
	});
}
