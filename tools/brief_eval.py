#!/usr/bin/env python3
"""brief_eval.py: does a briefing agent in front of the executing agent get Nate a better result, and at what cost?

  tools/brief_eval.py run    --task T[,T...] --arm direct --arm brief:NAME [--reps N] [--jobs N]
  tools/brief_eval.py briefs --task T[,T...] --arm brief:NAME [--reps N] [--jobs N]   brief only, scored on the rubric
  tools/brief_eval.py judge  [--task T,...]     judge every finished run that has no verdict yet
  tools/brief_eval.py report [--task T,...] [--arm A ...]
  tools/brief_eval.py exclude RUN --reason WHY  keep a run out of the report (a leak the sandbox could not stop)

A task replays a real past request of Nate's (local/evals/brief/tasks/<id>/task.json: repo, commit, request) in a clone
of the repo at the commit before he asked. The clone holds only the history up to that commit and has no remote. Arms:
  direct      Nate's request, verbatim, is the executor's first message.
  brief:NAME  a briefer runs the instructions in local/evals/brief/briefers/NAME.md over the request in the same clone,
              and its final message, verbatim, is a fresh executor's first message. brief:shipped runs the
              instructions /brief ships (extensions/brief.md), the way /brief does.
Briefer and executor run Opus 5.5 at high thinking, Nate's default session model. A run is scored at its first stop
(the executor's final reply and the repo diff) against the task's hindsight rubric (rubric.json) by GPT-6 Astra, which
sees only the run's directory and so does not know the arm. `briefs` scores a brief alone against the same rubric: a
cheap signal for tuning briefer instructions before paying for executors.

Every run gets a project .omp/ layer that turns off Executor, Dross memory, the agent bridge and X, and routes muse,
gemini and researcher subagents to Sonnet (subscriptions only). Every session also runs under sandbox-exec (see
`sandbox`): Nate's project trees (bar what omp itself loads), omp's sessions and prompt history, the brain, account
credentials and a task's `deny_paths` are unreadable, and local services are unreachable. A replay that finds the real
outcome measures nothing, and one that acts as Nate (an Executor call, his Chrome) changes his real accounts. Runs that
still try those paths, or name the repo on GitHub, are listed as leaks.
Sessions, briefs, verdicts and metrics live in local/evals/brief/meta/<run>/; the judge's view of a run (clone,
reply.md, diff.patch) lives in /tmp/brief-eval/<run>/, outside any directory whose AGENTS.md omp would load.
"""
import argparse, concurrent.futures, json, os, random, re, secrets, shutil, statistics, subprocess, sys, threading, time
from pathlib import Path

HOME = Path.home()
OMP = HOME / ".bun" / "bin" / "omp"
OMP_AGENT = HOME / ".omp" / "agent"
REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "local" / "evals" / "brief"
VIEWS = Path("/tmp/brief-eval")
AGENT_MODEL = ("anthropic/claude-opus-5-5", "high")
JUDGE_MODEL = ("openai-codex/gpt-6-astra", "high")
BRIEF_JUDGE_MODEL = ("openai-codex/gpt-6-astra", "medium")
EXECUTOR_LIMITS = ("60m", "30")   # --max-time, --max-cost (USD at catalog prices) per executor run
BRIEFER_LIMITS = ("25m", "10")
JUDGE_LIMITS = ("20m", "10")
WEIGHT = {"must": 2, "should": 1, "must_not": 2}
MUST_NOT_PENALTY = 15

PROJECT_CONFIG = """\
task:
  agentModelOverrides:
    muse: anthropic/claude-sonnet-5-5:medium
    gemini: anthropic/claude-sonnet-5-5:high
    researcher: anthropic/claude-sonnet-5-5:high
disabledExtensions:
  - extension-module:sourcewire
  - extension-module:turn-timer
  - extension-module:code-visibility
  - extension-module:agent-bridge
  - skill:bambu-labs
"""
PROJECT_MCP = {"mcpServers": {
    "executor": {"type": "http", "url": "http://127.0.0.1:1/mcp", "enabled": False},
    "dross-memory": {"type": "http", "url": "http://127.0.0.1:1/mcp", "enabled": False},
    "agent-bridge": {"type": "stdio", "command": "true", "enabled": False},
    "x-api": {"type": "stdio", "command": "true", "enabled": False},
}}

