#!/usr/bin/env python3
"""Research eval: score search providers and research workers on your own questions.

  research-eval.py search  [--providers exa,tinyfish] [--judge M] [--jobs N] [--limit N]
  research-eval.py answers [--model M] [--judge M] [--limit N] [--ids a,b] [--jobs 6] [--run ID [--regrade]]
  research-eval.py compare <runA> <runB>
  research-eval.py show <run>

Data lives in $RESEARCH_EVAL_DIR (default <repo>/local/evals/research), kept out of git:
  search.jsonl     {id, kind: real|fresh, query, target?}   target: regex the expected page's
                   url or title matches (fresh known items)
  questions.jsonl  {id, question, intent, asOf, checks: [{id, kind: must|must_not, text}], source}
  runs/<run>/      results.json per run; answer runs also keep <qid>/NOTE.md and trace.jsonl

Search runs `web search --provider P --json` per query. Answer runs one headless Dig per question
(`omp -p` as the roster's researcher with the worker field guide), then `web check` on the note and
a judge from another model family grades each check and each cited sentence against its page.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import tomllib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("RESEARCH_EVAL_DIR") or os.path.join(REPO, "local", "evals", "research")
WEB = os.environ.get("WEB_BIN") or "web"
OMP = os.environ.get("OMP_BIN") or "omp"

# List price per 1,000 searches, USD, as configured in `web` (Exa type "lite"; TinyFish free pool).
# Source: provider pricing pages read 2026-10-22 (research-shape SearchAPILandscape lane).
PRICE_PER_1K = {"exa": 4.0, "tinyfish": 0.0, "brave": 5.0, "serper": 1.0}
WORKER_TOOLS = "read,bash,write,grep,glob"
DIG_MAX_TIME = "20m"
PAGE_CHARS = 20000          # judge sees a cited page whole up to this size
HEAD_CHARS = 4000           # longer pages: this head plus windows around the cited terms
JUDGE_ORDER = ("verifier", "opus", "astra", "gemini")


class EvalError(Exception):
    pass


# ---------------------------------------------------------------- roster and models

def roster() -> dict:
    with open(os.path.join(REPO, "roster.toml"), "rb") as fh:
        return tomllib.load(fh).get("agents", {})


def family_of(model: str) -> str:
    for a in roster().values():
        if a.get("model") == model:
            return a.get("family", "")
    parts = model.split("/")
    if parts[0] == "openrouter" and len(parts) > 2:
        return parts[1]
    return {"openai-codex": "openai", "google-antigravity": "google"}.get(parts[0], parts[0])


def resolve_model(name: str | None, default_agent: str) -> tuple[str, str]:
    """A roster agent name or a model id -> (model, thinking)."""
    agents = roster()
    a = agents.get(name or default_agent)
    if a:
        return a["model"], a.get("thinking", "medium")
    if not name:
        raise EvalError(f"roster.toml has no agent '{default_agent}'")
    return name, "medium"


def pick_judge(name: str | None, avoid_family: str | None) -> tuple[str, str]:
    if name:
        model, thinking = resolve_model(name, "verifier")
        if avoid_family and family_of(model) == avoid_family:
            raise EvalError(f"judge {model} is the worker's family ({avoid_family}); pick another")
        return model, thinking
    agents = roster()
    for key in JUDGE_ORDER:
        a = agents.get(key)
        if a and a.get("family") != avoid_family:
            return a["model"], a.get("thinking", "medium")
    raise EvalError("no roster agent outside the worker's family to judge with")


# ---------------------------------------------------------------- omp

def omp_run(prompt: str, model: str, *, thinking: str, tools: str, cwd: str,
            env: dict | None = None, append_system: str | None = None,
            system: str | None = None, max_time: str | None = None,
            trace_path: str | None = None, timeout: int = 1800) -> dict:
    """Run one headless omp session; return final text, cost, wall seconds, tool calls."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(prompt)
        prompt_file = fh.name
    cmd = [OMP, "-p", "--mode", "json", "--no-session", "--no-title", "--no-skills",
           "--no-rules", "--no-extensions", "--model", model, "--thinking", thinking,
           "--tools", tools]
    if system:
        cmd += ["--system-prompt", system]
    if append_system:
        cmd += ["--append-system-prompt", append_system]
    if max_time:
        cmd += ["--max-time", max_time]
    cmd.append("@" + prompt_file)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})},
                           capture_output=True, text=True, timeout=timeout)
        out, err, code = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err, code = "timeout", -1
    finally:
        os.unlink(prompt_file)
    wall = time.time() - t0
    cost, text, calls, errors = 0.0, "", [], []
    trace = open(trace_path, "w") if trace_path else None
    for line in out.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "message_end":
            continue
        m = e.get("message") or {}
        if m.get("role") == "assistant":
            cost += ((m.get("usage") or {}).get("cost") or {}).get("total") or 0.0
            if m.get("errorMessage"):
                errors.append(m["errorMessage"])
            parts = m.get("content") or []
            t = "".join(c.get("text", "") for c in parts if c.get("type") == "text")
            if t.strip():
                text = t
            for c in parts:
                if c.get("type") == "toolCall":
                    call = {"tool": c.get("name"), "args": c.get("arguments")}
                    calls.append(call)
                    if trace:
                        trace.write(json.dumps(call) + "\n")
        elif m.get("role") == "toolResult" and trace:
            body = "".join(c.get("text", "") for c in (m.get("content") or []) if c.get("type") == "text")
            trace.write(json.dumps({"result": m.get("toolName"), "error": m.get("isError", False),
                                    "head": body[:400]}) + "\n")
    if trace:
        trace.close()
    if code != 0 and not text:
        errors.append(f"omp exit {code}: {err.strip()[-400:]}")
    return {"text": text, "cost": round(cost, 6), "seconds": round(wall, 1),
            "calls": calls, "errors": errors}


