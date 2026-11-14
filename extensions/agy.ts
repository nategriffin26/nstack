/**
 * The `agy` provider: a subagent whose model runs inside Google's Antigravity CLI.
 *
 * Each omp session on an `agy/<model>` model drives one unmodified `agy acp` process over the Agent Client Protocol
 * (JSON-RPC lines on stdin/stdout). agy signs in, holds the credentials, runs its own tools in the session's working
 * directory and bills the Antigravity plan; omp never sees a Google token or calls a Google endpoint. One omp turn is
 * one agy prompt, run to completion: agy's tool calls and thoughts stream back as thinking, its reply as text, and when
 * the session has omp's `yield` tool (a task subagent) the reply is handed to it, so the child finishes in one turn.
 * Later turns (a follow-up, a rejected yield) continue the same agy conversation with only what is new.
 *
 * agy runs in its `auto` mode: edits and commands it judges safe go ahead; anything it would ask about is refused,
 * because nobody can answer in a headless run, and the refusals are listed in the result.
 */
import { AssistantMessageEventStream } from "@oh-my-pi/pi-ai";
import type { AssistantMessage, TextContent, ThinkingContent, ToolCall } from "@oh-my-pi/pi-ai";
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import type { FileSink, Subprocess } from "bun";
import { realpathSync } from "node:fs";
import { homedir } from "node:os";
import * as path from "node:path";

const PROVIDER = "agy";
const API = "agy-acp";
const EFFORTS = ["low", "medium", "high", "xhigh"] as const;
type Effort = (typeof EFFORTS)[number];

/** Appended to agy's own system prompt; the brief arrives as the user prompt. */
const WORKER_PROMPT = [
	"You are working as a delegated subagent for another coding agent, which reads your final reply as your result.",
	"Do exactly what the brief asks, inside the working directory, and stop when it is done.",
	"Nobody can answer questions or approve actions during the run: anything that needs approval is refused, so take",
	"another route or say in your reply that it is blocked.",
	"End with a short report: the outcome, the files you changed, the evidence that it works, and anything you could not do.",
].join(" ");

/** `agy` on PATH, else where Google's installer puts it. */
function agyBinary(): string {
	return Bun.which("agy") ?? path.join(homedir(), ".local/bin/agy");
}

/** agy inherits omp's environment minus Google API keys, so it bills the signed-in plan, never a key. */
function childEnv(): Record<string, string> {
	const env: Record<string, string> = {};
	for (const [k, v] of Object.entries(process.env)) if (v !== undefined) env[k] = v;
	delete env.GEMINI_API_KEY;
	delete env.GOOGLE_API_KEY;
	return env;
}

// ---------- prices ----------

/** USD per million tokens. Gemini caching is implicit, so a cache write costs nothing extra. */
export interface Price {
	input: number;
	output: number;
	cacheRead: number;
	cacheWrite: number;
}

/** A price change at midnight US Pacific, as Google states its dates. */
const DEC_1_2026 = Date.UTC(2026, 11, 1, 8);
const JAN_1_2027 = Date.UTC(2027, 0, 1, 8);
const ARGON_TIER: { from: number; price: Price }[] = [
	{ from: 0, price: { input: 2, output: 10, cacheRead: 0.1, cacheWrite: 0 } },
	{ from: DEC_1_2026, price: { input: 4, output: 20, cacheRead: 0.2, cacheWrite: 0 } },
];

/**
 * What each agy model's tokens would cost on the pay-per-token API, so omp's cost views show the plan's value; the plan
 * itself bills nothing per token. Gemini: ai.google.dev/gemini-api/docs/pricing (read 2026-11-13). Claude: Anthropic's
 * list prices. GPT-OSS 120B: OpenRouter's price, since Google lists none for it. Keyed by agy's model id without effort.
 */
