#!/usr/bin/env python3
"""Deterministic spend/process metrics over every omp and Context session file.

Per assistant call: cost and context size (input + cache read + cache write).
Per subagent file: the agent type that spawned it (matched by task name in the parent),
its role (research / verify / review / build-or-other), cost, month.
Per session file: build briefs it spawned more than once (exact text after whitespace folding).
Writes local/digests/metrics.json and prints the tables used in the audit report (local/audit/REPORT.md, private).
`--since YYYY-MM-DD` keeps only root sessions started on or after that date and `--until YYYY-MM-DD` only
those started before it (forks are still charged to their earliest session first); the output file name
carries both.
"""
import glob, json, os, re, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

HOME = os.path.expanduser("~")
CONTEXT_HOME = os.environ.get("CONTEXT_HOME") or f"{HOME}/.context-next"
# Context worker transcripts: the pre-cutover layout <home>/workers/<id>/session/*.jsonl (the old ~/.context, frozen in
# ~/.context-cutover/frozen on 2026-10-12) and the current one, <home>/workers/sessions/<sha256 of the session>/main.jsonl
# with its subagents under main/.
WORKER_SESSION_DIRS = (f"{HOME}/.context-cutover/frozen/workers/*/session", f"{CONTEXT_HOME}/workers/sessions/*")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "local", "digests", "metrics.json")
REVIEW = re.compile(r"review|audit|critic|judge|interrogat|challenge|redteam|red-team|adversar|skeptic|check(er)?$", re.I)
LANE = re.compile(r"^(researcher|verifier)")
BUCKETS = [50_000, 100_000, 200_000, 300_000, 400_000, 10**9]


def scan(path):
    """Assistant calls as (context, cost, call key, build briefs spawned in that call) plus spawned agent names.

    The session's start is its header line, not its first assistant message: a fork copies its parent's
    history, so the first message in a fork predates the fork."""
    calls, spawns, start, first_ts = [], {}, None, None
    with open(path, errors="replace") as fh:
        for line in fh:
            if start is None and '"session"' in line[:120]:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") == "session":
                    start = d.get("timestamp")
                continue
            if '"toolResult"' in line[:260] or '"assistant"' not in line[:400]:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            m = d.get("message") or {}
            if d.get("type") != "message" or m.get("role") != "assistant":
                continue
            first_ts = first_ts or d.get("timestamp")
            u = m.get("usage") or {}
            ctx = (u.get("input") or 0) + (u.get("cacheRead") or 0) + (u.get("cacheWrite") or 0)
            key = str(m.get("responseId") or (d.get("id"), d.get("timestamp")))
            briefs = set()
            for b in m.get("content") or []:
                if b.get("type") == "toolCall" and b.get("name") == "task":
                    for tk in (b.get("arguments") or {}).get("tasks") or []:
                        if tk.get("name"):
                            spawns[tk["name"]] = tk.get("agent") or "task"
                        brief = " ".join(str(tk.get("task") or "").split())
                        if brief and not LANE.match(str(tk.get("agent") or "")):
                            briefs.add(brief)
            calls.append((ctx, ((u.get("cost") or {}).get("total") or 0), key, tuple(briefs)))
    return {"calls": calls, "spawns": spawns, "ts": start or first_ts}


def tree(root):
    """Yield (file, depth, parent_file) for the root session and every nested subagent file."""
    yield root, 0, None
    stack = [(root, 0)]
    while stack:
        f, depth = stack.pop()
        d = f[:-6]
        if os.path.isdir(d):
            for c in sorted(glob.glob(d + "/*.jsonl")):
                yield c, depth + 1, f
                stack.append((c, depth + 1))


def session(item):
    src, proj, root = item
    files = list(tree(root))
    scans = {f: scan(f) for f, _, _ in files}
    rows = []
    for f, depth, parent in files:
        s = scans[f]
        name = os.path.basename(f)[:-6]
        agent = "root" if depth == 0 else (scans[parent]["spawns"].get(name) or "unknown")
        role = ("root" if depth == 0 else
                "research" if agent.startswith("researcher") else
                "verify" if agent.startswith("verifier") else
                "review" if REVIEW.search(name) else "build-or-other")
        rows.append({"src": src, "proj": proj, "root": root, "depth": depth, "name": name, "agent": agent,
                     "role": role, "month": (scans[files[0][0]]["ts"] or "????-??")[:7],
                     "ts": scans[files[0][0]]["ts"] or "", "calls_raw": s["calls"]})
    return rows


def roots():
    for f in glob.glob(f"{HOME}/.omp/agent/sessions/*/*.jsonl"):
        p = f.split("/sessions/")[1].split("/")[0]
        if p != "-Projects-nstack":
            yield ("omp", p, f)
    for pattern in WORKER_SESSION_DIRS:
        for w in glob.glob(pattern):
            wid = (w.split("/")[-2] if w.endswith("/session") else w.split("/")[-1])[:8]
            for f in glob.glob(w + "/*.jsonl"):
                yield ("worker", wid, f)