JUDGE_TASK = """\
You are judging one coding agent's answer to a request Nate made. The agent worked in a clone of his repository at \
the commit before he asked. Judge what Nate got back at the agent's first stop: its final reply (reply.md) and the \
repository state (the clone in {repo_dir}/, and diff.patch, its full change against the starting commit). Read both, \
and inspect or run things in the clone when a criterion needs it; change nothing.

Nate's request, verbatim:
{request}

The rubric comes from what Nate turned out to want in the real session that followed this request. Reference, not a \
template (many good answers differ from it): {ideal}

Criteria ("must" and "should" pass when met; "must_not" passes when NOT violated):
{criteria}

Then give satisfaction 1-10: how satisfied Nate would be if this were the reply to his request. He wants the outcome \
first, claims backed by evidence (paths, commands, links), nothing he said not to do yet, no scope he did not ask \
for, and plain words. Length and effort earn nothing on their own.

End with exactly one JSON object in a ```json block and nothing after it:
{{"criteria": [{{"id": "c1", "pass": true, "evidence": "quote or path:line"}}], "satisfaction": 7, "summary": "one sentence"}}
"""

BRIEF_JUDGE_TASK = """\
A briefing agent turned Nate's request into a brief for a fresh executing agent, which will follow every line as \
Nate's instruction. Judge how well the brief sets that agent up to deliver what Nate turned out to want.

Nate's request, verbatim:
{request}

What Nate turned out to want (reference): {ideal}

Criteria on the executor's eventual answer:
{criteria}

For each criterion: "covered" if the brief points the agent at it or hands it the facts that lead there, "silent" if \
the brief neither helps nor hinders, "conflict" if the brief steers the agent against it (orders the violation of a \
must_not, or rules out a must). Then list every order in the brief that neither Nate's words nor the brief's stated \
facts call for, each with its likely effect on the answer ("helps", "neutral" or "hurts").

The brief:
<brief>
{brief}
</brief>

End with exactly one JSON object in a ```json block and nothing after it:
{{"criteria": [{{"id": "c1", "verdict": "covered", "why": "..."}}], "unasked_orders": [{{"order": "...", "effect": "neutral"}}]}}
"""


def fenced(text):
    longest = max([0, *map(len, re.findall(r"`+", text))])
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}"


def load_task(tid):
    d = DATA / "tasks" / tid
    task = json.loads((d / "task.json").read_text())
    task["rubric"] = json.loads((d / "rubric.json").read_text())
    return task


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout


def write_project_layer(root):
    (root / ".omp").mkdir(parents=True, exist_ok=True)
    (root / ".omp" / "config.yml").write_text(PROJECT_CONFIG)
    (root / ".omp" / "mcp.json").write_text(json.dumps(PROJECT_MCP, indent=2))


def prepare_view(task, run_id):
    """/tmp/brief-eval/<run>/<repo name>: the repo at the task's commit, its history up to there, no remote."""
    view = VIEWS / run_id
    repo = view / Path(task["repo"]).name
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "fetch", "-q", "--no-tags", task["repo"], task["commit"])
    git(repo, "checkout", "-q", "-b", "main", "FETCH_HEAD")
    if (repo / ".omp" / "config.yml").exists() or (repo / ".omp" / "mcp.json").exists():
        raise RuntimeError(f"{task['id']}: the repo has its own .omp config; merge the run layer into it by hand")
    write_project_layer(view)
    write_project_layer(repo)
    with open(repo / ".git" / "info" / "exclude", "a") as f:
        f.write("\n/.omp/config.yml\n/.omp/mcp.json\n")
    return view, repo


