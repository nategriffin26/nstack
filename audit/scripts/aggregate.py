#!/usr/bin/env python3
"""Aggregate the per-session analyses (local/analysis/*.jsonl) with the extracted stats
(local/digests/sessions.jsonl). Prints the tables cited in audit/REPORT.md and writes
local/analysis/AGGREGATE.json. The current audit session (-Projects-nstack) is excluded.
"""
import glob, json, os, re, statistics as st
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "local")
A = os.path.join(ROOT, "analysis")


def load(pattern):
    out = []
    for f in sorted(glob.glob(os.path.join(A, pattern))):
        for i, line in enumerate(open(f)):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception as e:
                print(f"PARSE FAIL {os.path.basename(f)}:{i + 1}: {e}")
                continue
            d["_batch"] = os.path.basename(f).split(".")[0]
            out.append(d)
    return out


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return (round(st.mean(xs), 2), len(xs)) if xs else (None, 0)


def bucket_cost(c):
    for lim, lab in [(5, "<$5"), (20, "$5-20"), (50, "$20-50"), (100, "$50-100"), (250, "$100-250"), (10**9, ">=$250")]:
        if c < lim:
            return lab


def bucket_subs(n):
    return "0" if n == 0 else "1-4" if n <= 4 else "5-19" if n <= 19 else "20+"


def table(title, rows, cols):
    print(f"\n## {title}")
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")