def judge_json(prompt: str, model: str, thinking: str) -> tuple[dict, float]:
    """Ask the judge; parse the first JSON object in its reply (one retry)."""
    cost = 0.0
    for _ in range(2):
        r = omp_run(prompt, model, thinking=thinking, tools="read", cwd=tempfile.gettempdir(),
                    system="You are a strict, careful grader. Reply with one JSON object only.")
        cost += r["cost"]
        text = r["text"]
        start = text.find("{")
        while start != -1:
            try:
                return json.JSONDecoder().raw_decode(text[start:])[0], cost
            except ValueError:
                start = text.find("{", start + 1)
    raise EvalError(f"judge returned no JSON: {text[:300]!r} {r['errors']}")


# ---------------------------------------------------------------- data

def load_jsonl(name: str) -> list[dict]:
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        raise EvalError(f"missing {path}")
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def run_dir(run: str) -> str:
    d = run if os.path.isdir(run) else os.path.join(DATA, "runs", run)
    if not os.path.isdir(d):
        raise EvalError(f"no run {run} under {os.path.join(DATA, 'runs')}")
    return d


def write_json(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def p50(xs: list[float]) -> float | None:
    return round(statistics.median(xs), 2) if xs else None


def table(headers: list[str], rows: list[list]) -> str:
    cells = [[("" if c is None else str(c)) for c in r] for r in rows]
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in cells]
    return "\n".join(out)


# ---------------------------------------------------------------- search

SEARCH_JUDGE = """An AI research agent will try to answer the query below by opening pages from ONE of these \
result lists. Score every list 0-10 for how well an agent could answer the query by fetching from it: \
relevance to what the query actually asks, primary sources (official docs, papers, repos, first-hand \
reports) over SEO and aggregator pages, coverage, and freshness where the query needs recent information. \
Judge from titles, URLs and dates only. An empty list scores 0.

Query: {query}

{lists}

Reply with JSON: {{"scores": {{"A": n, ...}}, "best": "<label>", "why": "<one sentence>"}}"""


def web_search(query: str, provider: str, lane: str) -> dict:
    cmd = [WEB, "search", query, "--provider", provider, "--json", "--limit", "10", "--lane", lane]
    for attempt in range(2):
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        lat = time.time() - t0
        if p.returncode == 0:
            rows = json.loads(p.stdout).get("results") or []
            return {"results": [{"title": r.get("title") or "", "url": r.get("url") or "",
                                 "date": r.get("date") or ""} for r in rows[:10]],
                    "latency": round(lat, 2), "error": None}
        if p.returncode != 75 or attempt:
            return {"results": [], "latency": round(lat, 2),
                    "error": f"exit {p.returncode}: {(p.stderr or p.stdout).strip()[-300:]}"}
        time.sleep(5)