const PRICES: Record<string, { from: number; price: Price }[]> = {
	"gemini-4-carbon": ARGON_TIER,
	"gemini-4-argon": ARGON_TIER,
	"gemini-pro-orchestrator-g1-pro": ARGON_TIER,
	"gemini-4-hydrogen": [{ from: 0, price: { input: 1.5, output: 7.5, cacheRead: 0.075, cacheWrite: 0 } }],
	"gemini-3.8-flash": [
		{ from: 0, price: { input: 0.75, output: 3.75, cacheRead: 0.075, cacheWrite: 0 } },
		{ from: JAN_1_2027, price: { input: 1.5, output: 7.5, cacheRead: 0.15, cacheWrite: 0 } },
	],
	"claude-opus-5-5": [{ from: 0, price: { input: 4, output: 20, cacheRead: 0.2, cacheWrite: 5 } }],
	"claude-sonnet-5-5": [{ from: 0, price: { input: 2, output: 10, cacheRead: 0.1, cacheWrite: 2.5 } }],
	"gpt-oss-120b": [{ from: 0, price: { input: 0.15, output: 0.6, cacheRead: 0.075, cacheWrite: 0 } }],
};

/** The price in force at `at` (ms since epoch), or undefined for a model with no listed price. */
export function priceOn(modelId: string, at: number): Price | undefined {
	return PRICES[modelId]?.findLast(step => step.from <= at)?.price;
}

// ---------- models ----------

export interface AgyModel {
	id: string;
	name: string;
	efforts: Effort[];
}

/** `agy models` prints `<id>\t<name>` per model; ids ending in an effort are one model at several efforts. */
export function parseModels(output: string): AgyModel[] {
	const models = new Map<string, AgyModel>();
	for (const line of output.split("\n")) {
		const [id, name] = line.split("\t");
		if (!id || !name) continue;
		const m = id.match(/^(.+)-(low|medium|high|xhigh)$/);
		const base = m ? m[1] : id;
		const model = models.get(base) ?? { id: base, name: name.replace(/ \((Low|Medium|High|XHigh)\)$/, ""), efforts: [] };
		if (m) model.efforts.push(m[2] as Effort);
		models.set(base, model);
	}
	for (const model of models.values()) model.efforts.sort((a, b) => EFFORTS.indexOf(a) - EFFORTS.indexOf(b));
	return [...models.values()];
}

