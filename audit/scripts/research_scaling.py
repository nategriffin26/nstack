#!/usr/bin/env python3
"""Does adding research lanes buy better answers?

Joins every research run on disk (lane dossiers, verifier verdicts, SYNTHESIS.md/.json) with
the omp session logs (each lane's model and cost, verifier cost, the orchestrator's cost from
the first lane spawn to the synthesis write, Nate's first reply after it) and the tf.py ledger
(pages each lane fetched). Writes local/analysis/RESEARCH-SCALING.json and prints the tables
behind the audit report (local/audit/REPORT.md, private).
"""
import glob, json, os, random, re, sqlite3, subprocess
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

HOME = os.path.expanduser("~")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "local", "analysis", "RESEARCH-SCALING.json")
RUN_GLOBS = ["Projects/*/local/research/*/", "Projects/*/*/local/research/*/",
             ".omp/agent/sessions/*/*/local/research/*/", ".omp/local/research/*/", "local/research/*/"]
URL = re.compile(r"https?://[^\s\"'<>)\]\\`|]+")
SPAWN_PATH = re.compile(r"((?:/Users/|~/)[^\s\"'`]*?/)?local/research/([A-Za-z0-9._\-]+)/(verify/)?([A-Za-z0-9._\-]+)\.json")
KEEP_QUERY = ("youtube.com", "news.ycombinator.com")
LEDGER = os.path.join(HOME, ".omp", "local", "tinyfish-rate.db")


def norm(url):
    url = url.strip().rstrip(".,;:)]}'\"*`").split("#")[0]
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", url)
    if m:
        return "arxiv:" + m.group(1)
    url = re.sub(r"^https?://(www\.)?", "", url, flags=re.I)
    host, _, rest = url.partition("/")
    host = host.lower()
    if not host.endswith(KEEP_QUERY):
        rest = rest.split("?")[0]
    return (host + "/" + rest).rstrip("/")