def fresh_rank(target: str, results: list[dict]) -> int | None:
    rx = re.compile(target, re.I)
    for i, r in enumerate(results, 1):
        if rx.search(r["url"]) or rx.search(r["title"]):
            return i
    return None


def cmd_search(a) -> int:
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    unknown = [p for p in providers if p not in PRICE_PER_1K]
    if unknown:
        raise EvalError(f"unknown provider(s) {unknown}; known: {', '.join(PRICE_PER_1K)}")
    items = load_jsonl("search.jsonl")[: a.limit or None]
    judge_model, judge_thinking = pick_judge(a.judge, None)
    run = a.run or "search-" + dt.datetime.now().strftime("%Y%m%d-%H%M")
    out_dir = os.path.join(DATA, "runs", run)
    os.makedirs(out_dir, exist_ok=True)
    lane = f"eval-{run}/search"
    started, t0 = now(), time.time()
    print(f"search eval {run}: {len(items)} queries x {', '.join(providers)}; judge {judge_model}",
          file=sys.stderr)

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {(it["id"], p): ex.submit(web_search, it["query"], p, lane)
                for it in items for p in providers}
        got = {k: f.result() for k, f in futs.items()}

    def judge_one(it):
        if it.get("kind") == "fresh" or len(providers) < 2:
            return None
        labels = [chr(65 + i) for i in range(len(providers))]
        order = providers[:]
        random.Random(f"{run}:{it['id']}").shuffle(order)
        blocks = []
        for lab, p in zip(labels, order):
            rows = got[(it["id"], p)]["results"]
            lines = [f"  {i}. {r['title']} · {r['url']}" + (f" · {r['date']}" if r["date"] else "")
                     for i, r in enumerate(rows, 1)] or ["  (no results)"]
            blocks.append(f"List {lab}:\n" + "\n".join(lines))
        verdict, cost = judge_json(SEARCH_JUDGE.format(query=it["query"], lists="\n\n".join(blocks)),
                                   judge_model, judge_thinking)
        scores = {p: verdict.get("scores", {}).get(lab) for lab, p in zip(labels, order)}
        best = dict(zip(labels, order)).get(verdict.get("best"))
        return {"scores": scores, "best": best, "why": verdict.get("why"), "cost": cost}

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        judged = dict(zip([it["id"] for it in items], ex.map(judge_one, items)))

    per_query = []
    for it in items:
        row = {"id": it["id"], "kind": it.get("kind"), "query": it["query"], "providers": {}}
        for p in providers:
            g = got[(it["id"], p)]
            entry = {"latency": g["latency"], "error": g["error"], "results": g["results"]}
            if it.get("kind") == "fresh":
                entry["rank"] = fresh_rank(it["target"], g["results"])
            row["providers"][p] = entry
        if judged[it["id"]]:
            row["judge"] = judged[it["id"]]
        per_query.append(row)

    summary = {}
    for p in providers:
        scores = [q["judge"]["scores"][p] for q in per_query
                  if q.get("judge") and isinstance(q["judge"]["scores"].get(p), (int, float))]
        fresh = [q["providers"][p]["rank"] for q in per_query if q["kind"] == "fresh"]
        lats = [q["providers"][p]["latency"] for q in per_query if not q["providers"][p]["error"]]
        summary[p] = {
            "judgeMean": round(statistics.mean(scores), 2) if scores else None,
            "judged": len(scores),
            "wins": sum(1 for q in per_query if q.get("judge") and q["judge"]["best"] == p),
            "freshHits": sum(1 for r in fresh if r is not None and r <= 10),
            "freshAt1": sum(1 for r in fresh if r == 1),
            "fresh": len(fresh),
            "errors": sum(1 for q in per_query if q["providers"][p]["error"]),
            "p50Latency": p50(lats),
            "per1k": PRICE_PER_1K[p],
        }
    judge_cost = round(sum(q["judge"]["cost"] for q in per_query if q.get("judge")), 4)
    result = {"kind": "search", "run": run, "started": started, "finished": now(),
              "wallSeconds": round(time.time() - t0), "judge": judge_model, "lane": lane,
              "judgeCost": judge_cost, "summary": summary, "queries": per_query}
    write_json(os.path.join(out_dir, "results.json"), result)
    print_search(result)
    return 0