async function listModels() {
	const proc = Bun.spawn([agyBinary(), "models"], { stdout: "pipe", stderr: "pipe", env: childEnv(), cwd: homedir() });
	const [out, err] = await Promise.all([new Response(proc.stdout).text(), new Response(proc.stderr).text()]);
	await proc.exited;
	const models = parseModels(out);
	if (models.length === 0) throw new Error(`agy models listed nothing: ${(err || out).trim() || `exit ${proc.exitCode}`}`);
	return models.map(model => {
		const price = priceOn(model.id, Date.now());
		return {
			id: model.id,
			name: `${model.name} (agy${price ? "" : ", unpriced"})`,
			api: API,
			reasoning: model.efforts.length > 0,
			thinking: model.efforts.length > 0 ? { mode: "effort" as const, efforts: model.efforts } : undefined,
			input: ["text", "image"] as ("text" | "image")[],
			cost: price ?? { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
			contextWindow: 1_048_576,
			maxTokens: 65_536,
		};
	});
}

/** The agy model id for an omp model and effort: the effort suffix when the model has efforts. */
export function wireModelId(model: { id: string; thinking?: { efforts: readonly string[] } }, effort?: string): string {
	const efforts = model.thinking?.efforts ?? [];
	if (efforts.length === 0) return model.id;
	const pick = effort && efforts.includes(effort) ? effort : efforts.includes("medium") ? "medium" : efforts[0];
	return `${model.id}-${pick}`;
}

// ---------- ACP wire ----------
// The shapes below are the parts of the Agent Client Protocol this client reads, as `agy acp` sends them.

interface RpcMessage {
	id?: number;
	method?: string;
	params?: unknown;
	result?: unknown;
	error?: { message?: string };
}

interface SessionUpdate {
	sessionUpdate: string;
	content?: { type: string; text?: string };
	title?: string;
	name?: string;
	status?: string;
}

interface PermissionRequest {
	toolCall?: { title?: string; name?: string };
	options?: { optionId: string; kind: string }[];
}

type PermissionOutcome = { outcome: { outcome: "selected"; optionId: string } | { outcome: "cancelled" } };

interface PromptResult {
	stopReason: string;
	usage?: { inputTokens?: number; outputTokens?: number; cachedReadTokens?: number; cachedWriteTokens?: number; thoughtTokens?: number; totalTokens?: number };
}

type PromptBlock = { type: "text"; text: string } | { type: "image"; data: string; mimeType?: string };

/** Every live `agy acp`, so a turn cut off when omp exits does not leave agy running. */
const running = new Set<Subprocess>();
process.once("exit", () => {
	for (const proc of running) proc.kill();
});

class AcpConnection {
	readonly proc: Subprocess<"pipe", "pipe", "pipe">;
	readonly closed: Promise<void>;
	onUpdate: (update: SessionUpdate) => void = () => {};
	onPermission: (request: PermissionRequest) => PermissionOutcome = () => ({ outcome: { outcome: "cancelled" } });
	#nextId = 1;
	#pending = new Map<number, { resolve: (value: unknown) => void; reject: (error: Error) => void }>();
	#stderr = "";

	constructor(cwd: string) {
		this.proc = Bun.spawn([agyBinary(), "acp"], { cwd, env: childEnv(), stdin: "pipe", stdout: "pipe", stderr: "pipe" });
		running.add(this.proc);
		void this.#readStderr();
		this.closed = this.#readStdout().finally(() => {
			running.delete(this.proc);
			const tail = this.#stderr.trim().slice(-800);
			const why = new Error(`agy acp exited (${this.proc.exitCode ?? "signal"})${tail ? `: ${tail}` : ""}`);
			for (const p of this.#pending.values()) p.reject(why);
			this.#pending.clear();
		});
	}

	request<T>(method: string, params: object): Promise<T> {
		const id = this.#nextId++;
		const { promise, resolve, reject } = Promise.withResolvers<T>();
		this.#pending.set(id, { resolve: resolve as (value: unknown) => void, reject });
		this.#send({ jsonrpc: "2.0", id, method, params });
		return promise;
	}

	notify(method: string, params: object): void {
		this.#send({ jsonrpc: "2.0", method, params });
	}

	close(): void {
		try {
			(this.proc.stdin as FileSink).end();
		} catch {
			// stdin already closed with the process
		}
		this.proc.kill();
	}

	#send(message: object): void {
		const stdin = this.proc.stdin as FileSink;
		stdin.write(`${JSON.stringify(message)}\n`);
		stdin.flush();
	}

	async #readStderr(): Promise<void> {
		const decoder = new TextDecoder();
		for await (const chunk of this.proc.stderr) this.#stderr = (this.#stderr + decoder.decode(chunk, { stream: true })).slice(-4000);
	}

	async #readStdout(): Promise<void> {
		const decoder = new TextDecoder();
		let buffer = "";
		for await (const chunk of this.proc.stdout) {
			buffer += decoder.decode(chunk, { stream: true });
			let newline: number;
			while ((newline = buffer.indexOf("\n")) >= 0) {
				const line = buffer.slice(0, newline).trim();
				buffer = buffer.slice(newline + 1);
				if (line) this.#dispatch(JSON.parse(line) as RpcMessage);
			}
		}
	}

	#dispatch(m: RpcMessage): void {
		if (m.method === undefined) {
			const pending = m.id === undefined ? undefined : this.#pending.get(m.id);
			if (!pending || m.id === undefined) return;
			this.#pending.delete(m.id);
			if (m.error) pending.reject(new Error(m.error.message ?? JSON.stringify(m.error)));
			else pending.resolve(m.result);
			return;
		}
		if (m.method === "session/update") {
			// ACP: a session/update notification's params are { sessionId, update }.
			const params = m.params as { update: SessionUpdate };
			return this.onUpdate(params.update);
		}
		if (m.id === undefined) return;
		if (m.method === "session/request_permission") {
			this.#send({ jsonrpc: "2.0", id: m.id, result: this.onPermission(m.params as PermissionRequest) });
			return;
		}
		this.#send({ jsonrpc: "2.0", id: m.id, error: { code: -32601, message: `${m.method} is not supported by this client` } });
	}
}

