#!/usr/bin/env python3
"""Judge a work against exemplars with model judges from different companies, each in a fresh blind context.

  judge.py pairwise --work W --exemplar name=path [...] --context C --out OUT.json
      W against each exemplar in both orders; a verdict (work | exemplar | tie) counts only when both orders agree,
      otherwise it is `split`. Per-dimension verdicts and the gaps each judge names come with it.
  judge.py checks --work W --checks CHECKS.md --context C --out OUT.json
      One true/false per `- ` line of CHECKS.md, with a note on every failure.
  judge.py score --work W [--exemplar name=path ...] --context C --out OUT.json
      1-10 per dimension; with exemplars, every screen is scored, shuffled and unnamed. Diagnostic only: never the
      objective (scores drift run to run and move with whatever is shown beside them).

--context is a sentence or a file: what the work is and what a judge should weigh. Never put a target score, a round
number, history or which item is ours in it. Inputs are any files `omp -p` attaches with @ (images, text, PDF).
Judges are agent names from the roster (`--roster`, default the repository's roster.toml), each run with that agent's
model through `omp -p` on Nate's subscriptions with no tools, skills, rules or context files, and each sees its files
under neutral names. A judge whose call fails or whose reply is not JSON is reported as `error`, and the script exits 1.
"""
import argparse, concurrent.futures as cf, json, pathlib, random, re, shutil, subprocess, tempfile, tomllib

DEFAULT_ROSTER = pathlib.Path(__file__).resolve().parents[3] / "roster.toml"

DEFAULT_DIMENSIONS = "hierarchy,typography,color_contrast,spacing_rhythm,consistency,calm_restraint,overall"


def run(model: str, files: list[str], prompt: str) -> dict:
    # A judge must not learn from a file name which item is the work.
    neutral = pathlib.Path(tempfile.mkdtemp())
    try:
        attached = []
        for n, f in enumerate(files, 1):
            copy = neutral / f"item-{n}{pathlib.Path(f).suffix}"
            shutil.copyfile(f, copy)
            attached.append(f"@{copy}")
        cmd = ["omp", "-p", "--model", model, "--no-session", "--no-skills", "--no-rules", "--no-context-files",
               "--no-tools", "--no-extensions", "--no-title", "--thinking", "medium", *attached, prompt]
        out, failure = "", "unparsed"
        for _ in range(2):
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            out = p.stdout
            if p.returncode != 0:
                failure = f"exit {p.returncode}: {p.stderr[-300:]}"
                continue
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            failure = "unparsed"
        return {"error": failure, "raw": out[-2000:]}
    finally:
        shutil.rmtree(neutral, ignore_errors=True)


def parallel(a, jobs: dict) -> dict:
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(run, a.models[judge], files, prompt): key for key, (judge, files, prompt) in jobs.items()}
        return {futures[f]: f.result() for f in cf.as_completed(futures)}


def side(winner, work_slot: str) -> str:
    if winner == "tie":
        return "tie"
    if winner in ("1", "2"):
        return "work" if winner == work_slot else "exemplar"
    return "error"


def pairwise(a) -> dict:
    prompt = (f"{a.context}\n\nThe two attached files are item 1 then item 2. Compare them. Reply with JSON only: "
              '{"winner": "1"|"2"|"tie", "dimensions": {' + ", ".join(f'"{d}": "1"|"2"|"tie"' for d in a.dims)
              + '}, "reason": "<one sentence>", "gaps": [<up to 5 concrete things the weaker item does worse than the '
              'stronger, each naming the element and the fix>]}')
    jobs = {}
    for j in a.judges:
        for name, ex in a.exemplars.items():
            jobs[(j, name, "first")] = (j, [a.work, ex], prompt)
            jobs[(j, name, "second")] = (j, [ex, a.work], prompt)
    res = parallel(a, jobs)
    out = {}
    for j in a.judges:
        for name in a.exemplars:
            r1, r2 = res[(j, name, "first")], res[(j, name, "second")]
            v1, v2 = side(r1.get("winner"), "1"), side(r2.get("winner"), "2")
            dims = {}
            for d in a.dims:
                d1 = side(r1.get("dimensions", {}).get(d), "1")
                d2 = side(r2.get("dimensions", {}).get(d), "2")
                dims[d] = d1 if d1 == d2 else "split"
            if "error" in r1 or "error" in r2:
                out[f"{j}|{name}"] = {"verdict": "error", "error": [r1.get("error"), r2.get("error")]}
                continue
            out[f"{j}|{name}"] = {"verdict": v1 if v1 == v2 else "split", "orders": [v1, v2], "dimensions": dims,
                                  "reasons": [r1.get("reason"), r2.get("reason")],
                                  "gaps": (r1.get("gaps") or []) + (r2.get("gaps") or [])}
    return out