def print_search(r: dict) -> None:
    rows = []
    for p, s in r["summary"].items():
        rows.append([p, s["judgeMean"], f"{s['wins']}/{s['judged']}",
                     f"{s['freshHits']}/{s['fresh']} ({s['freshAt1']} at 1)",
                     s["p50Latency"], f"${s['per1k']:g}", s["errors"]])
    print(f"search {r['run']} · judge {r['judge']} · {r['wallSeconds']}s · judge ${r['judgeCost']}")
    print(table(["provider", "judge mean", "wins", "fresh in top 10", "p50 s", "per 1k", "errors"], rows))


# ---------------------------------------------------------------- answers

# Mirrors the Dig brief in skills/nstack-research/SKILL.md (Dig step 1, read floor and stop rule).
DIG_TASK = """Dig: {question}

Output: {dir}/NOTE.md (run slug `{slug}`, today {today}). Lane: `{lane}`; pass `--lane {lane}` on every \
`web` call.

Read floor: **every claim needs at least one page read through `web`; search results may choose what to \
read but are never quoted as evidence**.
Stop rule: **search and read until new pages stop adding distinct evidence or changing the verdict, then \
stop and say why in `stoppedBecause`; there is no search or read budget**.
No repo edits, tests or formatters."""

ANSWER_JUDGE = """You grade one research note against a fixed answer key and against its own cited pages.

Question: {question}

NOTE:
<<<
{note}
>>>

1. Answer key. For each check decide pass true/false from the NOTE alone.
   kind "must": pass when the note states this fact (same meaning; exact wording not needed; a hedged \
or vague mention that would not let a reader act on the fact fails).
   kind "must_not": pass when the note does NOT assert this wrong claim; fail when it asserts it.
{checks}

2. Citations. For each numbered sentence below, decide whether the cited page text supports it: every \
number, name, version, date and qualifier in the sentence must be in or directly implied by the cited \
pages. A page that could not be read counts as unsupported.
{sentences}

CITED PAGES:
{pages}

Reply with JSON:
{{"checks": [{{"id": "<check id>", "pass": true|false, "why": "<short>"}}],
  "citations": [{{"n": <sentence number>, "supported": true|false, "why": "<short>"}}]}}"""

CITE_RE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")
SOURCE_RE = re.compile(r"^\s*\[(\d+)\]")
URL_RE = re.compile(r"https?://[^\s)>\]]+")


def parse_note(text: str) -> dict:
    """Split a Dig note into cited sentences, uncited sentences and its sources (n -> urls)."""
    body, sources, section = [], {}, "body"
    for i, line in enumerate(text.splitlines()):
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if line.startswith("#") or (i < 3 and line.startswith("Dig ·")):
            continue
        if section == "sources":
            m = SOURCE_RE.match(line)
            urls = [u.rstrip(".,;") for u in URL_RE.findall(line)]
            if m and urls:
                sources[int(m.group(1))] = urls
        elif section != "unsure" and line.strip():
            body.append(line.strip().lstrip("-*• ").strip())
    cited, uncited = [], []
    for line in body:
        for s in re.split(r"(?<=[.!?\]])\s+(?=[A-Z\"(])", line):
            s = s.strip()
            if not s:
                continue
            refs = sorted({int(n) for g in CITE_RE.findall(s) for n in _expand(g)})
            (cited if refs else uncited).append({"text": s, "refs": refs} if refs else s)
    uncited = [u for u in uncited if len(u) > 40 and not u.endswith(":")]
    return {"cited": cited, "uncited": uncited, "sources": sources}