// ---------- conversations ----------

/**
 * One omp session's agy conversation: agy's session id once it exists, and how many omp messages agy has seen.
 * No process is held between turns: an idle `agy acp` takes about 170 MB, and omp keeps finished subagents around for
 * follow-ups, so each turn starts agy, reloads the conversation from agy's own store (under a second) and closes it.
 */
interface Conversation {
	cwd: string;
	sessionId?: string;
	seen: number;
}

/** Start agy for one turn of a conversation: a new agy session the first time, the saved one after. */
async function connect(conversation: Conversation, modelId: string): Promise<{ conn: AcpConnection; sessionId: string }> {
	const conn = new AcpConnection(conversation.cwd);
	try {
		await conn.request("initialize", { protocolVersion: 1, clientCapabilities: {} });
		const params = { cwd: conversation.cwd, mcpServers: [], _meta: { antigravity: { systemPrompt: { append: WORKER_PROMPT } } } };
		if (conversation.sessionId) await conn.request("session/load", { ...params, sessionId: conversation.sessionId });
		else conversation.sessionId = (await conn.request<{ sessionId: string }>("session/new", params)).sessionId;
		const sessionId = conversation.sessionId;
		await conn.request("session/set_mode", { sessionId, modeId: "auto" });
		try {
			await conn.request("session/set_model", { sessionId, modelId });
		} catch (err) {
			throw new Error(`agy cannot use ${modelId} on this account (${(err as Error).message}); \`agy models\` lists what the plan includes`);
		}
		return { conn, sessionId };
	} catch (err) {
		conn.close();
		throw err;
	}
}

interface OmpBlock {
	type: string;
	text?: string;
	data?: string;
	mimeType?: string;
}

interface OmpMessage {
	role: string;
	content?: string | OmpBlock[];
	toolName?: string;
}

/**
 * The ACP prompt for the omp messages from index `from` on: user text and images, omp's notes to the agent after the
 * first user message (the developer messages before it are omp's own context, which agy does not take), and results
 * of our yield calls.
 */
export function promptFor(messages: readonly OmpMessage[], from: number): PromptBlock[] {
	const firstUser = messages.findIndex(m => m.role === "user");
	const prompt: PromptBlock[] = [];
	for (const [index, message] of messages.entries()) {
		if (index < from) continue;
		const blocks = typeof message.content === "string" ? [{ type: "text", text: message.content }] : (message.content ?? []);
		const texts = blocks.flatMap(b => (b.type === "text" && b.text ? [b.text] : []));
		if (message.role === "user") {
			for (const b of blocks) {
				if (b.type === "text" && b.text) prompt.push({ type: "text", text: b.text });
				else if (b.type === "image" && b.data) prompt.push({ type: "image", data: b.data, mimeType: b.mimeType });
			}
		} else if (message.role === "developer" && index > firstUser) {
			for (const text of texts) prompt.push({ type: "text", text });
		} else if (message.role === "toolResult" && texts.length) {
			prompt.push({ type: "text", text: `The caller answered your result (${message.toolName}):\n${texts.join("\n")}` });
		}
	}
	return prompt;
}