def epoch(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() if ts else 0.0


def load_runs():
    runs = {}
    for pat in RUN_GLOBS:
        for d in glob.glob(os.path.join(HOME, pat)):
            d = os.path.realpath(d.rstrip("/"))
            if "node_modules" in d or d in runs:
                continue
            lanes, mtimes = {}, []
            for f in glob.glob(d + "/*.json"):
                if f.endswith("SYNTHESIS.json"):
                    continue
                try:
                    doc = json.load(open(f))
                except Exception:
                    continue
                claims = doc.get("claims") if isinstance(doc, dict) else None
                if not isinstance(claims, list) or (claims and isinstance(claims[0], dict) and "sources" not in claims[0]):
                    continue  # verifier outputs saved beside dossiers have verdicts, not sources
                urls = {norm(u) for c in claims if isinstance(c, dict) for u in URL.findall(json.dumps(c.get("sources") or []))}
                lanes[os.path.basename(f)[:-5]] = {"claims": len(claims), "urls": urls,
                                                   "confidence": Counter(str(c.get("confidence", "?")).split()[0].lower()
                                                                         for c in claims if isinstance(c, dict))}
                mtimes.append(os.path.getmtime(f))
            if not lanes:
                continue
            synth, adopted = "", set()
            for name in ("SYNTHESIS.md", "SYNTHESIS.json"):
                if os.path.exists(os.path.join(d, name)):
                    synth += open(os.path.join(d, name), errors="replace").read()
            try:
                adopted = {norm(u) for u in URL.findall(json.dumps(json.load(open(os.path.join(d, "SYNTHESIS.json"))).get("adopted") or []))}
            except Exception:
                pass
            verdicts = []
            for f in glob.glob(d + "/verify/*.json"):
                try:
                    doc = json.load(open(f))
                except Exception:
                    continue
                for v in (doc.get("verdicts") if isinstance(doc, dict) else doc) or []:
                    if isinstance(v, dict) and v.get("verdict"):
                        verdicts.append({"verdict": str(v["verdict"]).upper().split()[0],
                                         "text": json.dumps(v.get("claim") or v.get("datum") or v.get("id") or "")})
            runs[d] = {"slug": os.path.basename(d), "lanes": lanes, "mtime": (min(mtimes), max(mtimes)),
                       "synth_urls": {norm(u) for u in URL.findall(synth)} if synth else None,
                       "adopted_urls": adopted, "verdicts": verdicts}
    return runs


def subagent_stats(path):
    cost, calls, model, first, last = 0.0, 0, None, None, None
    try:
        fh = open(path, errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            if '"assistant"' not in line[:400]:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            m = d.get("message") or {}
            if d.get("type") != "message" or m.get("role") != "assistant":
                continue
            calls += 1
            cost += ((m.get("usage") or {}).get("cost") or {}).get("total") or 0
            model = model or m.get("model")
            first = first or d.get("timestamp")
            last = d.get("timestamp")
    return {"cost": cost, "calls": calls, "model": model, "start": epoch(first), "end": epoch(last)}


def scan(path):
    """Research spawns, synthesis writes, Nate's messages and call costs of one orchestrator file."""
    spawns, synth_writes, users, calls, cwd = [], [], [], [], None
    with open(path, errors="replace") as fh:
        for line in fh:
            head = line[:400]
            if cwd is None and '"type":"session"' in head:
                cwd = json.loads(line).get("cwd") or ""
                continue
            if '"role":"user"' in head:
                d = json.loads(line)
                content = (d.get("message") or {}).get("content")
                text = content if isinstance(content, str) else " ".join(
                    b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")
                if text.strip() and not text.lstrip().startswith("<"):
                    users.append((epoch(d.get("timestamp")), text.strip()))
                continue
            if '"assistant"' not in head:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            m = d.get("message") or {}
            if d.get("type") != "message" or m.get("role") != "assistant":
                continue
            ts = epoch(d.get("timestamp"))
            calls.append((ts, ((m.get("usage") or {}).get("cost") or {}).get("total") or 0,
                          str(m.get("responseId") or (d.get("id"), d.get("timestamp")))))
            for b in m.get("content") or []:
                if b.get("type") != "toolCall":
                    continue
                args = b.get("arguments") or {}
                if b.get("name") == "task":
                    for t in args.get("tasks") or []:
                        hit = SPAWN_PATH.search(json.dumps(t))
                        if hit:
                            spawns.append({"ts": ts, "call": b.get("id"), "name": t.get("name"), "agent": t.get("agent") or "task",
                                           "prefix": hit.group(1) or "", "slug": hit.group(2), "verify": bool(hit.group(3)),
                                           "lane": hit.group(4)})
                elif "SYNTHESIS.md" in json.dumps(args):
                    hit = re.search(r"local/research/([A-Za-z0-9._\-]+)/SYNTHESIS\.md", json.dumps(args))
                    if hit and b.get("name") in ("write", "edit"):
                        synth_writes.append((ts, hit.group(1)))
    if not spawns:
        return None
    return {"path": path, "cwd": cwd or "", "spawns": spawns, "synth_writes": synth_writes, "users": users, "calls": calls}


def resolve(spawn, orch, runs_by_slug):
    cands = runs_by_slug.get(spawn["slug"], [])
    if len(cands) <= 1:
        return cands[0] if cands else None
    tries = [spawn["prefix"].replace("~/", HOME + "/"), orch["path"][:-6] + "/", orch["cwd"] + "/"]
    for prefix in tries:
        p = os.path.realpath(prefix + "local/research/" + spawn["slug"]) if prefix.startswith("/") else None
        if p in cands:
            return p
    return None


def rarefaction(lane_sets, target, k, trials=300):
    rng = random.Random(7)
    names = list(lane_sets)
    total = 0.0
    for _ in range(trials):
        covered = set().union(*(lane_sets[n] for n in rng.sample(names, k)))
        total += len(covered & target) / len(target)
    return total / trials


def main():
    runs = load_runs()
    runs_by_slug = defaultdict(list)
    for d, r in runs.items():
        runs_by_slug[r["slug"]].append(d)

    context_workers = [p for p in (f"{HOME}/.context-cutover/frozen/workers",
                                   f"{os.environ.get('CONTEXT_HOME') or HOME + '/.context-next'}/workers/sessions")
                       if os.path.isdir(p)]
    grep = subprocess.run(["/usr/bin/grep", "-rl", "--null", "--include=*.jsonl", "local/research/",
                           f"{HOME}/.omp/agent/sessions", *context_workers], capture_output=True, text=True)
    files = sorted(f for f in grep.stdout.split("\0") if f)
    with ProcessPoolExecutor(max_workers=10) as ex:
        orchs = [o for o in ex.map(scan, files, chunksize=4) if o]
    orchs.sort(key=lambda o: o["calls"][0][0] if o["calls"] else 0)

    # attach spawns to runs; forks repeat a spawn, so the earliest orchestrator file owns it
    seen_spawn, seen_call = set(), set()
    per_run = defaultdict(lambda: {"spawns": [], "orchs": {}, "synth_ts": None})
    for o in orchs:
        for s in o["spawns"]:
            d = resolve(s, o, runs_by_slug)
            key = (d, s["lane"], s["verify"])
            if d is None or key in seen_spawn:
                continue
            seen_spawn.add(key)
            s["file"] = o["path"][:-6] + "/" + (s["name"] or "") + ".jsonl"
            per_run[d]["spawns"].append(s)
            per_run[d]["orchs"][o["path"]] = o
        for ts, slug in o["synth_writes"]:
            for d in runs_by_slug.get(slug, []):
                if o["path"] in per_run[d]["orchs"] and per_run[d]["synth_ts"] is None:
                    per_run[d]["synth_ts"] = ts

    ledger = sqlite3.connect(LEDGER) if os.path.exists(LEDGER) else None
    out_runs = []
    for d, r in runs.items():
        info = per_run.get(d, {"spawns": [], "orchs": {}, "synth_ts": None})
        lanes = r["lanes"]
        lane_spawns = {s["lane"]: s for s in info["spawns"] if not s["verify"]}
        verify_spawns = [s for s in info["spawns"] if s["verify"]]
        waves = sorted({s["call"] for s in lane_spawns.values()}, key=lambda c: min(s["ts"] for s in lane_spawns.values() if s["call"] == c))
        wave_of = {s["lane"]: waves.index(s["call"]) + 1 for s in lane_spawns.values()}
        stats = {}
        for lane, s in lane_spawns.items():
            st = subagent_stats(s["file"]) if s.get("name") else None
            if st:
                stats[lane] = dict(st, agent=s["agent"])
        vstats = [subagent_stats(s["file"]) for s in verify_spawns if s.get("name")]
        start = min((s["ts"] for s in info["spawns"]), default=r["mtime"][0] - 4 * 3600)
        end = info["synth_ts"] or r["mtime"][1]

        fetched = {}
        if ledger:
            for lane in lanes:
                rows = ledger.execute("select url from pages where lane=? and ts between ? and ? and status='ok'",
                                      (lane, start - 120, end + 120)).fetchall()
                fetched[lane] = {norm(u) for (u,) in rows}

        cited_count = Counter(u for l in lanes.values() for u in l["urls"])
        all_cited = set(cited_count)
        synth = r["synth_urls"] & all_cited if r["synth_urls"] else None
        row = {"run": d.replace(HOME, "~"), "lanes": len(lanes), "waves": len(waves) or None,
               "claims": sum(l["claims"] for l in lanes.values()), "cited_urls": len(all_cited),
               "cited_shared": round(sum(1 for c in cited_count.values() if c > 1) / len(all_cited), 3) if all_cited else None,
               "fetched_urls": len(set().union(*fetched.values())) if fetched else None,
               "lane_models": dict(Counter((stats[l]["model"] or "?") for l in stats)),
               "lane_cost": round(sum(s["cost"] for s in stats.values()), 2),
               "verify_cost": round(sum(v["cost"] for v in vstats if v), 2),
               "verdicts": dict(Counter(v["verdict"] for v in r["verdicts"])),
               "synth_ts": info["synth_ts"]}
        if synth:
            contributing = [l for l in lanes if lanes[l]["urls"] & synth]
            row.update({"synth_urls": len(synth),
                        "lanes_contributing": round(len(contributing) / len(lanes), 3),
                        "synth_single_lane": round(sum(1 for u in synth if cited_count[u] == 1) / len(synth), 3)})
            if len(waves) > 1:
                late = set().union(*(lanes[l]["urls"] for l in lanes if wave_of.get(l, 1) > 1))
                early = set().union(*(lanes[l]["urls"] for l in lanes if wave_of.get(l, 1) == 1))
                row["synth_only_from_later_waves"] = round(len((synth & late) - early) / len(synth), 3)
                adopted_late = (r["adopted_urls"] & late) - early
                if r["adopted_urls"] & all_cited:
                    row["adopted_only_from_later_waves"] = round(len(adopted_late) / len(r["adopted_urls"] & all_cited), 3)
            if len(lanes) >= 6:
                sets = {l: lanes[l]["urls"] for l in lanes}
                row["coverage_at"] = {f: round(rarefaction(sets, synth, max(1, round(len(lanes) * f))), 3) for f in (0.25, 0.5, 0.75)}
        adopted = r["adopted_urls"] & all_cited
        if adopted:
            row.update({"adopted_urls": len(adopted),
                        "lanes_with_adopted": round(sum(1 for l in lanes if lanes[l]["urls"] & adopted) / len(lanes), 3),
                        "adopted_single_lane": round(sum(1 for u in adopted if cited_count[u] == 1) / len(adopted), 3)})
        # orchestrator cost from the first spawn to the synthesis write (upper bound: includes other work in that window)
        if info["synth_ts"] and info["orchs"]:
            cost = 0.0
            for o in info["orchs"].values():
                for ts, c, rid in o["calls"]:
                    if start <= ts <= info["synth_ts"] and rid not in seen_call:
                        seen_call.add(rid)
                        cost += c
            row["orchestrator_cost"] = round(cost, 2)
            row["minutes_to_synthesis"] = round((info["synth_ts"] - start) / 60, 1)
            root = min(info["orchs"].values(), key=lambda o: o["calls"][0][0] if o["calls"] else 0)
            later = [t for ts, t in root["users"] if ts > info["synth_ts"]]
            row["nate_next"] = later[0][:400] if later else None
            row["root"] = root["path"].replace(HOME, "~")
        row["_lane_detail"] = {l: {"model": stats.get(l, {}).get("model"), "agent": stats.get(l, {}).get("agent"),
                                   "cost": round(stats.get(l, {}).get("cost", 0), 3), "wave": wave_of.get(l),
                                   "claims": lanes[l]["claims"], "cited": len(lanes[l]["urls"]),
                                   "in_synth": len(lanes[l]["urls"] & synth) if synth else None,
                                   "fetched": len(fetched.get(l, ())),
                                   "verdicts": dict(Counter(v["verdict"] for v in r["verdicts"]
                                                            if re.search(r"\b" + re.escape(l) + r"\b", v["text"])))}
                               for l in lanes}
        out_runs.append(row)

    out_runs.sort(key=lambda x: -x["lanes"])
    summary = summarize(out_runs)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"summary": summary, "runs": out_runs}, open(OUT, "w"), indent=1)
    print(json.dumps(summary, indent=1))
    print(f"{len(out_runs)} runs, {sum(r['lanes'] for r in out_runs)} lanes -> {OUT}")


def summarize(runs):
    median = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
    family = lambda m: next((k for k in ("muse", "gemini-3.8", "gemini-3.7", "sonnet", "opus", "glm", "sol", "astra", "fable")
                             if k in (m or "")), m or "unmapped")
    synth = [r for r in runs if r.get("synth_urls")]
    cov = [r["coverage_at"] for r in runs if r.get("coverage_at")]
    adopted = [r for r in runs if r.get("adopted_urls")]
    orch = [r for r in runs if "orchestrator_cost" in r]
    per_lane, verdicts = defaultdict(list), defaultdict(Counter)
    for r in runs:
        for lane in r["_lane_detail"].values():
            f = family(lane["model"]) if lane["model"] else "unmapped"
            if lane["model"]:
                per_lane[f].append(lane["cost"])
            verdicts[f].update(lane["verdicts"])
    n, xs, ys = len(orch), [r["lanes"] for r in orch], [r["orchestrator_cost"] for r in orch]
    mx, my = sum(xs) / n, sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return {
        "runs": len(runs), "lanes": sum(r["lanes"] for r in runs),
        "median_share_of_cited_sources_found_by_2plus_lanes": median([r["cited_shared"] for r in runs if r["cited_shared"] is not None]),
        "synthesis_runs": len(synth),
        "median_share_of_lanes_cited_in_synthesis": median([r["lanes_contributing"] for r in synth]),
        "median_share_of_synthesis_sources_found_by_one_lane": median([r["synth_single_lane"] for r in synth]),
        "synthesis_sources_covered_by_fraction_of_lanes": {str(f): median([c[f] for c in cov]) for f in (0.25, 0.5, 0.75)} if cov else None,
        "coverage_runs": len(cov),
        "adopted_runs": len(adopted),
        "median_share_of_lanes_behind_an_adopted_finding": median([r["lanes_with_adopted"] for r in adopted]),
        "median_share_of_adopted_sources_found_by_one_lane": median([r["adopted_single_lane"] for r in adopted]),
        "later_waves": {r["run"].split("/")[-1]: [r["synth_only_from_later_waves"], r.get("adopted_only_from_later_waves")]
                        for r in runs if "synth_only_from_later_waves" in r},
        "lane_cost_by_model": {f: {"lanes": len(c), "median": round(median(c), 3), "total": round(sum(c), 2)} for f, c in per_lane.items()},
        "verdicts_by_lane_model": {f: dict(c) for f, c in verdicts.items() if c},
        "verdicts_all": dict(sum((Counter(r["verdicts"]) for r in runs), Counter())),
        "orchestrator_runs": n, "orchestrator_median": median(ys),
        "orchestrator_fixed_plus_per_lane": [round(my - slope * mx, 2), round(slope, 2)],
        "orchestrator_vs_lanes_vs_verifiers_total": [round(sum(ys), 2), round(sum(r["lane_cost"] for r in orch), 2),
                                                     round(sum(r["verify_cost"] for r in orch), 2)],
        "minutes_to_synthesis_median": median([r["minutes_to_synthesis"] for r in orch]),
        "lane_and_verifier_cost_all_runs": [round(sum(r["lane_cost"] for r in runs), 2), round(sum(r["verify_cost"] for r in runs), 2)],
    }


if __name__ == "__main__":
    main()