def _expand(group: str) -> list[int]:
    out = []
    for part in re.split(r"\s*,\s*", group):
        if re.search(r"[–-]", part):
            lo, hi = (int(x) for x in re.split(r"\s*[–-]\s*", part))
            out += list(range(lo, hi + 1)) if 0 <= hi - lo <= 20 else [lo, hi]
        elif part:
            out.append(int(part))
    return out


def page_text(url: str, lane: str, sentences: list[str]) -> str:
    """The stored page for the judge: whole up to PAGE_CHARS, else its head plus windows around
    each number, quote and name in the sentences that cite it (numbers first)."""
    p = subprocess.run([WEB, "read", url, "--max-chars", str(PAGE_CHARS), "--lane", lane],
                       capture_output=True, text=True, timeout=240)
    if p.returncode != 0:
        return f"(could not read: {(p.stderr or p.stdout).strip()[-200:]})"
    size = re.search(r"\| (\d+) chars \|", p.stdout)
    path = re.search(r"saved (\S+?\.md)\b", p.stdout)
    if not size or int(size.group(1)) <= PAGE_CHARS or not path or not os.path.exists(path.group(1)):
        return p.stdout
    text = open(path.group(1)).read()
    low = text.lower()
    clean = [CITE_RE.sub("", s) for s in sentences]
    tiers = [  # numbers decide most support calls, so they get the window budget first
        [t for s in clean for t in re.findall(r"\d+(?:[.,]\d+)+%?|\d{2,}%?", s)],
        [t.strip('`"') for s in clean for t in re.findall(r"`[^`]{3,40}`|\"[^\"]{4,60}\"", s)],
        [t for s in clean for t in re.findall(r"(?<!^)\b[A-Z][\w.-]{3,}", s)],
    ]
    spans, used = [], 0
    for t in dict.fromkeys(t for tier in tiers for t in tier):
        start = 0
        for _ in range(2):
            i = low.find(t.lower(), start)
            if i < 0 or used >= PAGE_CHARS:
                break
            a, b = max(0, i - 500), i + len(t) + 500
            if not any(x <= i and i + len(t) <= y for x, y in spans):
                spans.append([a, b])
                used += b - a
            start = i + len(t)
    merged = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    windows = "\n…\n".join(text[a:b] for a, b in merged)
    return (p.stdout[:HEAD_CHARS] + f"\n[… page is {len(text)} chars; passages around the cited terms:]\n"
            + windows)


def web_check(qdir: str, lane: str) -> dict:
    """`web check` exits 0 even with FAIL lines; its summary line carries the counts."""
    p = subprocess.run([WEB, "check", qdir, "--lane", lane], capture_output=True, text=True,
                       timeout=300, env={**os.environ, "WEB_LANE": lane})
    out = (p.stdout + p.stderr).strip()
    m = re.search(r"check \S+: (\d+) FAIL, (\d+) WARN", out)
    return {"ok": p.returncode == 0 and m is not None and m.group(1) == "0",
            "fail": int(m.group(1)) if m else None, "warn": int(m.group(2)) if m else None,
            "output": out[-2000:]}


def system_prompt_file(out_dir: str) -> str:
    """The researcher agent prompt plus the worker field guide, as one appended system prompt."""
    parts = []
    for rel in ("agents/researcher.md", "skills/nstack-research-worker/SKILL.md"):
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            raise EvalError(f"missing {path}")
        text = open(path).read()
        if text.startswith("---"):
            text = text.split("---", 2)[2]
        parts.append(text.strip())
    path = os.path.join(out_dir, "worker-prompt.md")
    with open(path, "w") as fh:
        fh.write("\n\n".join(parts) + "\n")
    return path


DIG_FIELDS = ("id", "intent", "minutes", "cost", "toolCalls", "searches", "reads", "reply", "errors")


