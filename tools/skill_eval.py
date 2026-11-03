#!/usr/bin/env python3
"""skill-eval: score how well each skill store routes real requests to the right skill.

  skill-eval [--store S,...] [--runs N] [--model M]        score every case in the case file
  skill-eval --propose STORE:SKILL.md [--drop STORE:NAME]   score the store as it is and with the change, side by side
  skill-eval catalog STORE [--propose ...] [--drop ...]     print the skill list exactly as that store's router sees it

Stores and what their router is shown:
  omp     ~/.omp/agent/skills and ~/.agents/skills filtered by config.yml skills.includeSkills/ignoredSkills, without
          hide or disable-model-invocation skills; each description as omp renders it: the <=12-word hint its smol model
          compressed (cached in ~/.omp/agent/skill-descriptions.db), else the first sentence or 99-character preview
  dross   Dross's agent_skills rows plus its built-ins, rendered by Dross's own formatSkillsCatalogInstruction
  brain   nbrain's skills, styles and built-ins as its MCP server instructions list them (first sentence, 200 chars)
  claude  ~/.claude/skills without disable-model-invocation skills

A case is one JSON line in the case file: {"id", "store", "request", "expect": [names], "allow": [names], "source"}.
`expect` is the set the router must load ([] means none fits); `allow` names extra loads that are not wrong.
A run passes when the loaded set holds every expected name and nothing outside expect + allow.
The router is a fresh model call per case and run (through `omp -p`) with the store's catalog as its system prompt.
"""
import argparse, concurrent.futures, fnmatch, hashlib, json, os, re, sqlite3, subprocess, sys, tempfile
from pathlib import Path

HOME = Path.home()
OMP = HOME / ".bun" / "bin" / "omp"
CASES = HOME / "Projects" / "nstack" / "local" / "evals" / "skill-routing" / "cases.jsonl"
DROSS = HOME / "Projects" / "dross"
NBRAIN = HOME / "Projects" / "nbrain"
BRAIN_CONTEXT = Path(os.environ.get("BRAIN_CONTEXT") or HOME / ".brain" / "context")
OMP_AGENT = HOME / ".omp" / "agent"
STORES = ("omp", "dross", "brain", "claude")
ROUTER_MODEL = "anthropic/claude-opus-5-5"
# omp's prompts/skills/compress-description.md (omp v18.15), hashed into every cache key; a template change shows up as
# "0 cached" in `skill-eval catalog omp` and needs this copy updated.
OMP_COMPRESS_TEMPLATE = (
    "Compress into one routing hint of at most 12 words: WHEN to use; WHEN NOT only if it prevents confusion. "
    "Retain recognizable trigger words. Do not restate the skill name or market it. Output one line without bullets "
    "or quotes.\n\nSkill: {{name}}\nDescription: {{description}}\n")
ROUTER_TASK = (
    "You are the assistant in this session and have just received the user's message below. Before doing anything "
    "else, decide which of the skills listed above you would load for it. Reply with only a JSON object: "
    '{"skills": [<exact skill names>]}, an empty list when none applies.')


# ---- SKILL.md frontmatter -------------------------------------------------------------------------------------------

