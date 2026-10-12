/**
 * nstack-guard: one-line reminders at the patterns that cost Nate the most in his session audit
 * (~/Projects/nstack/audit/REPORT.md): agents run without control, and markdown sprawl.
 *
 * How agents were run mattered more than how many in his logs (complete briefs, one writer per file, every
 * agent tracked), so the reminders point at control, never at doing less: the first time a session runs several
 * build agents without having read `skill://nstack-agents`, when a later call repeats a brief an earlier call
 * already spawned (a race spawns its same-brief candidates together, in one call, and is not flagged), and at
 * growing agent counts as a prompt to account for every agent.
 *
 * It never blocks a tool. Guidance rides on `additionalContext`, which omp delivers after the tool results.
 * Any internal error returns nothing, because a throwing handler would block the tool (fail-closed).
 */
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

/** Cumulative build agents per session at which the accounting reminder fires (once per step). */
const ACCOUNT_STEPS = [12, 24, 48, 96];
/** Build agents per session at which a session that has not read nstack-agents gets the pointer (once). */
const CONTROL_POINTER_AT = 2;
/** Markdown files written per session at which the reminder fires (once per step). */
const MD_STEPS = [6, 15, 30, 60];
/** The nstack ledger is the one sanctioned status file. */
const LEDGER_PATH = /(^|\/)local\/nstack\/|^local:\/\//;
/** Research and verifier lanes run under skill://research and are not build agents. */
const RESEARCH_LANE = /^(researcher|verifier)/;
/** The skill body itself, by URI or installed path, with an optional read selector; not a sub-file. */
const AGENTS_SKILL_BODY = /^(skill:\/\/nstack-agents(\/SKILL\.md)?|.*\/skills\/nstack-agents\/SKILL\.md)(:[^/]*)?$/;

type Session = { agents: number; readAgentsSkill: boolean; pointed: boolean; briefs: Map<string, string>; md: Set<string> };
type TaskItem = { agent?: unknown; name?: unknown; task?: unknown };
const sessions = new Map<string, Session>();

function sessionFor(id: string): Session {
	let s = sessions.get(id);
	if (!s) {
		s = { agents: 0, readAgentsSkill: false, pointed: false, briefs: new Map(), md: new Set() };
		sessions.set(id, s);
	}
	return s;
}

export default function nstackGuard(pi: ExtensionAPI): void {
	pi.on("tool_result", async (event, ctx) => {
		try {
			if (event.toolName === "read" && !event.isError && AGENTS_SKILL_BODY.test(String(event.input.path ?? ""))) {
				sessionFor(ctx.sessionManager.getSessionId()).readAgentsSkill = true;
			}
		} catch {
			// A guard failure must never touch a tool result.
		}
		return undefined;
	});

	pi.on("tool_call", async (event, ctx) => {
		try {
			const s = sessionFor(ctx.sessionManager.getSessionId());
			const input = event.input as Record<string, unknown>;

			if (event.toolName === "task") {
				const items = (Array.isArray(input.tasks) ? (input.tasks as TaskItem[]) : []).filter(
					t => !RESEARCH_LANE.test(String(t?.agent ?? "")),
				);
				if (items.length === 0) return undefined;
				const before = s.agents;
				s.agents += items.length;
				const notes: string[] = [];

				const repeats: string[] = [];
				const thisCall = new Map<string, string>();
				for (const t of items) {
					const brief = String(t?.task ?? "").replace(/\s+/g, " ").trim();
					if (!brief) continue;
					const earlier = s.briefs.get(brief);
					if (earlier !== undefined) repeats.push(earlier || "an earlier agent");
					else if (!thisCall.has(brief)) thisCall.set(brief, String(t?.name ?? ""));
				}
				for (const [brief, name] of thisCall) s.briefs.set(brief, name);
				if (repeats.length > 0) {
					notes.push(
						`This call repeats a brief an earlier call in this session already spawned (${repeats.join(", ")}). ` +
							"Unless that is an intended rerun, check that agent first: if it is still running, let it finish; " +
							"if it failed or stalled, re-brief with consolidated scope (the original brief, every later decision, its partial report).",
					);
				}

				if (!s.readAgentsSkill && !s.pointed && s.agents >= CONTROL_POINTER_AT) {
					s.pointed = true;
					notes.push(
						"Several build agents are running and skill://nstack-agents has not been read in this session. Its control: " +
							"complete briefs (outcome in Nate's words, exact inputs, owned files and resources, his standing decisions, " +
							"done-checks with evidence), one writer per file and resource, an untried kind of unit piloted first, every agent tracked to done.",
					);
				}

				const step = ACCOUNT_STEPS.find(n => before < n && s.agents >= n);
				if (step !== undefined) {
					notes.push(
						`${s.agents} build agents started in this session. Account for each one (done, failed, stopped or running) ` +
							"before spawning more: replace stalled ones with consolidated scope, and do not wait on finished ones.",
					);
				}

				if (notes.length === 0) return undefined;
				return { additionalContext: `nstack: ${notes.join(" ")} Nate's explicit requests stand.` };
			}

			if (event.toolName === "write") {
				const path = String(input.path ?? "");
				if (!path.toLowerCase().endsWith(".md") || LEDGER_PATH.test(path) || s.md.has(path)) return undefined;
				s.md.add(path);
				if (!MD_STEPS.includes(s.md.size)) return undefined;
				return {
					additionalContext:
						`nstack: ${s.md.size} markdown files written in this session. ` +
						"Write only code, checks, the one ledger (local/nstack/<slug>.md), fixes to docs the change made wrong, and new docs Nate asked for; fold status into the ledger.",
				};
			}
		} catch {
			// A guard failure must never block a tool call.
		}
		return undefined;
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		try {
			sessions.delete(ctx.sessionManager.getSessionId());
		} catch {
			// Nothing to clean up.
		}
	});
}