def answer_one(q: dict, ctx: dict) -> dict:
    qdir = os.path.join(ctx["dir"], q["id"])
    done = os.path.join(qdir, "result.json")
    lane = f"eval-{ctx['run']}/{q['id']}"
    if os.path.exists(done):
        with open(done) as fh:
            res = json.load(fh)
        if not ctx["regrade"] or res.get("status") == "no-note":
            return res
        return grade(q, ctx, {k: res[k] for k in DIG_FIELDS if k in res}, qdir, lane)
    os.makedirs(qdir, exist_ok=True)
    task = DIG_TASK.format(question=q["question"], dir=qdir, slug=q["id"], lane=lane,
                           today=dt.date.today().isoformat())
    dig = omp_run(task, ctx["model"], thinking=ctx["thinking"], tools=WORKER_TOOLS, cwd=qdir,
                  env={"WEB_LANE": lane}, append_system=ctx["prompt"], max_time=DIG_MAX_TIME,
                  trace_path=os.path.join(qdir, "trace.jsonl"))
    web_cmds = [c["args"].get("command", "") for c in dig["calls"]
                if c["tool"] == "bash" and isinstance(c.get("args"), dict)]
    res = {"id": q["id"], "intent": q.get("intent"), "minutes": round(dig["seconds"] / 60, 1),
           "cost": dig["cost"], "toolCalls": len(dig["calls"]),
           "searches": sum(len(re.findall(r"\bweb\s+search\b", c)) for c in web_cmds),
           "reads": sum(len(re.findall(r"\bweb\s+read\b", c)) for c in web_cmds),
           "reply": dig["text"][-500:], "errors": dig["errors"]}
    if not os.path.exists(os.path.join(qdir, "NOTE.md")):
        res.update(status="no-note", checks=[{"id": c["id"], "kind": c["kind"], "pass": False,
                                              "why": "no note"} for c in q["checks"]])
        write_json(done, res)
        return res
    return grade(q, ctx, res, qdir, lane)


def grade(q: dict, ctx: dict, res: dict, qdir: str, lane: str) -> dict:
    """`web check` the note, then have the judge grade the checks and every cited sentence."""
    note = open(os.path.join(qdir, "NOTE.md")).read()
    res["webCheck"] = web_check(qdir, lane)
    parsed = parse_note(note)
    cited_refs = {n for s in parsed["cited"] for n in s["refs"]}
    judge_lane = f"eval-{ctx['run']}/judge"
    blocks = []
    for n, urls in sorted(parsed["sources"].items()):
        if n in cited_refs:
            texts = [s["text"] for s in parsed["cited"] if n in s["refs"]]
            blocks += [f"[{n}] {u}\n<<<\n{page_text(u, judge_lane, texts)}\n>>>" for u in urls]
    sentences = "\n".join(f"S{i}: {s['text']}" for i, s in enumerate(parsed["cited"], 1)) or "(none)"
    checks = "\n".join(f"   - {c['id']} [{c['kind']}]: {c['text']}" for c in q["checks"])
    verdict, jcost = judge_json(ANSWER_JUDGE.format(question=q["question"], note=note, checks=checks,
                                                    sentences=sentences,
                                                    pages="\n\n".join(blocks) or "(none)"),
                                ctx["judge"], ctx["judge_thinking"])
    by_id = {str(c.get("id")): c for c in verdict.get("checks", [])}
    res["checks"] = [{"id": c["id"], "kind": c["kind"],
                      "pass": bool(by_id.get(c["id"], {}).get("pass")),
                      "why": by_id.get(c["id"], {}).get("why", "not graded")} for c in q["checks"]]
    by_n = {int(c.get("n")): c for c in verdict.get("citations", []) if str(c.get("n", "")).isdigit()}
    res["citations"] = [{"n": i, "text": s["text"], "refs": s["refs"],
                         "unknownRef": [r for r in s["refs"] if r not in parsed["sources"]],
                         "supported": bool(by_n.get(i, {}).get("supported")),
                         "why": by_n.get(i, {}).get("why", "not graded")}
                        for i, s in enumerate(parsed["cited"], 1)]
    res["uncited"] = parsed["uncited"]
    res["sources"] = len(parsed["sources"])
    res["judgeCost"] = jcost
    res["status"] = "graded"
    write_json(os.path.join(qdir, "result.json"), res)
    return res