def frontmatter(text):
    """Top-level scalar keys of a SKILL.md's YAML frontmatter, as a YAML parser yields them (plain, quoted, folded and
    literal block scalars; nested maps are skipped)."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        raise ValueError("no frontmatter")
    lines, out, i = m.group(1).split("\n"), {}, 0
    while i < len(lines):
        km = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", lines[i])
        i += 1
        if not km:
            continue
        key, raw = km.group(1), km.group(2).rstrip()
        if re.fullmatch(r"[>|][+-]?", raw):
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i]); i += 1
            while block and not block[-1].strip():
                block.pop()
            indent = min(len(b) - len(b.lstrip()) for b in block if b.strip()) if block else 0
            body = [b[indent:] for b in block]
            value = " ".join(b for b in body if b) if raw[0] == ">" else "\n".join(body)
            out[key] = value if raw.endswith("-") else value + "\n"
        elif raw.startswith('"'):
            out[key] = json.loads(raw)
        elif raw.startswith("'"):
            out[key] = raw[1:-1].replace("''", "'")
        elif raw:
            out[key] = raw
    return out


def read_skill(path):
    fm = frontmatter(Path(path).read_text())
    return {"name": fm["name"], "description": fm.get("description", ""), "fm": fm}


def truthy(value):
    return str(value).strip().lower() == "true"


# ---- stores ---------------------------------------------------------------------------------------------------------

def config_lists(text, section, key):
    """A `key:` list under a top-level `section:` of omp's config.yml."""
    m = re.search(rf"^{section}:\n((?:[ \t]+.*\n?)*)", text, re.M)
    if not m:
        return []
    km = re.search(rf"^[ \t]+{key}:\n((?:[ \t]+- .*\n?)*)", m.group(1), re.M)
    return [re.sub(r"^[ \t]+- ", "", l).strip().strip("'\"") for l in km.group(1).splitlines()] if km else []


def config_value(text, section, key):
    m = re.search(rf"^{section}:\n((?:[ \t]+.*\n?)*)", text, re.M)
    km = m and re.search(rf"^[ \t]+{key}:[ \t]*(\S.*)$", m.group(1), re.M)
    return km.group(1).strip() if km else None


def omp_config():
    return (OMP_AGENT / "config.yml").read_text()


def omp_skills():
    cfg = omp_config()
    include, ignored = config_lists(cfg, "skills", "includeSkills"), set(config_lists(cfg, "skills", "ignoredSkills"))
    seen = {}
    for root in (OMP_AGENT / "skills", HOME / ".agents" / "skills", OMP_AGENT / "managed-skills"):
        for p in sorted(root.glob("*/SKILL.md")) if root.is_dir() else []:
            s = read_skill(p)
            if s["name"] in seen or s["name"] in ignored:
                continue
            if truthy(s["fm"].get("hide")) or truthy(s["fm"].get("disable-model-invocation")):
                continue
            seen[s["name"]] = s
    return [s for n, s in seen.items() if not include or any(fnmatch.fnmatchcase(n, g) for g in include)]


def omp_preview(description):
    """omp's fallback rendering (cnt): the whole text up to 100 chars, else its first sentence of 40+ chars, else a
    word-boundary cut with an ellipsis."""
    t = re.sub(r"\s+", " ", description).strip()
    if len(t) <= 100:
        return t
    r = t[:99]
    s = re.match(r"^.*?[.!?](?=\s|$)", r)
    if s and len(s.group(0)) >= 40:
        return s.group(0)
    cut = r.rfind(" ")
    return (r[:cut].rstrip() if cut >= 40 else r) + "\u2026"


def omp_key(name, description):
    return hashlib.sha256(f"{OMP_COMPRESS_TEMPLATE}\0{name}\0{description}".encode()).hexdigest()


def omp_compress(name, description, smol):
    """What omp's smol model makes of a description it has not compressed yet, with omp's acceptance rule (one line,
    <=160 chars, <=12 words); None when omp would keep the preview."""
    prompt = OMP_COMPRESS_TEMPLATE.replace("{{name}}", name).replace("{{description}}", description)
    out = model_call(smol, " ", prompt).strip()
    if not out or "\n" in out or len(out) > 160 or len(out.split()) > 12:
        return None
    return out


