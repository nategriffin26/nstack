#!/usr/bin/env python3
"""Compress omp + Context (Dross/worker) session logs into per-session digests.

Read-only over ~/.omp/agent/sessions and Context's sessions and workers: the pre-cutover home frozen in
~/.context-cutover/frozen (Dross's omp sessions and old-layout workers) and the live home's workers/sessions.
Writes:
  local/digests/sessions.jsonl   one stats record per root session (subagents rolled up)
  local/digests/md/<key>.md      one readable digest per root session (user turns verbatim-ish,
                                 agent yields truncated, per-turn cost/tools/delegation)
"""
import glob, json, os, re, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

HOME = os.path.expanduser("~")
FROZEN = f"{HOME}/.context-cutover/frozen"
CONTEXT_HOME = os.environ.get("CONTEXT_HOME") or f"{HOME}/.context-next"
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "local", "digests")
REMINDER = re.compile(r"<(system-reminder|system-notice|system-directive|system-interrupt)[^>]*>.*?</\1>", re.S)
WS = re.compile(r"\n{3,}")


def iso(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def clip(s, n):
    s = WS.sub("\n\n", s.strip())
    if len(s) <= n:
        return s
    head = int(n * 0.75)
    return s[:head] + f"\n[… {len(s) - n} chars cut …]\n" + s[-(n - head):]


def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if b.get("type") == "text":
            out.append(b.get("text", ""))
        elif b.get("type") == "image":
            out.append("[image]")
    return "\n".join(out)


def parse(path):
    """One jsonl -> raw facts. Skips toolResult bodies (prefilter) for speed."""
    s = {"path": path, "id": None, "cwd": None, "parent": None, "title": None, "start": None, "end": None,
         "models": Counter(), "cost": 0.0, "aux_cost": 0.0, "tin": 0, "tout": 0, "tcr": 0, "tcw": 0,
         "tools": Counter(), "skills": Counter(), "writes": [], "tasks": [], "asks": 0, "todo_ops": 0,
         "compactions": 0, "events": [], "turn": 0, "first_edit": None, "first_task": None, "mkeys": []}
    try:
        fh = open(path, errors="replace")
    except OSError:
        return s
    with fh:
        for line in fh:
            head = line[:260]
            if '"toolResult"' in head:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            ts = d.get("timestamp")
            if ts and isinstance(ts, str):
                if not s["start"]:
                    s["start"] = ts
                s["end"] = ts
            if t == "session":
                s["id"] = d.get("id"); s["cwd"] = d.get("cwd"); s["parent"] = d.get("parentSession")
            elif t in ("title", "title_change"):
                s["title"] = d.get("title")
            elif t == "compaction":
                s["compactions"] += 1
            elif t == "model_usage":
                s["aux_cost"] += ((d.get("usage") or {}).get("cost") or {}).get("total", 0) or 0
            elif t == "message":
                m = d.get("message") or {}
                role = m.get("role")
                if role == "user":
                    txt = REMINDER.sub("", text_of(m.get("content"))).strip()
                    if txt:
                        s["events"].append(("user", ts, txt))
                        s["turn"] += 1
                elif role == "assistant":
                    u = m.get("usage") or {}
                    c = (u.get("cost") or {}).get("total", 0) or 0
                    s["cost"] += c
                    s["mkeys"].append((str(m.get("responseId") or (d.get("id"), ts)), c))
                    s["tin"] += u.get("input", 0) or 0; s["tout"] += u.get("output", 0) or 0
                    s["tcr"] += u.get("cacheRead", 0) or 0; s["tcw"] += u.get("cacheWrite", 0) or 0
                    if m.get("model"):
                        s["models"][m["model"]] += 1
                    texts, calls, spawned = [], [], []
                    for b in m.get("content") or []:
                        bt = b.get("type")
                        if bt == "text" and b.get("text", "").strip():
                            texts.append(b["text"])
                        elif bt == "toolCall":
                            name = b.get("name") or "?"
                            a = b.get("arguments") or {}
                            s["tools"][name] += 1
                            calls.append(name)
                            if name == "read":
                                p = str(a.get("path", ""))
                                mm = re.match(r"skill://([^/:\s]+)", p)
                                if mm:
                                    s["skills"][mm.group(1)] += 1
                            elif name in ("write", "edit"):
                                p = a.get("path") or ""
                                if not p and name == "edit":
                                    mm = re.findall(r"\[([^\]#]+)#[0-9A-F]{4}\]", str(a.get("input", "")))
                                    p = ",".join(mm)
                                s["writes"].append(p)
                                if s["first_edit"] is None:
                                    s["first_edit"] = {"ts": ts, "turn": s["turn"], "cost_before": round(s["cost"], 2)}
                            elif name == "task":
                                for tk in a.get("tasks") or []:
                                    spec = {"agent": tk.get("agent") or "task", "name": tk.get("name"),
                                            "len": len(tk.get("task") or ""),
                                            "head": (tk.get("task") or "")[:300],
                                            "ctxlen": len(a.get("context") or "")}
                                    s["tasks"].append(spec)
                                    spawned.append(spec)
                                if s["first_task"] is None:
                                    s["first_task"] = {"ts": ts, "turn": s["turn"], "cost_before": round(s["cost"], 2)}
                            elif name == "ask":
                                s["asks"] += 1
                            elif name == "todo":
                                s["todo_ops"] += 1
                    s["events"].append(("assistant", ts, "\n".join(texts), calls, c, spawned))
    return s


def subfiles(root_jsonl):
    d = root_jsonl[:-6]
    return sorted(glob.glob(d + "/**/*.jsonl", recursive=True)) if os.path.isdir(d) else []


def roots():
    for f in glob.glob(f"{HOME}/.omp/agent/sessions/*/*.jsonl"):
        proj = f.split("/sessions/")[1].split("/")[0]
        yield ("omp", proj, f)
    for f in glob.glob(f"{FROZEN}/sessions/*.jsonl"):
        yield ("dross", "dross", f)
    for pattern in (f"{FROZEN}/workers/*/session", f"{CONTEXT_HOME}/workers/sessions/*"):
        for w in glob.glob(pattern):
            wid = w.split("/")[-2] if w.endswith("/session") else w.split("/")[-1]
            for f in sorted(glob.glob(w + "/*.jsonl")):
                yield ("worker", wid[:8], f)


def summarize(item):
    src, proj, f = item
    r = parse(f)
    subs = [parse(x) for x in subfiles(f)]
    sub_cost = sum(x["cost"] + x["aux_cost"] for x in subs)
    sub_agents = Counter()
    for x in subs:
        sub_agents[(x["models"].most_common(1)[0][0] if x["models"] else "?")] += 1
    users = [e for e in r["events"] if e[0] == "user"]
    st, en = iso(r["start"] or ""), iso(r["end"] or "")
    rec = {
        "key": f"{src}__{proj}__{os.path.basename(f)[:-6]}",
        "source": src, "project": proj, "file": f, "cwd": r["cwd"], "title": r["title"],
        "start": r["start"], "end": r["end"],
        "minutes": round((en - st).total_seconds() / 60, 1) if st and en else None,
        "user_turns": len(users),
        "first_prompt_chars": len(users[0][2]) if users else 0,
        "root_cost": round(r["cost"] + r["aux_cost"], 4), "sub_cost": round(sub_cost, 4),
        "total_cost": round(r["cost"] + r["aux_cost"] + sub_cost, 4),
        "tokens_out": r["tout"] + sum(x["tout"] for x in subs),
        "tokens_in_total": r["tin"] + r["tcr"] + r["tcw"] + sum(x["tin"] + x["tcr"] + x["tcw"] for x in subs),
        "models": dict(r["models"]), "sub_models": dict(sub_agents), "n_subagents": len(subs),
        "tools": dict(r["tools"]), "sub_tools": dict(sum((x["tools"] for x in subs), Counter())),
        "skills": dict(r["skills"] + sum((x["skills"] for x in subs), Counter())),
        "asks": r["asks"], "todo_ops": r["todo_ops"], "compactions": r["compactions"],
        "writes": len(r["writes"]) + sum(len(x["writes"]) for x in subs),
        "md_writes": sum(1 for w in r["writes"] + [w for x in subs for w in x["writes"]] if str(w).endswith(".md")),
        "task_specs": r["tasks"],
        "first_edit": r["first_edit"], "first_task": r["first_task"],
        "first_sub_edit_ts": min((x["first_edit"]["ts"] for x in subs if x["first_edit"]), default=None),
        "subagents": [{"file": os.path.relpath(x["path"], f[:-6]), "title": x["title"],
                       "model": (x["models"].most_common(1)[0][0] if x["models"] else None),
                       "cost": round(x["cost"] + x["aux_cost"], 4), "tools": sum(x["tools"].values()),
                       "minutes": round((iso(x["end"]) - iso(x["start"])).total_seconds() / 60, 1)
                       if x["start"] and x["end"] and iso(x["start"]) and iso(x["end"]) else None}
                      for x in subs],
        "_mk_root": r["mkeys"], "_mk_sub": [k for x in subs for k in x["mkeys"]],
    }
    md = render(rec, r)
    return rec, md


def render(rec, r):
    L = []
    L.append(f"# {rec['source']}/{rec['project']} — {rec['title'] or '(untitled)'}")
    L.append(f"key: {rec['key']}  ")
    L.append(f"cwd: {rec['cwd']}  start: {rec['start']}  end: {rec['end']}  wall_min: {rec['minutes']}")
    L.append(f"cost: ${rec['total_cost']:.2f} (root ${rec['root_cost']:.2f}, {rec['n_subagents']} subagents ${rec['sub_cost']:.2f})"
             f"  models: {rec['models']}  sub_models: {rec['sub_models']}  compactions: {rec['compactions']}")
    top = ", ".join(f"{k} {v}" for k, v in Counter(rec["tools"]).most_common(12))
    L.append(f"root tools: {top}  | asks: {rec['asks']} todo_ops: {rec['todo_ops']} writes: {rec['writes']} (md {rec['md_writes']})")
    L.append(f"first root edit: {rec['first_edit']}  first spawn: {rec['first_task']}  first subagent edit: {rec['first_sub_edit_ts']}")
    if rec["skills"]:
        L.append(f"skills read: {rec['skills']}")
    L.append("")
    turn = 0
    pending = None  # accumulate assistant activity between user messages
    def flush():
        nonlocal pending
        if pending is None:
            return
        calls = Counter(pending["calls"])
        callstr = ", ".join(f"{k} {v}" for k, v in calls.most_common(8))
        L.append(f"### AGENT (turn {turn}) — ${pending['cost']:.2f}, {sum(calls.values())} tool calls [{callstr}]"
                 f", last @ {pending['last_ts']}")
        if pending["spawned"]:
            for tk in pending["spawned"][:25]:
                L.append(f"- spawned `{tk['agent']}` {tk['name'] or ''} (brief {tk['len']} chars): {clip(tk['head'], 200)!r}")
            if len(pending["spawned"]) > 25:
                L.append(f"- … {len(pending['spawned']) - 25} more spawns")
        if len(pending["texts"]) > 1:
            L.append("[first agent text this turn] " + clip(pending["texts"][0], 700))
            L.append("[final agent text this turn]")
        if pending["texts"]:
            L.append(clip(pending["texts"][-1], 1800))
        L.append("")
        pending = None
    for e in r["events"]:
        if e[0] == "user":
            flush()
            turn += 1
            limit = 7000 if turn == 1 else 2500
            L.append(f"### USER (turn {turn}) @ {e[1]}")
            L.append(clip(e[2], limit))
            L.append("")
        else:
            if pending is None:
                pending = {"calls": [], "cost": 0.0, "texts": [], "spawned": [], "last_ts": None}
            _, ts, txt, calls, c, spawned = e
            pending["calls"] += calls
            pending["cost"] += c
            pending["last_ts"] = ts
            pending["spawned"] += spawned
            if txt.strip():
                pending["texts"].append(txt)
    flush()
    if rec["subagents"]:
        L.append("### SUBAGENT SESSIONS (cost, tool calls, minutes)")
        for x in sorted(rec["subagents"], key=lambda x: -x["cost"])[:40]:
            L.append(f"- {x['file']} [{x['model']}] ${x['cost']:.2f}, {x['tools']} calls, {x['minutes']} min")
        L.append("")
    return "\n".join(L)


def main():
    os.makedirs(os.path.join(OUT, "md"), exist_ok=True)
    items = list(roots())
    print(f"{len(items)} root sessions", file=sys.stderr)
    recs = []
    with ProcessPoolExecutor(max_workers=10) as ex:
        for rec, md in ex.map(summarize, items, chunksize=4):
            recs.append(rec)
            with open(os.path.join(OUT, "md", rec["key"] + ".md"), "w") as fh:
                fh.write(md)
    # Forked sessions copy their parent's history, so the same model call appears in several files.
    # Charge each call once, to the earliest session that contains it.
    seen = set()
    for rec in sorted(recs, key=lambda r: r["start"] or ""):
        parts = {}
        for part in ("root", "sub"):
            total = 0.0
            for k, c in rec.pop(f"_mk_{part}"):
                if k not in seen:
                    seen.add(k)
                    total += c
            parts[part] = total
        rec["root_cost_dedup"] = round(parts["root"], 4)
        rec["sub_cost_dedup"] = round(parts["sub"], 4)
        rec["total_cost_dedup"] = round(parts["root"] + parts["sub"], 4)
    with open(os.path.join(OUT, "sessions.jsonl"), "w") as out:
        for rec in recs:
            out.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