def main():
    since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else ""
    until = sys.argv[sys.argv.index("--until") + 1] if "--until" in sys.argv else ""
    suffix = (f"-since-{since}" if since else "") + (f"-until-{until}" if until else "")
    out_path = OUT.replace(".json", f"{suffix}.json")
    with ProcessPoolExecutor(max_workers=10) as ex:
        rows = [r for rs in ex.map(session, list(roots()), chunksize=4) for r in rs]
    # Forked sessions copy the parent's history: charge each model call, and count each spawn, once, to the
    # earliest session. A brief repeated across calls of one session is a repeat; candidates of one race share
    # a call and are not.
    seen = set()
    for r in sorted(rows, key=lambda r: (r["ts"], r["depth"])):
        raw = r.pop("calls_raw")
        r["raw_calls"] = len(raw)
        kept = [(x, c, b) for x, c, k, b in raw if not (k in seen or seen.add(k))]
        r["ctx"] = [x for x, _, _ in kept]; r["ccost"] = [c for _, c, _ in kept]
        r["cost"] = sum(r["ccost"]); r["calls"] = len(kept)
        briefs = Counter(brief for _, _, call in kept for brief in call)
        r["repeats"] = sum(n - 1 for n in briefs.values())
    rows = [r for r in rows if r["ts"] >= since and (not until or r["ts"] < until)]
    total = sum(r["cost"] for r in rows)
    out = {"total_cost": total, "files": len(rows)}
    # cost by role and by month
    by_role, by_month_role = Counter(), defaultdict(Counter)
    for r in rows:
        by_role[r["role"]] += r["cost"]; by_month_role[r["month"]][r["role"]] += r["cost"]
    out["by_role"] = dict(by_role); out["by_month_role"] = {k: dict(v) for k, v in sorted(by_month_role.items())}
    # cost by agent type (subagents)
    by_agent = Counter()
    for r in rows:
        if r["depth"] > 0:
            by_agent[r["agent"]] += r["cost"]
    out["by_agent"] = dict(by_agent.most_common())
    # context buckets over every call
    bucket_cost, bucket_calls = Counter(), Counter()
    allctx = []
    for r in rows:
        for x, c in zip(r["ctx"], r["ccost"]):
            b = next(i for i, lim in enumerate(BUCKETS) if x < lim)
            bucket_cost[b] += c; bucket_calls[b] += 1; allctx.append(x)
    allctx.sort()
    labels = ["<50k", "50-100k", "100-200k", "200-300k", "300-400k", ">=400k"]
    out["ctx_buckets"] = {labels[b]: {"calls": bucket_calls[b], "cost": round(bucket_cost[b], 2)} for b in range(len(labels))}
    out["ctx_pct"] = {p: allctx[int(len(allctx) * p / 100)] for p in (10, 25, 50, 75, 90, 99)} if allctx else {}
    # fan-out per root session
    per_root = defaultdict(lambda: {"cost": 0.0, "subs": 0, "research": 0, "verify": 0, "review": 0, "proj": None,
                                    "repeats": 0, "dead": 0, "nested": 0})
    for r in rows:
        x = per_root[r["root"]]; x["cost"] += r["cost"]; x["proj"] = r["proj"]; x["repeats"] += r["repeats"]
        if r["depth"] > 0:
            x["subs"] += 1
            if r["role"] in ("research", "verify", "review"):
                x[r["role"]] += 1
            if r["raw_calls"] == 0:
                x["dead"] += 1
            if r["depth"] >= 2 and r["role"] == "build-or-other":
                x["nested"] += 1
    fan = Counter(); fan_cost = Counter()
    for x in per_root.values():
        k = "0" if x["subs"] == 0 else "1-4" if x["subs"] <= 4 else "5-19" if x["subs"] <= 19 else "20-99" if x["subs"] <= 99 else "100+"
        fan[k] += 1; fan_cost[k] += x["cost"]
    out["fanout"] = {k: {"sessions": fan[k], "cost": round(fan_cost[k], 2)} for k in ["0", "1-4", "5-19", "20-99", "100+"]}
    out["sessions_with_research"] = sum(1 for x in per_root.values() if x["research"])
    out["sessions_with_verify"] = sum(1 for x in per_root.values() if x["verify"])
    out["sessions_with_review"] = sum(1 for x in per_root.values() if x["review"])
    out["research_lanes"] = sum(x["research"] for x in per_root.values())
    out["review_lanes"] = sum(x["review"] for x in per_root.values())
    # Fan-out shares are descriptive: agent count did not decide outcomes in the audit, control did. The control
    # indicators are what nstack is meant to move: briefs spawned twice in one session, subagents that never made a
    # model call, and build agents spawned by other subagents.
    share = lambda part: round(part / (total or 1), 3)
    build_subs = lambda x: x["subs"] - x["research"] - x["verify"]
    subs_total = sum(x["subs"] for x in per_root.values())
    out["indicators"] = {
        "sessions": len(per_root),
        "spend": round(total, 2),
        "share_in_20plus_subagent_sessions": share(sum(x["cost"] for x in per_root.values() if x["subs"] >= 20)),
        "share_in_20plus_build_subagent_sessions": share(sum(x["cost"] for x in per_root.values() if build_subs(x) >= 20)),
        "share_at_200k_plus_context": share(sum(c for r in rows for x, c in zip(r["ctx"], r["ccost"]) if x >= 200_000)),
        "share_in_subagents": share(sum(r["cost"] for r in rows if r["depth"] > 0)),
        "share_in_research_and_verifier_lanes": share(sum(r["cost"] for r in rows if r["role"] in ("research", "verify"))),
        "repeated_briefs": sum(x["repeats"] for x in per_root.values()),
        "share_in_sessions_with_repeated_briefs": share(sum(x["cost"] for x in per_root.values() if x["repeats"])),
        "subagents_without_a_model_call": sum(x["dead"] for x in per_root.values()),
        "share_of_subagents_without_a_model_call": round(sum(x["dead"] for x in per_root.values()) / (subs_total or 1), 3),
        "nested_build_subagents": sum(x["nested"] for x in per_root.values()),
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
