/**
 * nstack-guard: one-line reminders at the two patterns that cost Nate the most in his session audit
 * (~/Projects/nstack/audit/REPORT.md): subagent fan-out and markdown sprawl.
 *
 * It never blocks a tool. When a session crosses a threshold it attaches passive guidance through
 * `additionalContext`, which omp delivers after the tool results. Any internal error returns nothing,
 * because a throwing `tool_call` handler would block the tool (fail-closed).
 */
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

/** Cumulative subagents per session at which the reminder fires (once per step). */
const TASK_STEPS = [6, 12, 24, 48];
/** The first task call this wide gets the reminder even below the next step (once per session). */
const WIDE_BATCH = 5;
/** Markdown files written per session at which the reminder fires (once per step). */
const MD_STEPS = [6, 15, 30, 60];
/** The nstack ledger is the one sanctioned status file. */
const LEDGER_PATH = /(^|\/)local\/nstack\/|^local:\/\//;

type Counts = { tasks: number; wideWarned: boolean; md: Set<string> };
const counts = new Map<string, Counts>();

export default function nstackGuard(pi: ExtensionAPI): void {
	pi.on("tool_call", async (event, ctx) => {
		try {
			const sessionId = ctx.sessionManager.getSessionId();
			let c = counts.get(sessionId);
			if (!c) {
				c = { tasks: 0, wideWarned: false, md: new Set() };
				counts.set(sessionId, c);
			}
			const input = event.input as Record<string, unknown>;

			if (event.toolName === "task") {
				const started = Array.isArray(input.tasks) ? input.tasks.length : 0;
				if (started === 0) return undefined;
				const before = c.tasks;
				c.tasks += started;
				const crossedStep = TASK_STEPS.some(step => before < step && c.tasks >= step);
				const firstWide = started >= WIDE_BATCH && !c.wideWarned;
				if (!crossedStep && !firstWide) return undefined;
				if (firstWide) c.wideWarned = true;
				return {
					additionalContext:
						`nstack: ${c.tasks} subagents started in this session (${started} in this call). ` +
						"Fan-out repeats context and adds coordination, and Nate's 20+-subagent sessions scored lowest. " +
						"Keep only disjoint slices with their own checks, bulk reading on a cheap model, one independent review, " +
						"or research lanes on independent open questions; do the rest yourself. Nate's explicit requests stand.",
				};
			}

			if (event.toolName === "write") {
				const path = String(input.path ?? "");
				if (!path.toLowerCase().endsWith(".md") || LEDGER_PATH.test(path) || c.md.has(path)) return undefined;
				c.md.add(path);
				if (!MD_STEPS.includes(c.md.size)) return undefined;
				return {
					additionalContext:
						`nstack: ${c.md.size} markdown files written in this session. ` +
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
			counts.delete(ctx.sessionManager.getSessionId());
		} catch {
			// Nothing to clean up.
		}
	});
}