def omp_render(skills, compress=True):
    """(name, shown description, how) for each skill, as omp's system prompt lists them."""
    db = OMP_AGENT / "skill-descriptions.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True) if db.exists() else None
    smol = config_value(omp_config(), "modelRoles", "smol") or "smol"
    smol_model = smol.rsplit(":", 1)[0] if smol.count(":") else smol
    rows = []
    for s in skills:
        key = omp_key(s["name"], s["description"])
        hit = con and con.execute("select description from skill_descriptions where key = ?", (key,)).fetchone()
        failed = con and con.execute("select description from skill_descriptions where key = ?", (f"{key}:{smol_model}",)).fetchone()
        if hit:
            rows.append((s["name"], hit[0], "compressed"))
        elif failed:
            rows.append((s["name"], failed[0], "preview: compression unusable"))
        elif compress:
            fresh = omp_compress(s["name"], s["description"], smol_model)
            rows.append((s["name"], fresh, "compressed now") if fresh else (s["name"], omp_preview(s["description"]), "preview: compression unusable"))
        else:
            rows.append((s["name"], omp_preview(s["description"]), "preview: not compressed yet"))
    return rows


def omp_catalog(skills, compress=True):
    rows = omp_render(sorted(skills, key=lambda s: s["name"]), compress)
    text = "# Skills & Rules\nMatching skill \u2192 MUST read `skill://<name>` first.\n<skills>\n" + "".join(
        f"- {n}: {d}\n" for n, d, _ in rows) + "</skills>"
    return text, rows


def dross_rows():
    sql = ("select coalesce(json_agg(json_build_object('name',name,'description',description,'content',content) "
           "order by name),'[]') from agent_skills where source='user'")
    out = subprocess.run(["docker", "exec", "dross-postgres-1", "psql", "-U", "dross", "-d", "dross", "-At", "-c", sql],
                         check=True, capture_output=True, text=True).stdout
    return [{"name": r["name"], "description": r["description"], "content": r["content"]} for r in json.loads(out)]


DROSS_RENDER = """
import { formatSkillsCatalogInstruction, mergeBuiltinSkills } from "%s/packages/core/src/agent-skill.ts";
import { BUILTIN_AGENT_SKILLS } from "%s/packages/adapters/src/builtin-skills.ts";
const rows = JSON.parse(await Bun.stdin.text());
const skills = mergeBuiltinSkills(BUILTIN_AGENT_SKILLS, rows);
console.log(JSON.stringify({ names: skills.map(s => s.name), text: formatSkillsCatalogInstruction(skills) ?? "" }));
"""


def dross_catalog(rows):
    with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False) as f:
        f.write(DROSS_RENDER % (DROSS, DROSS))
    try:
        out = subprocess.run([str(HOME / ".bun" / "bin" / "bun"), "run", f.name], input=json.dumps(rows),
                             check=True, capture_output=True, text=True).stdout
    finally:
        os.unlink(f.name)
    d = json.loads(out)
    by = {r["name"]: r["description"] for r in rows}
    return d["text"], [(n, by.get(n, ""), "") for n in d["names"]]


def brain_skills():
    out = []
    for prefix, root in (("skills", BRAIN_CONTEXT / "skills"), ("styles", BRAIN_CONTEXT / "styles"), ("nbrain", NBRAIN / "skills")):
        for p in sorted(root.glob("*/SKILL.md")) if root.is_dir() else []:
            s = read_skill(p)
            meta = re.search(r"^metadata:\n((?:[ \t]+.*\n?)*)", re.match(r"^---\n(.*?)\n---", p.read_text(), re.S).group(1) + "\n", re.M)
            kind = re.search(r"^[ \t]+kind:[ \t]*(\S+)", meta.group(1), re.M) if meta else None
            default = re.search(r"^[ \t]+default:[ \t]*['\"]?true", meta.group(1), re.M) if meta else None
            s["path"] = f"{prefix}/{p.parent.name}"
            s["kind"] = kind.group(1).strip("'\"") if kind else ("style" if prefix == "styles" else "skill")
            s["default"] = bool(default)
            out.append(s)
    return out


def first_sentence(text):
    m = re.match(r"^.*?[.!?](?=\s|$)", text.strip(), re.S)
    return re.sub(r"\s+", " ", m.group(0) if m else text.strip())[:200]