def sandbox(task, run_id):
    """The sandbox-exec profile for every session of one run. Nothing under ~/Projects or ~/Desktop/Projects is
    readable except what omp loads (skills, commands, extensions, the web tool); nor omp's sessions and prompt history,
    the brain, GitHub credentials (private repos would show the later commits), the credentials of the CLIs that act
    as Nate (Executor, Google Workspace, gcloud, X), other runs, or the task's `deny_paths` (machine state the
    historical session changed; not executable either). No local service is reachable: Executor, Dross memory, the
    bridge and Chrome's debugging port all listen on localhost, and omp itself needs none of them. Writes go only to
    the run's clone, its records and the system temp dirs."""
    agent = OMP_AGENT
    meta = DATA / "meta" / run_id
    view = Path(os.path.realpath(VIEWS))
    readable = [HOME / "Projects" / "nstack" / d for d in ("skills", "commands", "extensions", "tools")] + [
        HOME / "Projects" / p for p in ("ios-toolkit", "pcb-toolkit/skills", "stepper-composer/skills",
                                        "term/integrations/omp", "agent-bridge-v2/extension")]
    denied = [Path(p).expanduser() for p in task.get("deny_paths", [])] or [Path("/nonexistent")]
    sub = lambda paths: " ".join(f'(subpath "{p}")' for p in paths)
    profile = meta / "sandbox.sb"
    profile.write_text(f"""(version 1)
(allow default)
(deny file-read* file-write* {sub([HOME / "Projects", HOME / "Desktop" / "Projects", view])})
(allow file-read* {sub(readable)})
(allow file-read* file-write* {sub([meta, view / run_id])})
(deny file-read* file-write* (regex #"^{str(task["repo"]).replace(".", "[.]")}[^/]*(/|$)"))
(deny file-read* file-write* process-exec* {sub(denied)})
(deny file-read* file-write* {sub([agent / "sessions", HOME / ".brain"])} (literal "{agent / 'history.db'}") (literal "{HOME / '.config/gh/hosts.yml'}"))
(deny file-read* file-write* {sub([HOME / d for d in (".executor", ".computer", ".xurl", ".config/gws", ".config/gcloud")])})
(deny network-outbound (remote ip "localhost:*"))
(deny file-write* {sub([agent / "skills", agent / "commands", agent / "extensions"])} {" ".join(f'(literal "{agent / n}")' for n in ("AGENTS.md", "RULES.md", "config.yml", "mcp.json"))})
""")
    return profile


def omp(prompt, cwd, session_dir, model, limits, log, run_id, task):
    """One headless omp session inside the run's sandbox, with its own web page store; returns its exit code, wall
    seconds and its start (UTC, for telling its own entries from history a subagent forked in)."""
    session_dir.mkdir(parents=True, exist_ok=True)
    profile = sandbox(task, run_id)
    cmd = ["sandbox-exec", "-f", str(profile), str(OMP), "-p", "--no-title", "--wait-async", "--model", model[0],
           "--thinking", model[1], "--session-dir", str(session_dir), "--max-time", limits[0], "--max-cost", limits[1],
           prompt]
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    env["WEB_HOME"] = str(DATA / "meta" / run_id / "web")
    since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    start = time.monotonic()
    with open(log, "w") as out:
        code = subprocess.run(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT, env=env).returncode
    return code, round(time.monotonic() - start, 1), since


def text_of(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    return "\n".join(b["text"] for b in content or [] if b.get("type") == "text")


def own_entries(path, since):
    """The session file's entries written by this run; a seance subagent's file also carries the forked history."""
    for line in path.read_text().splitlines():
        e = json.loads(line)
        if e.get("timestamp", since) >= since:
            yield e


def session_metrics(session_dir, since):
    """Usage over the root session and every subagent under it, and the root's last assistant text."""
    roots = sorted(p for p in session_dir.glob("*.jsonl"))
    if len(roots) != 1:
        raise RuntimeError(f"{session_dir}: expected one root session, found {len(roots)}")
    root = roots[0]
    files = [root, *sorted(root.with_suffix("").rglob("*.jsonl"))] if root.with_suffix("").is_dir() else [root]
    m = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "requests": 0, "tool_calls": 0,
         "subagents": len(files) - 1}
    final = ""
    calls = []
    for f in files:
        for e in own_entries(f, since):
            msg = e.get("message") or {}
            if e.get("type") != "message" or msg.get("role") != "assistant":
                continue
            u = msg.get("usage") or {}
            m["input"] += u.get("input", 0)
            m["output"] += u.get("output", 0)
            m["cache_read"] += u.get("cacheRead", 0)
            m["cache_write"] += u.get("cacheWrite", 0)
            m["cost_usd"] += (u.get("cost") or {}).get("total", 0) or 0
            m["requests"] += 1
            for b in msg.get("content") or []:
                if b.get("type") == "toolCall":
                    calls.append((b["name"], json.dumps(b.get("arguments"))))
            if f == root and text_of(msg).strip():
                final = text_of(msg).strip()
    m["tool_calls"] = len(calls)
    m["tokens"] = m["input"] + m["output"] + m["cache_read"] + m["cache_write"]
    m["cost_usd"] = round(m["cost_usd"], 3)
    return m, final, calls


