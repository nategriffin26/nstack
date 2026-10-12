#!/usr/bin/env python3
"""Read-only dump of the Dross conversation and worker briefs from ~/.context/context.sqlite.

Writes local/digests/context/conversation-<day>.md and workers-<n>.md.
"""
import json, os, sqlite3
from collections import defaultdict
from datetime import datetime, timezone

DB = os.path.expanduser("~/.context/context.sqlite")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "local", "digests", "context")


def clip(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: int(n * 0.8)] + f"\n[… {len(s) - n} chars cut …]\n" + s[-int(n * 0.2):]


def day(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone().strftime("%Y-%m-%d")


def hm(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone().strftime("%m-%d %H:%M")


def main():
    os.makedirs(OUT, exist_ok=True)
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    by_day = defaultdict(list)
    for created, role, origin, hidden, data in db.execute(
            "select created_at, role, origin, hidden, data from messages order by created_at"):
        d = json.loads(data)
        text = d.get("text") or ""
        who = "NATE" if role == "user" and origin in (None, "user") else (
            "DROSS" if role == "agent" else (origin or role).upper())
        lim = {"NATE": 3000, "DROSS": 1400}.get(who, 500)
        if hidden and who not in ("NATE",):
            lim = min(lim, 400)
        by_day[day(created)].append(f"**{who}** {hm(created)}{' (hidden)' if hidden else ''}: {clip(text, lim)}\n")
    for k, lines in by_day.items():
        with open(os.path.join(OUT, f"conversation-{k}.md"), "w") as fh:
            fh.write(f"# Dross conversation {k}\n\n" + "\n".join(lines))

    cost = defaultdict(float)
    for sid, c in db.execute("select source_id, sum(cost) from usage_calls where source='worker' group by source_id"):
        cost[sid] = c or 0
    reports = dict(db.execute("select worker_id, text from worker_reports"))
    steer = defaultdict(list)
    for wid, at, mode, text, source in db.execute(
            "select worker_id, at, mode, text, source from worker_messages order by at"):
        steer[wid].append(f"  - {hm(at)} [{mode}/{source}] {clip(text, 600)}")
    blocks = []
    for wid, state, created, job, data in db.execute(
            "select id, state, created_at, job, data from workers order by created_at"):
        d = json.loads(data)
        task = d.get("task") or job or ""
        o = d.get("outcome") or {}
        b = [f"## Worker {wid[:8]} — {d.get('title')}",
             f"state: {state}; created {hm(created)}; started {d.get('startedAt')}; ended {d.get('endedAt')}; "
             f"model: {d.get('model')}; cost ${cost.get(wid, 0):.2f}; brief {len(task)} chars",
             f"outcome: {o.get('kind')} — {clip(o.get('summary') or d.get('lastLine') or '', 600)}",
             "", "### Brief", clip(task, 9000), ""]
        if steer.get(wid):
            b += ["### Messages sent to the worker"] + steer[wid] + [""]
        if reports.get(wid):
            b += ["### Final report", clip(reports[wid], 1800), ""]
        blocks.append("\n".join(b))
    # split into ~250 KB files for agent intake
    part, size, n = [], 0, 1
    for blk in blocks:
        if size + len(blk) > 250_000 and part:
            open(os.path.join(OUT, f"workers-{n}.md"), "w").write("\n\n".join(part)); n += 1; part, size = [], 0
        part.append(blk); size += len(blk)
    if part:
        open(os.path.join(OUT, f"workers-{n}.md"), "w").write("\n\n".join(part))


if __name__ == "__main__":
    main()
