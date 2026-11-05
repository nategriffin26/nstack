/**
 * nstack-guard: Nate's few nstack rules that prose did not hold in the v3 rewrite (50 h, 79 agents), enforced
 * where they fire instead of restated in the skills:
 *
 * - a review closes at its verdict: the lead writing to a critic that has already reported gets a note (fixes are
 *   not re-reviewed); a critic is an agent whose name says so (critic, review, verdict);
 * - builders do not message critics: a subagent writing to one gets a note;
 * - never stall running agents on a question: an `ask` while agents run gets the rule as a note (it arrives after
 *   the answer, for the next question; omp's `ask.timeout` is what bounds the wait itself);
 * - the ledger holds the current state only: a write or edit to a ledger past LEDGER_BYTES gets a note, once per
 *   ledger per session, to move finished detail and the log to its archive;
 * - comments and maintainer docs describe the code as it is: a write, edit or bash heredoc that adds a comment,
 *   docstring or README/AGENTS.md line in HISTORY's wording ("used to", "before this fix", "as requested") gets a note;
 * - after compaction, the summary carries a pointer back to the ledger and the skill.
 *
 * Notes ride on `additionalContext`. Any internal error returns nothing, because a throwing handler would block the
 * tool (fail-closed).
 */
import { readFileSync, statSync } from "node:fs";
import * as path from "node:path";
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

/** Agent names that mark a critic or reviewer. */
const REVIEW = /critic|review|verdict/i;
/** Ledger size past which it carries history rather than the current state. */
const LEDGER_BYTES = 12_000;
/** A ledger is `local/nstack/<slug>.md`; files in its subdirectories and `<slug>.archive.md` are not. */
const LEDGER = /(?:^|\/)local\/nstack\/([^/]+)\.md$/;

/**
 * Wording that describes earlier code, the edit that changed it, or the conversation behind it, after astral-sh/uv's
 * AGENTS.md rule. Kept narrow on purpose: in the comments Nate's agents committed, "old", "previous", "no longer",
 * "after the commit" and "in this chat" mostly name runtime states (the previous page, a database commit, the code a
 * hot reload keeps serving), so only phrasings that were mostly history there are listed.
 */
const HISTORY = new RegExp(
	[
		// Habitual "used to": "the map used to drop them"; not the passive "a key used to sign" or "is used to".
		String.raw`(?<![,(:;—]\s?)(?<!\b(?:is|are|was|were|be|been|being|get|gets|got|never|only|also|not|and|or)\s)\bused to (?:be|have|call|send|return|drop|ship|leave|give|publish|kill|come|reach|default|collapse|pass|close|count|run|use|read|write|take|show|go|lose|live|do|make|put|start|stop|break|fail|crash|land|need|wait|throw|skip|print|log|render|emit|load|save|store|fire|match|miss|hang|block|work|freeze|ignore|report|treat|accept|reject|refuse|leak|overwrite|truncate|wrap|import|export|require|depend|rely|expect)\b`,
		String.raw`\b(?:before|after) this (?:change|fix|rewrite|refactor|patch)\b|\b(?:before|after) the fix\b|\bas it did before\b`,
		String.raw`\bin (?:this|the|a|this lane's) next commit\b|\bnow lives? (?:in|at|under)\b|\bpreviously\b[^.]*\bnow\b`,
		String.raw`\bported (?:unchanged )?from (?:the )?(?:old|earlier|previous|former)\b|\bport of the (?:old|earlier|previous)\b|\bmoved here (?:\w+ )?from\b`,
		String.raw`\b(?:the|its) (?:old|previous|prior|former) (?:implementation|approach|behaviou?r|logic|regex|estimate|heuristic|algorithm|wording)\b`,
		String.raw`\b(?:preserve|keep|retain)s? (?:the )?(?:existing|original|old|previous|prior) (?:behaviou?r|rules?|semantics|logic)\b`,
		String.raw`\bas (?:you )?(?:requested|discussed)\b|\bper (?:your|our) (?:request|feedback|instructions?|discussion|conversation)\b`,
	].join("|"),
	"i",
);
/** The line-comment marker of each source file type; `//` types also take block and doc-comment lines. */
const COMMENT_MARKER: Record<string, "#" | "//" | "--"> = Object.fromEntries([
	...[".py", ".sh", ".bash", ".zsh", ".rb", ".toml", ".yaml", ".yml", ".nix", ".tf", ".ex", ".exs"].map(e => [e, "#"]),
	...[".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".rs", ".go", ".swift", ".kt", ".java", ".c", ".h", ".cc", ".cpp",
		".hpp", ".m", ".mm", ".css", ".scss", ".vue", ".svelte", ".zig", ".cs", ".php", ".dart", ".scala"].map(e => [e, "//"]),
	...[".lua", ".sql", ".hs"].map(e => [e, "--"]),
]);
/** Maintainer docs whose every line is prose for the next maintainer; a CHANGELOG is history by design. */
const MAINTAINER_DOCS = /(?:^|\/)(?:README|AGENTS|CLAUDE)\.md$/i;