def brain_catalog(skills):
    """nbrain's skillsInstructions (src/skills/mcp.ts): one line per entry until ~1,500 chars, then names only."""
    text, rest, rows = ("\n\nSkills and styles: before work one covers, load it with skill_get (or resources/read of its "
                        "skill:// URI) and follow it; 1-3 per task."), [], []
    for s in skills:
        label = f"{s['path']} ({s['kind']}{', the default when no ' + s['kind'] + ' is named' if s['default'] else ''})"
        line = f"\n- {label}: {first_sentence(s['description'])}"
        rows.append((s["path"], first_sentence(s["description"]), ""))
        if rest or len(text) + len(line) > 1500:
            rest.append(s["path"])
        else:
            text += line
    if rest:
        text += "\n- Also: " + ", ".join(rest)
    return text.strip() + "\nSkill names are the paths before the parentheses.", rows


def claude_skills():
    out = []
    for p in sorted((HOME / ".claude" / "skills").glob("*/SKILL.md")):
        s = read_skill(p)
        if not truthy(s["fm"].get("disable-model-invocation")) and not truthy(s["fm"].get("hide")):
            out.append(s)
    return out


def claude_catalog(skills):
    rows = [(s["name"], re.sub(r"\s+", " ", s["description"]).strip()[:1536], "") for s in skills]
    return "<available_skills>\n" + "".join(f"- {n}: {d}\n" for n, d, _ in rows) + "</available_skills>", rows


def apply_changes(store, skills, proposals, drops):
    """The store's skill list with proposed SKILL.md files swapped in (by name) and dropped names removed."""
    key = "path" if store == "brain" else "name"
    skills = [s for s in skills if s[key] not in drops]
    for path in proposals:
        text = Path(path).read_text()
        p = read_skill(path)
        if store == "dross":
            p = {"name": p["name"], "description": p["description"], "content": text}
        if store == "brain":
            old = next((s for s in skills if s["name"] == p["name"]), None)
            p.update(path=old["path"] if old else f"skills/{p['name']}", kind=old["kind"] if old else "skill",
                     default=old["default"] if old else False)
        at = next((i for i, s in enumerate(skills) if s[key] == p[key]), None)
        skills = skills[:at] + [p] + skills[at + 1:] if at is not None else skills + [p]
    return skills


def catalog(store, proposals=(), drops=(), compress=True):
    """(system-prompt text, [(name, shown description, note)]) for one store."""
    if store == "omp":
        return omp_catalog(apply_changes(store, omp_skills(), proposals, drops), compress)
    if store == "dross":
        return dross_catalog(apply_changes(store, dross_rows(), proposals, drops))
    if store == "brain":
        return brain_catalog(apply_changes(store, brain_skills(), proposals, drops))
    if store == "claude":
        return claude_catalog(apply_changes(store, claude_skills(), proposals, drops))
    raise SystemExit(f"unknown store {store}; stores: {', '.join(STORES)}")


# ---- routing --------------------------------------------------------------------------------------------------------

def model_call(model, system, user):
    cmd = [str(OMP), "-p", "--no-session", "--no-title", "--no-tools", "--no-skills", "--no-context-files",
           "--no-rules", "--no-extensions", "--no-lsp", "--thinking", "off", "--model", model, "--system-prompt", system, user]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=tempfile.gettempdir(), timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"omp -p failed ({r.returncode}): {r.stderr.strip()[-400:]}")
    return r.stdout


def route(model, catalog_text, request):
    out = model_call(model, f"{catalog_text}\n\n{ROUTER_TASK}", request)
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        raise RuntimeError(f"router reply is not JSON: {out.strip()[:200]}")
    return sorted(set(json.loads(m.group(0)).get("skills", [])))


def load_cases(path, stores):
    cases = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    return [c for c in cases if c["store"] in stores]


