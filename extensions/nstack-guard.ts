/**
 * nstack-guard: Nate's few nstack rules that prose did not hold in the v3 rewrite (50 h, 79 agents), enforced
 * where they fire instead of restated in the skills:
 *
 * - a review closes at its verdict: the lead writing to a critic that has already reported gets a note (fixes are
 *   not re-reviewed); a critic is an agent whose name says so (critic, review, verdict);
 * - builders do not message critics: a subagent writing to one gets a note;
 * - a fresh agent per packet: a long message to an agent this session already spawned gets a note, and a subagent
 *   past CONTEXT_LIMIT tokens is told to finish its unit and report;
 * - never stall running agents on a question: an `ask` while agents run gets the rule as a note (it arrives after
 *   the answer, for the next question; omp's `ask.timeout` is what bounds the wait itself);
 * - after compaction, the summary carries a pointer back to the ledger and the skill.
 *
 * Notes ride on `additionalContext`. Any internal error returns nothing, because a throwing handler would block the
 * tool (fail-closed).
 */
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

/** Subagent context size past which it finishes its unit and the next unit goes to a fresh agent. */
const CONTEXT_LIMIT = 250_000;
/** A message this long to an agent that already exists is a new packet, not a steer. */
const PACKET_CHARS = 1_500;
/** Agent names that mark a critic or reviewer. */
const REVIEW = /critic|review|verdict/i;

type Session = { spawned: Set<string>; limitNoted: boolean };
type TaskItem = { name?: unknown };
const sessions = new Map<string, Session>();

function sessionFor(id: string): Session {
	let s = sessions.get(id);
	if (!s) {
		s = { spawned: new Set(), limitNoted: false };
		sessions.set(id, s);
	}
	return s;
}

function note(text: string) {
	return { additionalContext: `nstack: ${text} Nate's explicit requests stand.` };
}

export default function nstackGuard(pi: ExtensionAPI): void {
	pi.on("tool_call", async (event, ctx) => {
		try {
			const s = sessionFor(ctx.sessionManager.getSessionId());
			const input = event.input as Record<string, unknown>;
			const sub = ctx.agent?.kind === "sub";

			if (sub && !s.limitNoted && (ctx.getContextUsage()?.tokens ?? 0) >= CONTEXT_LIMIT) {
				s.limitNoted = true;
				return note(
					`Your context is past ${CONTEXT_LIMIT / 1000}K tokens. Finish the unit in hand and report; the next unit goes to a fresh agent.`,
				);
			}

			if (event.toolName === "task") {
				for (const t of Array.isArray(input.tasks) ? (input.tasks as TaskItem[]) : []) {
					if (t?.name) s.spawned.add(String(t.name));
				}
				return undefined;
			}

			const running = ctx.getAsyncJobSnapshot()?.running.filter(j => j.type === "task") ?? [];

			if (event.toolName === "ask" && !sub && running.length > 0) {
				return note(
					`${running.length} agent(s) were running while this question waited on Nate. Next time put the question in your reply ` +
						"with your recommended default and the time after which you take it, and keep dispatching; only a one-way door or a taste pick waits for him.",
				);
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
				if (!sub && s.spawned.has(target) && String(input.content ?? "").length > PACKET_CHARS) {
					return note(
						"This sends a long brief to an agent that already exists. If it is new work rather than a correction to its current unit, give it to a fresh agent with a handoff from the ledger.",
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