def summarize_answers(results: list[dict]) -> dict:
    def block(rs):
        checks = [c for r in rs for c in r["checks"]]
        cites = [c for r in rs for c in r.get("citations", [])]
        return {
            "n": len(rs),
            "checksPassed": round(sum(c["pass"] for c in checks) / len(checks), 3) if checks else None,
            "allPassed": sum(all(c["pass"] for c in r["checks"]) for r in rs),
            "mustNotHit": sum(1 for c in checks if c["kind"] == "must_not" and not c["pass"]),
            "citesSupported": round(sum(c["supported"] for c in cites) / len(cites), 3) if cites else None,
            "uncited": sum(len(r.get("uncited", [])) for r in rs),
            "webCheckOk": sum(1 for r in rs if (r.get("webCheck") or {}).get("ok")),
            "noNote": sum(1 for r in rs if r.get("status") == "no-note"),
            "medianMinutes": p50([r["minutes"] for r in rs]),
            "cost": round(sum(r["cost"] for r in rs), 3),
            "judgeCost": round(sum(r.get("judgeCost", 0) for r in rs), 3),
        }
    out = {"all": block(results)}
    for intent in sorted({r.get("intent") or "?" for r in results}):
        out[intent] = block([r for r in results if (r.get("intent") or "?") == intent])
    return out


def cmd_answers(a) -> int:
    questions = everything = load_jsonl("questions.jsonl")
    if a.ids:
        want = set(a.ids.split(","))
        questions = [q for q in questions if q["id"] in want]
        missing = want - {q["id"] for q in questions}
        if missing:
            raise EvalError(f"no question(s) {sorted(missing)}")
    questions = questions[: a.limit or None]
    model, thinking = resolve_model(a.model, "researcher")
    judge, judge_thinking = pick_judge(a.judge, family_of(model))
    if not shutil.which(WEB):
        raise EvalError(f"`{WEB}` is not on PATH")
    run = a.run or "answers-" + dt.datetime.now().strftime("%Y%m%d-%H%M")
    out_dir = os.path.join(DATA, "runs", run)
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, "results.json")
    prior = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    if prior and prior.get("worker") != model:
        raise EvalError(f"run {run} was made with worker {prior.get('worker')}; start a new run")
    if prior and prior.get("judge") != judge and not a.regrade:
        raise EvalError(f"run {run} was graded by {prior.get('judge')}; pass --regrade to regrade it")
    ctx = {"run": run, "dir": out_dir, "model": model, "thinking": thinking, "judge": judge,
           "judge_thinking": judge_thinking, "prompt": system_prompt_file(out_dir),
           "regrade": a.regrade}
    started, t0 = prior.get("started") or now(), time.time()
    print(f"answers {run}: {len(questions)} questions; worker {model}; judge {judge}", file=sys.stderr)
    # A run covers whatever questions it has graded so far; --ids/--limit add to or redo a subset.
    lock, results = threading.Lock(), {q["id"]: q for q in prior.get("questions", [])}

    def save():
        ordered = [results[q["id"]] for q in everything if q["id"] in results]
        write_json(meta_path, {"kind": "answers", "run": run, "worker": model, "workerThinking": thinking,
                               "judge": judge, "started": started, "finished": now(),
                               "wallSeconds": prior.get("wallSeconds", 0)
                               + (0 if a.regrade else round(time.time() - t0)),
                               "summary": summarize_answers(ordered), "questions": ordered})

    def task(q):
        try:
            r = answer_one(q, ctx)
        except Exception as exc:          # one broken question must not sink the run
            r = {"id": q["id"], "intent": q.get("intent"), "status": "error", "error": str(exc),
                 "minutes": 0, "cost": 0, "checks": [{"id": c["id"], "kind": c["kind"], "pass": False,
                                                        "why": "error"} for c in q["checks"]]}
        with lock:
            results[q["id"]] = r
            save()
        n_pass = sum(c["pass"] for c in r["checks"])
        print(f"  {q['id']}: {r.get('status')} checks {n_pass}/{len(r['checks'])} "
              f"{r['minutes']} min ${r['cost']:.3f}", file=sys.stderr)

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(task, questions))
    print_answers(json.load(open(meta_path)))
    return 0