/** The yield payload: a reply that is a JSON object or array goes as data, so structured-output tasks validate. */
export function yieldData(reply: string): unknown {
	const body = reply.trim().replace(/^```(?:json)?\n([\s\S]*)\n```$/, "$1").trim();
	if (body.startsWith("{") || body.startsWith("[")) {
		try {
			return JSON.parse(body);
		} catch {
			// prose that happens to start with a bracket goes as text
		}
	}
	return reply.trim();
}

// ---------- the provider ----------

export default function agy(pi: ExtensionAPI) {
	const conversations = new Map<string, Conversation>();

	pi.registerProvider(PROVIDER, {
		baseUrl: "https://agy-acp.invalid/",
		apiKey: "signed-in-through-agy",
		api: API,
		fetchDynamicModels: listModels,
		streamSimple(model, context, options) {
			const stream = new AssistantMessageEventStream();
			const output: AssistantMessage = {
				role: "assistant",
				content: [],
				api: model.api,
				provider: model.provider,
				model: model.id,
				usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
				stopReason: "stop",
				timestamp: Date.now(),
			};

			// The open text or thinking block, so a switch between them ends one and starts the other.
			let open: { index: number; block: TextContent } | { index: number; block: ThinkingContent } | undefined;
			const closeOpen = () => {
				if (!open) return;
				if (open.block.type === "text") stream.push({ type: "text_end", contentIndex: open.index, content: open.block.text, partial: output });
				else stream.push({ type: "thinking_end", contentIndex: open.index, content: open.block.thinking, partial: output });
				open = undefined;
			};
			const append = (kind: "text" | "thinking", delta: string) => {
				if (!delta) return;
				if (open?.block.type !== kind) {
					closeOpen();
					const index = output.content.length;
					if (kind === "text") {
						const block: TextContent = { type: "text", text: "" };
						output.content.push(block);
						open = { index, block };
						stream.push({ type: "text_start", contentIndex: index, partial: output });
					} else {
						const block: ThinkingContent = { type: "thinking", thinking: "" };
						output.content.push(block);
						open = { index, block };
						stream.push({ type: "thinking_start", contentIndex: index, partial: output });
					}
				}
				if (!open) return;
				if (open.block.type === "text") {
					open.block.text += delta;
					stream.push({ type: "text_delta", contentIndex: open.index, delta, partial: output });
				} else {
					open.block.thinking += delta;
					stream.push({ type: "thinking_delta", contentIndex: open.index, delta, partial: output });
				}
			};
			const fail = (reason: "error" | "aborted", message: string) => {
				closeOpen();
				output.stopReason = reason;
				output.errorMessage = message;
				stream.push({ type: "error", reason, error: output });
				stream.end();
			};

			const run = async () => {
				const key = options?.sessionId ?? crypto.randomUUID();
				let conversation = conversations.get(key);
				// A rewritten history (compaction, a branch) no longer extends what agy has seen: start a fresh agy conversation.
				if (!conversation || context.messages.length < conversation.seen) {
					// agy treats paths under a symlinked cwd (macOS /tmp) as outside the workspace, so it gets the real path.
					conversation = { cwd: realpathSync(options?.cwd ?? process.cwd()), seen: 0 };
					conversations.set(key, conversation);
				}
				const prompt = promptFor(context.messages as OmpMessage[], conversation.seen);
				if (prompt.length === 0) throw new Error("agy provider: nothing new in the conversation to send to agy");
				const { conn, sessionId } = await connect(conversation, wireModelId(model, options?.reasoning));

				const refused: string[] = [];
				const reply: string[] = [];
				conn.onUpdate = update => {
					const text = update.content?.type === "text" ? (update.content.text ?? "") : "";
					switch (update.sessionUpdate) {
						case "agent_message_chunk":
							reply.push(text);
							append("text", text);
							break;
						case "agent_thought_chunk":
							append("thinking", text);
							break;
						case "tool_call":
							append("thinking", `▸ ${update.title || update.name || "tool"}\n`);
							break;
						case "tool_call_update":
							if (update.status === "failed") append("thinking", `✗ ${update.title || update.name || "tool"} failed\n`);
							break;
					}
				};
				conn.onPermission = request => {
					const what = request.toolCall?.title || request.toolCall?.name || "an action";
					refused.push(what);
					append("thinking", `✗ refused (needs approval): ${what}\n`);
					const reject = request.options?.find(o => o.kind === "reject_once") ?? request.options?.find(o => o.kind.startsWith("reject"));
					return reject ? { outcome: { outcome: "selected", optionId: reject.optionId } } : { outcome: { outcome: "cancelled" } };
				};

				const onAbort = () => conn.notify("session/cancel", { sessionId });
				options?.signal?.addEventListener("abort", onAbort, { once: true });
				stream.push({ type: "start", partial: output });
				let result: PromptResult;
				try {
					result = await conn.request<PromptResult>("session/prompt", { sessionId, prompt });
				} finally {
					options?.signal?.removeEventListener("abort", onAbort);
					conn.close();
				}
				conversation.seen = context.messages.length;

				const usage = result.usage ?? {};
				output.usage.input = usage.inputTokens ?? 0;
				output.usage.output = usage.outputTokens ?? 0;
				output.usage.cacheRead = usage.cachedReadTokens ?? 0;
				output.usage.cacheWrite = usage.cachedWriteTokens ?? 0;
				output.usage.totalTokens = usage.totalTokens ?? 0;
				if (usage.thoughtTokens) output.usage.reasoningTokens = usage.thoughtTokens;
				// Priced at the request's start, like omp's own providers across a price change.
				const price = priceOn(model.id, output.timestamp);
				if (price) {
					const cost = output.usage.cost;
					cost.input = (output.usage.input * price.input) / 1e6;
					cost.output = (output.usage.output * price.output) / 1e6;
					cost.cacheRead = (output.usage.cacheRead * price.cacheRead) / 1e6;
					cost.cacheWrite = (output.usage.cacheWrite * price.cacheWrite) / 1e6;
					cost.total = cost.input + cost.output + cost.cacheRead + cost.cacheWrite;
				}

				switch (result.stopReason) {
					case "cancelled":
						return fail("aborted", "agy run cancelled");
					case "refusal":
						return fail("error", `agy refused the prompt${reply.length ? `: ${reply.join("")}` : ""}`);
					case "end_turn":
					case "max_tokens":
					case "max_turn_requests":
						break;
					default:
						return fail("error", `agy stopped with ${JSON.stringify(result.stopReason)}`);
				}
				// The turn always ends in text, so omp reads it as a finished answer, and refusals reach the caller.
				const notes: string[] = [];
				if (!reply.join("").trim()) notes.push("agy ended its turn without a reply.");
				if (refused.length) notes.push(`Refused because they need approval: ${refused.join("; ")}.`);
				if (notes.length) {
					const note = `${reply.join("").trim() ? "\n\n" : ""}${notes.join(" ")}`;
					reply.push(note);
					append("text", note);
				}
				closeOpen();
				const report = reply.join("");
				if (context.tools?.some(t => t.name === "yield")) {
					const toolCall: ToolCall = { type: "toolCall", id: `agy_yield_${crypto.randomUUID()}`, name: "yield", arguments: { data: yieldData(report) } };
					output.content.push(toolCall);
					const index = output.content.length - 1;
					stream.push({ type: "toolcall_start", contentIndex: index, partial: output });
					stream.push({ type: "toolcall_end", contentIndex: index, toolCall, partial: output });
					output.stopReason = "toolUse";
					stream.push({ type: "done", reason: "toolUse", message: output });
				} else {
					output.stopReason = result.stopReason === "end_turn" ? "stop" : "length";
					stream.push({ type: "done", reason: output.stopReason, message: output });
				}
				stream.end();
			};

			run().catch(err => {
				if (options?.signal?.aborted) return fail("aborted", "agy run cancelled");
				fail("error", err instanceof Error ? err.message : String(err));
			});
			return stream;
		},
	});
}