def score(model, store, catalog_text, names, cases, runs, pool):
    """Per case: the loaded set of each run and how many runs passed."""
    known = set(names)
    for c in cases:
        unknown = (set(c["expect"]) | set(c.get("allow", []))) - known
        if unknown:
            print(f"  note {c['id']}: {', '.join(sorted(unknown))} not in the {store} catalog", file=sys.stderr)
    jobs = {(c["id"], i): pool.submit(route, model, catalog_text, c["request"]) for c in cases for i in range(runs)}
    results = []
    for c in cases:
        picks = [jobs[(c["id"], i)].result() for i in range(runs)]
        want, ok_extra = set(c["expect"]), set(c["expect"]) | set(c.get("allow", []))
        passed = sum(1 for p in picks if want <= set(p) and set(p) <= ok_extra)
        results.append({"id": c["id"], "expect": sorted(want), "picks": picks, "passed": passed, "runs": runs,
                        "request": c["request"]})
    return results


def summary(results):
    n = len(results)
    return sum(r["passed"] / r["runs"] for r in results) / n if n else float("nan")


def short(text, width=90):
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= width else t[: width - 1] + "\u2026"


def report(store, label, results):
    print(f"{store:<7} {label:<9} {summary(results) * 100:5.1f}%  ({len(results)} cases)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="run", choices=["run", "catalog"])
    ap.add_argument("catalog_store", nargs="?")
    ap.add_argument("--store", default=",".join(STORES), help="comma-separated stores (default: all)")
    ap.add_argument("--cases", default=str(CASES))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default=ROUTER_MODEL, help=f"router model (default {ROUTER_MODEL})")
    ap.add_argument("--jobs", type=int, default=4, help="concurrent router calls")
    ap.add_argument("--propose", action="append", default=[], metavar="STORE:SKILL.md")
    ap.add_argument("--drop", action="append", default=[], metavar="STORE:NAME")
    ap.add_argument("--json", metavar="PATH", help="write every case's picks here")
    a = ap.parse_args()

    def changes(store):
        pick = lambda items: [v.split(":", 1)[1] for v in items if v.split(":", 1)[0] == store]
        return pick(a.propose), pick(a.drop)

    if a.command == "catalog":
        store = a.catalog_store or sys.exit("usage: skill-eval catalog <store>")
        text, rows = catalog(store, *changes(store))
        if store == "omp":
            cached = sum(1 for *_, how in rows if how == "compressed")
            print(f"[{cached} of {len(rows)} descriptions from omp's compression cache]", file=sys.stderr)
            for n, _, how in rows:
                if how != "compressed":
                    print(f"[{n}: {how}]", file=sys.stderr)
        print(text)
        return

    stores = [s.strip() for s in a.store.split(",") if s.strip()]
    changed = {s for s in STORES if any(v.startswith(s + ":") for v in a.propose + a.drop)}
    if changed:
        stores = [s for s in stores if s in changed] or sorted(changed)
    cases = load_cases(a.cases, stores)
    out = {}
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        for store in stores:
            mine = [c for c in cases if c["store"] == store]
            if not mine:
                print(f"{store:<7} no cases")
                continue
            text, rows = catalog(store)
            base = score(a.model, store, text, [r[0] for r in rows], mine, a.runs, pool)
            report(store, "current", base)
            out[store] = {"current": base}
            if store in changed:
                ptext, prows = catalog(store, *changes(store))
                new = score(a.model, store, ptext, [r[0] for r in prows], mine, a.runs, pool)
                report(store, "proposed", new)
                out[store]["proposed"] = new
                for b, n in zip(base, new):
                    if b["passed"] != n["passed"]:
                        print(f"  {'better' if n['passed'] > b['passed'] else 'worse ':<6} {b['id']}: {b['passed']}/{b['runs']} -> "
                              f"{n['passed']}/{n['runs']}  expect {b['expect'] or '[]'}  now {n['picks'][0] or '[]'}  | {short(b['request'], 60)}")
            final = out[store].get("proposed", base)
            for r in final:
                if r["passed"] < r["runs"]:
                    print(f"  miss {r['id']}: {r['passed']}/{r['runs']}  expect {r['expect'] or '[]'}  got "
                          f"{' | '.join(','.join(p) or '[]' for p in r['picks'])}  | {short(r['request'], 60)}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