def leaks(task, calls, texts):
    """Signs the run tried to see the historical outcome or act as Nate: tool calls naming the live repo, omp's
    session store, Executor, the CLIs signed in to his accounts, his Chrome's debugging port, or the repo on GitHub
    (the sandbox refuses all but the last, which is public for some repos), or the rubric's leak markers in what the
    run produced."""
    github = Path(git(task["repo"], "remote", "get-url", "origin").strip().removesuffix(".git")).name
    live = re.compile(re.escape(task["repo"]) + "|~/" + re.escape(str(Path(task["repo"]).relative_to(HOME)))
                      + r"|\.omp/agent/sessions|history\.db|archive\.(search|sessions)|\"seance\"|nategriffin26/"
                      + re.escape(github) + r"\b|:4312\b|:9222\b|\.executor/|\b(xurl|gws|gcloud)\s")
    hits = [f"{name}: {m.group(0)}" for name, args in calls if (m := live.search(args))]
    hits += [f"marker: {marker}" for marker in task["rubric"].get("leak_markers", []) if any(marker in t for t in texts)]
    return sorted(set(hits))


def unwrap(brief):
    """A brief that arrives as one fenced block is sent as its contents."""
    m = re.fullmatch(r"(`{3,})[\w-]*\n(.*)\n\1", brief.strip(), re.S)
    return m.group(2) if m else brief


def briefer_file(name):
    return REPO / "extensions" / "brief.md" if name == "shipped" else DATA / "briefers" / f"{name}.md"


def briefer_prompt(name, request):
    """The briefer's first message; extensions/brief.ts builds the same one."""
    return f"{briefer_file(name).read_text().strip()}\n\nNate's request, verbatim:\n\n{fenced(request)}"


def diff_against(repo, commit):
    git(repo, "add", "-A", "-N")
    return git(repo, "diff", "--no-color", "--stat", commit) + "\n" + git(repo, "diff", "--no-color", commit)


def save(meta, record):
    tmp = meta / "run.json.tmp"
    tmp.write_text(json.dumps(record, indent=2))
    tmp.replace(meta / "run.json")