def checks(a) -> dict:
    items = [l[2:].strip() for l in pathlib.Path(a.checks).read_text().splitlines() if l.startswith("- ")]
    listing = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(items))
    prompt = (f"{a.context}\n\nThe attached file is one item. For each check answer true only if the item clearly meets "
              f"it as shown.\n{listing}\n\nReply with JSON only: "
              '{"checks": {"<number>": true|false, ...}, "notes": {"<number of each false check>": "<what is wrong>"}}')
    res = parallel(a, {j: (j, [a.work], prompt) for j in a.judges})
    return {j: {"error": r["error"], "of": len(items)} if "error" in r else
            {"passed": sum(v is True for v in r.get("checks", {}).values()), "of": len(items), **r}
            for j, r in res.items()}


def score(a) -> dict:
    schema = ", ".join(f'"{d}": <1-10, one decimal>' for d in a.dims)
    jobs, orders = {}, {}
    for j in a.judges:
        items = [("work", a.work), *a.exemplars.items()]
        random.Random(f"{a.seed}-{j}").shuffle(items)
        labels = [chr(65 + i) for i in range(len(items))]
        orders[j] = dict(zip(labels, (n for n, _ in items)))
        prompt = (f"{a.context}\n\nThe attached files are items {', '.join(labels)}, in that order. Score each. Reply with "
                  f'JSON only: {{"items": {{"<letter>": {{{schema}}}, ...}}, "fixes": {{"<letter>": [<the 3 changes that '
                  'would most improve it>], ...}}')
        jobs[j] = (j, [p for _, p in items], prompt)
    res = parallel(a, jobs)
    return {j: {"scores": {orders[j].get(k, k): v for k, v in r.get("items", {}).items()},
                "fixes": {orders[j].get(k, k): v for k, v in r.get("fixes", {}).items()}, **({"error": r["error"]} if "error" in r else {})}
            for j, r in res.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["pairwise", "checks", "score"])
    ap.add_argument("--work", required=True)
    ap.add_argument("--exemplar", action="append", default=[], help="name=path, repeatable")
    ap.add_argument("--checks", help="markdown file, one '- ' line per binary check")
    ap.add_argument("--context", required=True, help="text, or a path to a file holding it")
    ap.add_argument("--dimensions", default=DEFAULT_DIMENSIONS)
    ap.add_argument("--judges", default="opus,sol", help="comma list of roster agent names")
    ap.add_argument("--roster", default=DEFAULT_ROSTER, help="roster.toml whose agents are the judges")
    ap.add_argument("--seed", default="0")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ctx = pathlib.Path(a.context)
    a.context = ctx.read_text() if ctx.is_file() else a.context
    a.dims = a.dimensions.split(",")
    a.judges = a.judges.split(",")
    roster = tomllib.loads(pathlib.Path(a.roster).read_text())["agents"]
    unknown = [j for j in a.judges if j not in roster]
    if unknown:
        ap.error(f"unknown judge {', '.join(unknown)}; the roster has {', '.join(roster)}")
    a.models = {j: roster[j]["model"] for j in a.judges}
    a.exemplars = dict(e.split("=", 1) for e in a.exemplar)
    if a.mode == "pairwise" and not a.exemplars:
        ap.error("pairwise needs --exemplar")
    if a.mode == "checks" and not a.checks:
        ap.error("checks needs --checks")
    result = {"pairwise": pairwise, "checks": checks, "score": score}[a.mode](a)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"mode": a.mode, "work": a.work, "exemplars": a.exemplars, "judges": a.judges,
                               "result": result}, indent=1))
    for key, r in result.items():
        if "error" in r:
            print(f"{key}: error")
        elif a.mode == "pairwise":
            print(f"{key}: {r['verdict']}")
        elif a.mode == "checks":
            print(f"{key}: {r['passed']}/{r['of']}")
        else:
            print(f"{key}: " + ", ".join(f"{n} {s.get('overall')}" for n, s in r["scores"].items()))
    print(out)
    raise SystemExit(1 if any("error" in r for r in result.values()) else 0)


if __name__ == "__main__":
    main()