def print_answers(r: dict) -> None:
    rows = []
    for k, s in r["summary"].items():
        rows.append([k, s["n"], s["checksPassed"], f"{s['allPassed']}/{s['n']}", s["mustNotHit"],
                     s["citesSupported"], s["uncited"], f"{s['webCheckOk']}/{s['n']}",
                     s["medianMinutes"], f"${s['cost']}"])
    print(f"answers {r['run']} · worker {r['worker']} · judge {r['judge']} · {r['wallSeconds']}s · "
          f"judge ${r['summary']['all']['judgeCost']}")
    print(table(["intent", "n", "checks passed", "all checks", "must_not hit", "cites supported",
                 "uncited", "web check ok", "median min", "worker cost"], rows))
    bad = [q for q in r["questions"] if q.get("status") != "graded"]
    for q in bad:
        print(f"  {q['id']}: {q.get('status')} {q.get('error') or ''}".rstrip())


def cmd_compare(a) -> int:
    ra, rb = (json.load(open(os.path.join(run_dir(x), "results.json"))) for x in (a.a, a.b))
    if ra.get("kind") != "answers" or rb.get("kind") != "answers":
        raise EvalError("compare takes two answer runs")
    if ra["judge"] != rb["judge"]:
        print(f"note: different judges ({ra['judge']} vs {rb['judge']})")
    qa = {q["id"]: q for q in ra["questions"]}
    qb = {q["id"]: q for q in rb["questions"]}
    shared = [i for i in qa if i in qb]

    def score(q):
        return sum(c["pass"] for c in q["checks"]) / len(q["checks"]) if q["checks"] else 0.0

    def cites(q):
        c = q.get("citations") or []
        return sum(x["supported"] for x in c) / len(c) if c else None

    rows, diffs, better, worse = [], [], 0, 0
    for i in shared:
        d = score(qb[i]) - score(qa[i])
        diffs.append(d)
        better += d > 0
        worse += d < 0
        ca, cb = cites(qa[i]), cites(qb[i])
        rows.append([i, qa[i].get("intent"), f"{score(qa[i]):.2f} → {score(qb[i]):.2f}", f"{d:+.2f}",
                     "" if ca is None or cb is None else f"{ca:.2f} → {cb:.2f}",
                     f"{qa[i]['minutes']} → {qb[i]['minutes']}",
                     f"{qa[i]['cost']:.3f} → {qb[i]['cost']:.3f}"])
    print(f"{ra['run']} ({ra['worker']}) → {rb['run']} ({rb['worker']}): {len(shared)} shared questions")
    print(table(["question", "intent", "checks", "diff", "cites supported", "minutes", "cost $"], rows))
    if diffs:
        print(f"mean check diff {statistics.mean(diffs):+.3f}; B better on {better}, worse on {worse}, "
              f"same on {len(shared) - better - worse}")
    return 0


def cmd_show(a) -> int:
    r = json.load(open(os.path.join(run_dir(a.run), "results.json")))
    (print_search if r["kind"] == "search" else print_answers)(r)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="research-eval", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="score search providers on search.jsonl")
    s.add_argument("--providers", default="exa,tinyfish")
    s.add_argument("--judge", help="roster agent or model id (default: the roster verifier)")
    s.add_argument("--jobs", type=int, default=4)
    s.add_argument("--limit", type=int)
    s.add_argument("--run", help="run id (default search-<timestamp>)")
    s.set_defaults(fn=cmd_search)
    w = sub.add_parser("answers", help="run one Dig per question and grade it")
    w.add_argument("--model", help="roster agent or model id (default: the roster researcher)")
    w.add_argument("--judge", help="roster agent or model id from another family")
    w.add_argument("--limit", type=int)
    w.add_argument("--ids", help="comma-separated question ids")
    w.add_argument("--jobs", type=int, default=6)
    w.add_argument("--run", help="run id; rerunning one resumes it (default answers-<timestamp>)")
    w.add_argument("--regrade", action="store_true",
                   help="with --run: keep the notes, rerun `web check` and the judge")
    w.set_defaults(fn=cmd_answers)
    c = sub.add_parser("compare", help="paired per-question differences of two answer runs")
    c.add_argument("a")
    c.add_argument("b")
    c.set_defaults(fn=cmd_compare)
    sh = sub.add_parser("show", help="print a run's summary table")
    sh.add_argument("run")
    sh.set_defaults(fn=cmd_show)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except EvalError as exc:
        print(f"research-eval: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