type Session = { ledgersNoted: Set<string> };
const sessions = new Map<string, Session>();

function sessionFor(id: string): Session {
	let s = sessions.get(id);
	if (!s) {
		s = { ledgersNoted: new Set() };
		sessions.set(id, s);
	}
	return s;
}

function note(text: string) {
	return { additionalContext: `nstack: ${text} Nate's explicit requests stand.` };
}

/** Paths a write or edit call targets: `path`, or the `[PATH#TAG]` headers of a hashline edit. */
function targetPaths(toolName: string, input: Record<string, unknown>): string[] {
	if (typeof input.path === "string") return [input.path];
	if (toolName !== "edit") return [];
	return Array.from(String(input.input ?? "").matchAll(/^\[(.+)#[0-9A-Fa-f]{4}\]\s*$/gm), m => m[1]);
}

/**
 * The prose on each line of `lines`, a run of consecutive lines from `file`, or undefined where the line holds none:
 * own-line, trailing, block and doc comments, Python docstrings, and every line of a README or AGENTS.md.
 */
export function proseLines(file: string, lines: string[]): (string | undefined)[] {
	if (MAINTAINER_DOCS.test(file)) return lines.map(line => line.trim() || undefined);
	const ext = path.extname(file).toLowerCase();
	let python: "code" | "docstring" | "string" = "code";
	return lines.map(line => {
		const s = line.trim();
		if (ext === ".py") {
			const quotes = (s.match(/"""|'''/g) ?? []).length;
			const state = python;
			if (quotes % 2 === 1) python = state !== "code" ? "code" : /^[rbuf]*("""|''')/i.test(s) ? "docstring" : "string";
			if (state === "docstring" || (state === "code" && /^[rbuf]*("""|''')/i.test(s))) return s.replace(/"""|'''/g, "").trim() || undefined;
			if (state === "string") return undefined;
		}
		const marker = COMMENT_MARKER[ext];
		if (marker === "#") {
			if (s.startsWith("#!")) return undefined;
			if (s.startsWith("#")) return s.replace(/^#+/, "").trim() || undefined;
			const quotes = (s.match(/["']/g) ?? []).length;
			return quotes % 2 === 0 ? /\s#\s+(.+)$/.exec(s)?.[1] : undefined;
		}
		if (marker === "//") {
			const own = /^(?:\/\/[/!]?|\/\*\*?|\*(?!\/))\s*(.*?)\s*(?:\*\/)?$/.exec(s);
			if (own) return own[1] || undefined;
			return /(?<![:"'\w])\s\/\/\s+(.+)$/.exec(s)?.[1];
		}
		if (marker === "--") return s.startsWith("--") ? s.slice(2).trim() || undefined : undefined;
		return /^<!--\s*(.*?)\s*(?:-->)?$/.exec(s)?.[1] || undefined;
	});
}

/** The history wording in one line of prose, or undefined. */
export function historyWording(prose: string): string | undefined {
	return HISTORY.exec(prose)?.[0];
}

/**
 * Lines a call puts in each file: a write's content, the `+` rows of a hashline edit's sections, or a bash heredoc
 * redirected into a file (`cat > src/a.ts <<'EOF'`).
 */
function writtenLines(toolName: string, input: Record<string, unknown>): [string, string[]][] {
	if (toolName === "write") {
		return typeof input.path === "string" ? [[input.path, String(input.content ?? "").split("\n")]] : [];
	}
	if (toolName === "bash") {
		const command = String(input.command ?? "");
		if (!command.includes("<<")) return [];
		const heredocs = command.matchAll(/>\s*(['"]?)([^\s'"<>|&;]+)\1[^\n]*?<<-?\s*(['"]?)(\w+)\3[^\n]*\n([\s\S]*?)\n\s*\4\s*$/gm);
		return Array.from(heredocs, m => [m[2], m[5].split("\n")]);
	}
	const sections: [string, string[]][] = [];
	for (const line of String(input.input ?? "").split("\n")) {
		const header = /^\[(.+)#[0-9A-Fa-f]{4}\]\s*$/.exec(line);
		if (header) sections.push([header[1], []]);
		else if (line.startsWith("+") && sections.length > 0) sections[sections.length - 1][1].push(line.slice(1));
	}
	return sections;
}

/** At most this many findings, each quoted to at most EXCERPT characters, go into one note. */
const FINDINGS = 3;
const EXCERPT = 160;

function historyNote(cwd: string, toolName: string, input: Record<string, unknown>) {
	const found: string[] = [];
	scan: for (const [target, lines] of writtenLines(toolName, input)) {
		if (target.includes("://")) continue;
		const file = path.resolve(cwd, target);
		const prose = proseLines(file, lines);
		let existing: Set<string> | undefined;
		for (const [i, text] of prose.entries()) {
			const wording = text && historyWording(text);
			if (!wording) continue;
			// A line the file already holds was not written by this call (a hashline range repeats its keepers).
			existing ??= new Set(
				statSync(file, { throwIfNoEntry: false })?.isFile() ? readFileSync(file, "utf8").split("\n").map(l => l.trim()) : [],
			);
			if (existing.has(lines[i].trim())) continue;
			const start = Math.max(0, text.indexOf(wording) - EXCERPT / 2);
			const excerpt = text.length <= EXCERPT ? text : `…${text.slice(start, start + EXCERPT)}…`;
			found.push(`${target}: "${excerpt}" ("${wording}")`);
			if (found.length === FINDINGS) break scan;
		}
	}
	if (found.length === 0) return undefined;
	return note(
		`This may add wording about earlier code or the conversation to maintainer-facing prose: ${found.join("; ")}. ` +
			"Comments, docstrings and docs describe the code as it is and why, for a reader who never saw the edit or the chat: " +
			"state the current behavior or the constraint behind it, or delete the line. A line that already does, and text " +
			"that is runtime data or a fixture, stays.",
	);
}

function ledgerNote(s: Session, cwd: string, toolName: string, input: Record<string, unknown>) {
	for (const target of targetPaths(toolName, input)) {
		const file = path.resolve(cwd, target);
		const m = LEDGER.exec(file);
		if (!m || m[1].endsWith(".archive") || s.ledgersNoted.has(file)) continue;
		const bytes =
			toolName === "write"
				? Buffer.byteLength(String(input.content ?? ""))
				: (statSync(file, { throwIfNoEntry: false })?.size ?? 0);
		if (bytes <= LEDGER_BYTES) continue;
		s.ledgersNoted.add(file);
		const archive = path.join(path.dirname(target), `${m[1]}.archive.md`);
		return note(
			`The ledger ${target} is ${Math.round(bytes / 1000)} KB. Keep only the current state in it (frame, decisions, slice checklist, ` +
				`what is running with the next action), edited in place; move finished detail and the log to ${archive}.`,
		);
	}
	return undefined;
}

export default function nstackGuard(pi: ExtensionAPI): void {
	pi.on("tool_call", async (event, ctx) => {
		try {
			const s = sessionFor(ctx.sessionManager.getSessionId());
			const input = event.input as Record<string, unknown>;
			const sub = ctx.agent?.kind === "sub";

			const running = ctx.getAsyncJobSnapshot()?.running.filter(j => j.type === "task") ?? [];

			if (event.toolName === "ask" && !sub && running.length > 0) {
				return note(
					`${running.length} agent(s) were running while this question waited on Nate. Next time put the question in your reply ` +
						"with your recommended default and the time after which you take it, and keep dispatching; only a one-way door or a taste pick waits for him.",
				);
			}

			if (event.toolName === "write" || event.toolName === "edit") {
				const ledger = ledgerNote(s, ctx.cwd, event.toolName, input);
				if (ledger) return ledger;
			}

			if (event.toolName === "write" || event.toolName === "edit" || event.toolName === "bash") {
				const history = historyNote(ctx.cwd, event.toolName, input);
				if (history) return history;
			}

			if (event.toolName === "write") {
				const m = /^agent:\/\/([^/]+)/.exec(String(input.path ?? ""));
				if (!m || m[1] === "all") return undefined;
				const target = m[1];
				if (REVIEW.test(target) && (sub || !running.some(j => j.id === target || j.agentId === target))) {
					return note(
						sub
							? "Builders do not message critics or reviewers. Weigh the findings with what you know, fix what you take, and report to your lead."
							: "A review closes at its verdict, and fixes are not re-reviewed. Take or leave its findings on your own judgment and move on.",
					);
				}
			}
		} catch {
			// A guard failure must never block a tool call.
		}
		return undefined;
	});

	pi.on("session.compacting", async () => {
		try {
			return {
				context: [
					"nstack: resume from the ledger (local/nstack/<slug>.md) and re-read skill://nstack before the next step; do not redo what the ledger records.",
				],
			};
		} catch {
			return undefined;
		}
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		try {
			sessions.delete(ctx.sessionManager.getSessionId());
		} catch {
			// Nothing to clean up.
		}
	});
}