def run_one(task, arm, rep, kind):
    """kind 'run': [briefer ->] executor, then the judge view. kind 'brief': briefer only."""
    run_id = secrets.token_hex(4)
    meta = DATA / "meta" / run_id
    meta.mkdir(parents=True)
    record = {"id": run_id, "kind": kind, "task": task["id"], "arm": arm, "rep": rep, "status": "running",
              "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    save(meta, record)
    try:
        view, repo = prepare_view(task, run_id)
        texts = []
        calls = []
        prompt = task["request"]
        if arm.startswith("brief:"):
            name = arm.split(":", 1)[1]
            code, wall, since = omp(briefer_prompt(name, task["request"]), repo, meta / "sessions" / "briefer",
                                    AGENT_MODEL, BRIEFER_LIMITS, meta / "briefer.log", run_id, task)
            metrics, brief, bcalls = session_metrics(meta / "sessions" / "briefer", since)
            record["briefer"] = {"exit": code, "wall_s": wall, **metrics}
            if not brief:
                raise RuntimeError("the briefer ended without a brief")
            prompt = unwrap(brief)
            (meta / "brief.md").write_text(prompt)
            texts.append(prompt)
            calls += bcalls
            record["briefer"]["left_changes"] = bool(git(repo, "status", "--porcelain").strip())
        if kind == "run":
            code, wall, since = omp(prompt, repo, meta / "sessions" / "executor", AGENT_MODEL, EXECUTOR_LIMITS,
                                    meta / "executor.log", run_id, task)
            metrics, reply, ecalls = session_metrics(meta / "sessions" / "executor", since)
            record["executor"] = {"exit": code, "wall_s": wall, **metrics}
            (view / "reply.md").write_text(reply)
            diff = diff_against(repo, task["commit"])
            (view / "diff.patch").write_text(diff)
            shutil.copy(view / "reply.md", meta / "reply.md")
            shutil.copy(view / "diff.patch", meta / "diff.patch")
            texts += [reply, diff]
            calls += ecalls
        record["leaks"] = leaks(task, calls, texts)
        record["status"] = "done"
    except Exception as e:  # recorded on the run and reported; the batch goes on
        record["status"] = "failed"
        record["error"] = f"{type(e).__name__}: {e}"
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    save(meta, record)
    return record


def last_json(text):
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    if not blocks:
        raise RuntimeError("no ```json block in the verdict")
    return json.loads(blocks[-1])


def criteria_lines(rubric):
    return "\n".join(f"- {c['id']} [{c['kind']}] {c['text']}" for c in rubric["criteria"])


def score(rubric, verdict):
    passed = {c["id"]: bool(c["pass"]) for c in verdict["criteria"]}
    missing = [c["id"] for c in rubric["criteria"] if c["id"] not in passed]
    if missing:
        raise RuntimeError(f"the verdict skipped {missing}")
    positive = [c for c in rubric["criteria"] if c["kind"] != "must_not"]
    got = sum(WEIGHT[c["kind"]] for c in positive if passed[c["id"]])
    violations = sum(1 for c in rubric["criteria"] if c["kind"] == "must_not" and not passed[c["id"]])
    return max(0.0, round(100 * got / sum(WEIGHT[c["kind"]] for c in positive) - MUST_NOT_PENALTY * violations, 1)), violations


def judge_one(record):
    task = load_task(record["task"])
    meta = DATA / "meta" / record["id"]
    view = VIEWS / record["id"]
    if not (view / "reply.md").exists():
        raise RuntimeError(f"{record['id']}: judge view missing at {view}")
    prompt = JUDGE_TASK.format(repo_dir=Path(task["repo"]).name, request=fenced(task["request"]),
                               ideal=task["rubric"]["ideal_first_reply"], criteria=criteria_lines(task["rubric"]))
    sessions = meta / "sessions" / "judge"
    shutil.rmtree(sessions, ignore_errors=True)
    code, wall, since = omp(prompt, view, sessions, JUDGE_MODEL, JUDGE_LIMITS, meta / "judge.log", record["id"], task)
    metrics, text, _ = session_metrics(sessions, since)
    verdict = last_json(text)
    record["judge"] = {"exit": code, "wall_s": wall, "cost_usd": metrics["cost_usd"], **verdict}
    record["score"], record["must_not_violations"] = score(task["rubric"], verdict)
    record["satisfaction"] = verdict["satisfaction"]
    save(meta, record)
    return record


def brief_score(rubric, verdict):
    value = {"covered": 1, "silent": 0, "conflict": -1}
    v = {c["id"]: c["verdict"] for c in verdict["criteria"]}
    total = sum(WEIGHT[c["kind"]] for c in rubric["criteria"])
    got = sum(WEIGHT[c["kind"]] * value[v[c["id"]]] for c in rubric["criteria"])
    hurts = sum(1 for o in verdict.get("unasked_orders", []) if o.get("effect") == "hurts")
    return round(100 * got / total - 5 * hurts, 1), hurts


def judge_brief(record):
    task = load_task(record["task"])
    meta = DATA / "meta" / record["id"]
    prompt = BRIEF_JUDGE_TASK.format(request=fenced(task["request"]), ideal=task["rubric"]["ideal_first_reply"],
                                     criteria=criteria_lines(task["rubric"]), brief=(meta / "brief.md").read_text())
    sessions = meta / "sessions" / "brief-judge"
    shutil.rmtree(sessions, ignore_errors=True)
    code, wall, since = omp(prompt, VIEWS / record["id"], sessions, BRIEF_JUDGE_MODEL, JUDGE_LIMITS,
                            meta / "brief-judge.log", record["id"], task)
    metrics, text, _ = session_metrics(sessions, since)
    verdict = last_json(text)
    record["brief_judge"] = {"exit": code, "wall_s": wall, "cost_usd": metrics["cost_usd"], **verdict}
    record["brief_score"], record["brief_hurts"] = brief_score(task["rubric"], verdict)
    save(meta, record)
    return record


def records(tasks=None, arms=None):
    out = []
    for p in sorted((DATA / "meta").glob("*/run.json")):
        r = json.loads(p.read_text())
        if (not tasks or r["task"] in tasks) and (not arms or r["arm"] in arms):
            out.append(r)
    return out


def unjudged(record):
    """The verdicts a finished record still needs: its brief's, then its run's."""
    return record["status"] == "done" and (
        (record["arm"].startswith("brief:") and "brief_score" not in record)
        or (record["kind"] == "run" and "score" not in record))


def judge(record, lock):
    """Every missing verdict for one record, one after another (both write the same run.json)."""
    try:
        if record["arm"].startswith("brief:") and "brief_score" not in record:
            record = judge_brief(record)
        if record["kind"] == "run" and "score" not in record:
            record = judge_one(record)
        with lock:
            print(f"judged {record['task']} {record['arm']} #{record['rep']} ({record['id']}):"
                  + (f" score {record['score']}, satisfaction {record['satisfaction']}" if "score" in record else "")
                  + (f" brief {record['brief_score']}" if "brief_score" in record else ""), flush=True)
    except Exception as e:
        with lock:
            print(f"judge failed for {record['id']}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)


def execute(tasks, arms, reps, jobs, kind):
    """Runs every (task, arm, rep) with `jobs` Opus sessions at once, and judges each as soon as it finishes."""
    plan = [(load_task(t), a, r) for r in range(1, reps + 1) for t in tasks for a in arms]
    random.shuffle(plan)
    lock = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(jobs) as agents, concurrent.futures.ThreadPoolExecutor(jobs) as judges:
        pending = [agents.submit(run_one, t, a, r, kind) for t, a, r in plan]
        verdicts = []
        for fut in concurrent.futures.as_completed(pending):
            r = fut.result()
            with lock:
                spent = sum(r.get(s, {}).get("cost_usd", 0) for s in ("briefer", "executor"))
                print(f"{r['status']} {r['task']} {r['arm']} #{r['rep']} ({r['id']}) ${spent:.2f}"
                      + (f" {r['error']}" if r["status"] == "failed" else "")
                      + (f" leaks: {r['leaks']}" if r.get("leaks") else ""), flush=True)
            if unjudged(r):
                verdicts.append(judges.submit(judge, r, lock))
        concurrent.futures.wait(verdicts)


def med(values):
    values = [v for v in values if v is not None]
    if not values:
        return "-"
    m = statistics.median(values)
    return f"{m:.1f}" if len(values) == 1 else f"{m:.1f} ({min(values):.0f}-{max(values):.0f})"


def report(tasks, arms):
    rows = [r for r in records(tasks, arms) if r["status"] == "done" and not r.get("excluded")]
    runs = [r for r in rows if r["kind"] == "run"]
    briefs = [r for r in rows if r["kind"] == "brief" or "brief_score" in r]
    def cost(r):
        return sum(r.get(s, {}).get("cost_usd", 0) for s in ("briefer", "executor"))
    def tokens(r):
        return sum(r.get(s, {}).get("tokens", 0) for s in ("briefer", "executor")) / 1000
    def minutes(r):
        return sum(r.get(s, {}).get("wall_s", 0) for s in ("briefer", "executor")) / 60
    if runs:
        print("Runs: score 0-100 against the hindsight rubric; satisfaction 1-10; cost in USD at API prices (briefer +"
              " executor, subagents included); median (min-max)\n")
        print(f"| task | arm | n | score | satisfaction | cost $ | tokens k | minutes | subagents | stopped | leaks |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        keys = sorted({(r["task"], r["arm"]) for r in runs})
        for t, a in keys:
            g = [r for r in runs if (r["task"], r["arm"]) == (t, a)]
            print(f"| {t} | {a} | {len(g)} | {med([r.get('score') for r in g])} | {med([r.get('satisfaction') for r in g])}"
                  f" | {med([cost(r) for r in g])} | {med([tokens(r) for r in g])} | {med([minutes(r) for r in g])}"
                  f" | {med([r['executor']['subagents'] + r.get('briefer', {}).get('subagents', 0) for r in g])}"
                  f" | {sum(1 for r in g if r['executor']['exit'] != 0)} | {sum(1 for r in g if r.get('leaks'))} |")
        print("\nBy arm, the mean over tasks of each task's median:\n")
        print("| arm | tasks | score | satisfaction | cost $ | minutes |")
        print("|---|---|---|---|---|---|")
        for a in sorted({r["arm"] for r in runs}):
            per = {}
            for r in runs:
                if r["arm"] == a:
                    per.setdefault(r["task"], []).append(r)
            def mean_of(f):
                vals = [statistics.median(v) for g in per.values() if (v := [f(r) for r in g if f(r) is not None])]
                return f"{statistics.mean(vals):.1f}" if vals else "-"
            print(f"| {a} | {len(per)} | {mean_of(lambda r: r.get('score'))} | {mean_of(lambda r: r.get('satisfaction'))}"
                  f" | {mean_of(cost)} | {mean_of(minutes)} |")
    if briefs:
        print("\nBriefs: score -100..100 (rubric coverage minus conflicts, minus 5 per harmful unasked order)\n")
        print("| task | arm | n | brief score | harmful orders | briefer $ | briefer minutes | brief words |")
        print("|---|---|---|---|---|---|---|---|")
        for t, a in sorted({(r["task"], r["arm"]) for r in briefs}):
            g = [r for r in briefs if (r["task"], r["arm"]) == (t, a)]
            words = [len((DATA / "meta" / r["id"] / "brief.md").read_text().split()) for r in g]
            print(f"| {t} | {a} | {len(g)} | {med([r.get('brief_score') for r in g])} | {med([r.get('brief_hurts') for r in g])}"
                  f" | {med([r['briefer']['cost_usd'] for r in g])} | {med([r['briefer']['wall_s'] / 60 for r in g])}"
                  f" | {med(words)} |")
    for r in records(tasks, arms):
        if r["status"] != "done":
            print(f"\n{r['status']}: {r['task']} {r['arm']} #{r['rep']} ({r['id']}) {r.get('error', '')}")
        elif r.get("excluded"):
            print(f"\nexcluded: {r['task']} {r['arm']} #{r['rep']} ({r['id']}) {r['excluded']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "briefs", "judge", "report", "exclude"])
    ap.add_argument("run", nargs="?", help="exclude: the run id")
    ap.add_argument("--reason", help="exclude: why the run does not count (kept on the record)")
    ap.add_argument("--task", default="", help="comma-separated task ids (default: every task with a rubric)")
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=3, help="Opus sessions at once")
    a = ap.parse_args()
    tasks = [t for t in a.task.split(",") if t] or sorted(p.parent.name for p in (DATA / "tasks").glob("*/rubric.json"))
    if a.command in ("run", "briefs"):
        if not a.arm:
            ap.error("--arm is required")
        if a.command == "briefs" and any(not arm.startswith("brief:") for arm in a.arm):
            ap.error("briefs takes brief:NAME arms only")
        for arm in a.arm:
            if arm != "direct" and not (arm.startswith("brief:") and briefer_file(arm[6:]).exists()):
                ap.error(f"unknown arm {arm}")
        execute(tasks, a.arm, a.reps, a.jobs, "run" if a.command == "run" else "brief")
    elif a.command == "judge":
        lock = threading.Lock()
        with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
            for r in records(tasks):
                if unjudged(r):
                    pool.submit(judge, r, lock)
    elif a.command == "exclude":
        if not (a.run and a.reason):
            ap.error("exclude takes a run id and --reason")
        meta = DATA / "meta" / a.run
        record = json.loads((meta / "run.json").read_text())
        record["excluded"] = a.reason
        save(meta, record)
    else:
        report(tasks, a.arm)


if __name__ == "__main__":
    main()