def main():
    stats = {}
    for line in open(os.path.join(ROOT, "digests", "sessions.jsonl")):
        r = json.loads(line)
        stats[r["key"]] = r
    sess = [d for d in load("[SW]*.jsonl") if "-Projects-nstack" not in d.get("key", "")]
    seen = Counter(d.get("key") for d in sess)
    dup = [k for k, v in seen.items() if v > 1]
    missing = []
    manifest = json.load(open(os.path.join(ROOT, "batches", "manifest.json")))
    for b, keys in manifest.items():
        if b[0] in "SW":
            missing += [k for k in keys if k not in seen and "-Projects-nstack" not in k]
    print(f"session analyses: {len(sess)}; duplicates {len(dup)}; missing {len(missing)}")
    agg = {"n": len(sess), "missing": missing}

    for d in sess:
        s = stats.get(d.get("key"), {})
        d["_cost"] = s.get("total_cost_dedup", (d.get("token_plateau") or {}).get("spend_usd") or 0)
        d["_subs"] = s.get("n_subagents", (d.get("delegation") or {}).get("n_subagents") or 0)
        d["_score"] = (d.get("outcome") or {}).get("score_1_10")
        d["_turns"] = s.get("user_turns")
        d["_fe_turn"] = (s.get("first_edit") or {}).get("turn")

    total_cost = sum(d["_cost"] for d in sess)
    scored = [d for d in sess if isinstance(d["_score"], (int, float))]
    agg["score_mean"], agg["n_scored"] = mean([d["_score"] for d in scored])
    agg["score_median"] = st.median([d["_score"] for d in scored]) if scored else None
    print(f"total cost covered ${total_cost:,.0f}; scored {len(scored)}; mean score {agg['score_mean']}; median {agg['score_median']}")
    build_kinds = {"new-build", "rewrite", "feature", "ui-visual", "bugfix"}
    b = [d for d in scored if d.get("kind") in build_kinds]
    print(f"build-type sessions scored: {len(b)}, mean {mean([d['_score'] for d in b])}, median {st.median([d['_score'] for d in b]) if b else None}")

    def by(keyf, label, subset=scored, order=None):
        g = defaultdict(list)
        for d in subset:
            g[keyf(d)].append(d)
        keys = order or sorted(g, key=lambda k: str(k))
        rows = []
        for k in keys:
            if k not in g:
                continue
            ds = g[k]
            m, n = mean([x["_score"] for x in ds])
            gaps = sum(len(x.get("gaps") or []) for x in ds)
            rows.append([k, n, m, f"${sum(x['_cost'] for x in ds):,.0f}", round(gaps / max(len(ds), 1), 2)])
        table(label, rows, [label, "n", "mean score", "cost", "gaps/session"])
        return rows

    agg["by_kind"] = by(lambda d: d.get("kind"), "kind")
    agg["by_scale"] = by(lambda d: d.get("ask_scale"), "ask_scale", order=["small", "medium", "large", "huge"])
    agg["by_clarity"] = by(lambda d: d.get("ask_clarity"), "ask_clarity", order=["clear", "partly-ambiguous", "ambiguous"])
    agg["by_cost"] = by(lambda d: bucket_cost(d["_cost"]), "spend", order=["<$5", "$5-20", "$20-50", "$50-100", "$100-250", ">=$250"])
    agg["by_cost_build"] = by(lambda d: bucket_cost(d["_cost"]), "spend (build kinds)", subset=b, order=["<$5", "$5-20", "$20-50", "$50-100", "$100-250", ">=$250"])
    agg["by_subs"] = by(lambda d: bucket_subs(d["_subs"]), "subagents", order=["0", "1-4", "5-19", "20+"])
    agg["by_subs_build"] = by(lambda d: bucket_subs(d["_subs"]), "subagents (build kinds)", subset=b, order=["0", "1-4", "5-19", "20+"])
    pre = lambda d: d.get("pre_impl") or {}
    agg["by_confirm"] = by(lambda d: pre(d).get("user_confirmed_before_build"), "confirmed before build (build kinds)", subset=b)
    agg["by_restated"] = by(lambda d: pre(d).get("restated_intent"), "restated intent (build kinds)", subset=b)
    agg["by_qquality"] = by(lambda d: pre(d).get("question_quality"), "question quality (build kinds)", subset=b)
    agg["by_artifact"] = by(lambda d: pre(d).get("design_artifact"), "design artifact (build kinds)", subset=b)
    agg["by_research"] = by(lambda d: "0" if not pre(d).get("research_lanes_before_build") else "1-3" if pre(d)["research_lanes_before_build"] <= 3 else "4+", "research lanes before build (build kinds)", subset=b, order=["0", "1-3", "4+"])
    agg["by_plateau"] = by(lambda d: (d.get("token_plateau") or {}).get("judgement"), "plateau judgement", order=["under", "proportionate", "somewhat-over", "far-over"])
    agg["by_brief"] = by(lambda d: (d.get("delegation") or {}).get("briefs_carried_intent"), "briefs carried intent (with subagents)", subset=[d for d in scored if d["_subs"] > 0])

    # plateau spend shares
    pj = Counter(); pc = Counter()
    for d in sess:
        j = (d.get("token_plateau") or {}).get("judgement")
        pj[j] += 1; pc[j] += d["_cost"]
    table("plateau judgement (all analysed)", [[k, pj[k], f"${pc[k]:,.0f}", f"{100 * pc[k] / total_cost:.0f}%"] for k in pj], ["judgement", "sessions", "cost", "share"])
    agg["plateau_spend"] = {str(k): pc[k] for k in pc}

    # control for task size: within large/huge asks, does spend or fan-out buy outcome?
    big = [d for d in scored if d.get("ask_scale") in ("large", "huge")]
    agg["big_by_cost"] = by(lambda d: bucket_cost(d["_cost"]), "spend (large+huge asks)", subset=big, order=["<$5", "$5-20", "$20-50", "$50-100", "$100-250", ">=$250"])
    agg["big_by_subs"] = by(lambda d: bucket_subs(d["_subs"]), "subagents (large+huge asks)", subset=big, order=["0", "1-4", "5-19", "20+"])
    agg["big_by_confirm"] = by(lambda d: pre(d).get("user_confirmed_before_build"), "confirmed before build (large+huge asks)", subset=big)
    agg["big_by_clarity"] = by(lambda d: d.get("ask_clarity"), "ask clarity (large+huge asks)", subset=big, order=["clear", "partly-ambiguous", "ambiguous"])
    agg["big_by_artifact"] = by(lambda d: pre(d).get("design_artifact"), "design artifact (large+huge asks)", subset=big)
    agg["big_by_fe_turn"] = by(lambda d: "none" if d["_fe_turn"] is None else "turn 1" if d["_fe_turn"] == 1 else "turn 2+", "first root edit (large+huge asks)", subset=big, order=["turn 1", "turn 2+", "none"])

    # gaps
    gaps = [g for d in sess for g in (d.get("gaps") or [])]
    gt = Counter(g.get("type") for g in gaps); gr = Counter(g.get("root_cause") for g in gaps)
    prev = sum(1 for g in gaps if g.get("preventable_at_design"))
    print(f"\ngaps: {len(gaps)} in {sum(1 for d in sess if d.get('gaps'))} sessions; preventable at design {prev} ({100 * prev / max(len(gaps), 1):.0f}%)")
    table("gap types", [[k, v] for k, v in gt.most_common()], ["type", "n"])
    table("gap root causes", [[k, v, sum(1 for g in gaps if g.get('root_cause') == k and g.get('preventable_at_design'))] for k, v in gr.most_common()], ["root cause", "n", "preventable"])
    agg["gap_types"] = dict(gt); agg["gap_roots"] = dict(gr); agg["gaps_total"] = len(gaps); agg["gaps_preventable"] = prev

    # process porn
    pp = [(p, d) for d in sess for p in (d.get("process_porn") or [])]
    cats = Counter(); catcost = Counter()
    rules = [("review/audit/verify rounds", r"review|audit|verif|critic|judge|interrogat|second opinion|cross-family"),
             ("research waves", r"research|lane|dossier|counter.?thesis"),
             ("docs/plans/status/reports", r"doc|plan|status|report|essay|readme|summary|md\b|markdown|spec|matrix|synthesis"),
             ("todo churn", r"todo"),
             ("labs/prototypes not used", r"lab|prototype|mock"),
             ("parallel lanes/fan-out", r"lane|parallel|fan|subagent|swarm|arena"),
             ("polling/waiting", r"poll|wait|sleep|check-in")]
    for p, d in pp:
        w = (p.get("what") or "") + " " + (p.get("evidence") or "")
        cat = next((n for n, rx in rules if re.search(rx, w, re.I)), "other")
        cats[cat] += 1
        c = p.get("est_cost_usd")
        catcost[cat] += c if isinstance(c, (int, float)) else 0
    table("process porn (muse-estimated)", [[k, cats[k], f"${catcost[k]:,.0f}"] for k in cats], ["category", "items", "est cost"])
    agg["porn"] = {k: [cats[k], catcost[k]] for k in cats}

    # pre-impl stats over build kinds
    bb = [d for d in sess if d.get("kind") in build_kinds]
    def rate(f):
        xs = [f(d) for d in bb]
        xs = [x for x in xs if x is not None]
        return f"{sum(1 for x in xs if x)}/{len(xs)}"
    print("\nbuild-kind sessions:", len(bb))
    print("restated intent:", rate(lambda d: pre(d).get("restated_intent")))
    print("asked >=1 question:", rate(lambda d: (pre(d).get("questions_asked") or 0) > 0))
    print("confirmed before build:", rate(lambda d: pre(d).get("user_confirmed_before_build")))
    print("grounded in code:", rate(lambda d: pre(d).get("grounded_in_code")))
    print("design artifact:", Counter(pre(d).get("design_artifact") for d in bb))
    print("missing_from_ask top:", Counter(m.lower().strip()[:60] for d in bb for m in (d.get("missing_from_ask") or [])).most_common(25))
    json.dump(agg, open(os.path.join(A, "AGGREGATE.json"), "w"), indent=1, default=str)

    # quotes and interventions dump for reading
    with open(os.path.join(A, "QUOTES.md"), "w") as fh:
        fh.write("# Nate's process quotes (deduped)\n\n")
        seenq = set()
        for d in sorted(sess, key=lambda d: stats.get(d.get("key"), {}).get("start") or ""):
            for q in d.get("nate_process_quotes") or []:
                k = q.strip().lower()[:80]
                if k in seenq:
                    continue
                seenq.add(k)
                fh.write(f"- {q.strip()} — `{d.get('key', '')[:70]}`\n")
    with open(os.path.join(A, "INTERVENTIONS.md"), "w") as fh:
        fh.write("# Best interventions, by session cost\n\n")
        for d in sorted(sess, key=lambda d: -d["_cost"]):
            if d.get("best_intervention"):
                fh.write(f"- ${d['_cost']:,.0f} score={d['_score']} {d.get('kind')} — {d['best_intervention'].strip()} — `{d.get('key', '')[:70]}`\n")


if __name__ == "__main__":
    main()
