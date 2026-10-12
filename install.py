#!/usr/bin/env python3
"""Install, check or remove nstack.

  python3 install.py              back up, then install (idempotent); ends with --check
  python3 install.py --check      verify the installed state; exit 1 on any problem
  python3 install.py --uninstall  remove nstack and restore what the first install replaced
  python3 install.py --no-dross   leave Dross's home AGENTS.md alone (combines with the above)

What it manages:
  ~/.omp/agent/skills/<name>              symlinks to skills/<name>; other nstack* skills are removed
  ~/.omp/agent/commands/<name>.md         symlinks to commands/*.md (nstack, bro)
  ~/.omp/agent/extensions/nstack-guard.ts symlink to extensions/nstack-guard.ts
  ~/.omp/agent/RULES.md                   marked block from omp-rules.md (always applied by omp)
  ~/.context/home/AGENTS.md               marked block from dross.md (Dross's baseline instructions)

Before the first install changes anything, every managed path is copied to local/backups/baseline/
with manifest.json; --uninstall restores from it. Every later install also writes a dated backup.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
from fnmatch import fnmatchcase
from pathlib import Path

REPO = Path(__file__).resolve().parent
HOME = Path.home()
OMP = HOME / ".omp" / "agent"
SKILLS = OMP / "skills"
COMMANDS = OMP / "commands"
EXTENSION = OMP / "extensions" / "nstack-guard.ts"
RULES = OMP / "RULES.md"
DROSS_AGENTS = HOME / ".context" / "home" / "AGENTS.md"
CONTRACTS = [HOME / "Projects/context-wt/next/apps/core/src/factory/context.contract.json",
             HOME / "Projects/context/apps/core/src/factory/context.contract.json"]
BACKUPS = REPO / "local" / "backups"
BASELINE = BACKUPS / "baseline"
BEGIN, END = "<!-- nstack:begin -->", "<!-- nstack:end -->"
# Context embeds each standard whole in a worker's 32k-token pack; 8,000 chars is about 2k tokens.
MAX_STANDARD_CHARS = 8000


def repo_skills():
    return sorted(p.name for p in (REPO / "skills").iterdir() if (p / "SKILL.md").is_file())


def links():
    """(installed path, repo source) for every symlink nstack owns."""
    return ([(SKILLS / n, REPO / "skills" / n) for n in repo_skills()]
            + [(COMMANDS / p.name, p) for p in sorted((REPO / "commands").glob("*.md"))]
            + [(EXTENSION, REPO / "extensions" / "nstack-guard.ts")])


def owned(path, source):
    return path.is_symlink() and path.resolve() == source.resolve()


def present(path):
    return path.exists() or path.is_symlink()


def block(source):
    return f"{BEGIN}\n{(REPO / source).read_text().strip()}\n{END}"


def upsert_block(path, source, anchor=None):
    text = path.read_text() if path.exists() else ""
    new = block(source)
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        text = pattern.sub(lambda _: new, text, count=1)
    elif anchor and anchor in text:
        text = text.replace(anchor, f"\n{new}\n{anchor}", 1)
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + new + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def remove_block(path):
    if not path.exists():
        return
    text = re.sub(r"\n?" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "", path.read_text(), flags=re.S)
    path.write_text(text)


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif present(path):
        path.unlink()


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir() and not src.is_symlink():
        shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copy2(src, dst, follow_symlinks=False)


def backup(dross):
    """Copy every path an install may replace. The first backup is the baseline uninstall restores."""
    targets = [p for p, _ in links()] + list(SKILLS.glob("nstack*")) + [RULES, OMP / "AGENTS.md"]
    targets = list(dict.fromkeys(targets + ([DROSS_AGENTS] if dross else [])))
    BACKUPS.mkdir(parents=True, exist_ok=True)
    first = not (BASELINE / "manifest.json").exists()
    dest = BASELINE if first else Path(tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-"), dir=BACKUPS))
    dest.mkdir(exist_ok=True)
    manifest = {}
    for p in targets:
        name = str(p.relative_to(HOME)).replace("/", "__").lstrip(".")
        manifest[str(p)] = name if present(p) else None
        if present(p):
            copy(p, dest / name)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return dest


def install(dross):
    dest = backup(dross)
    names = repo_skills()
    for old in SKILLS.glob("nstack*"):
        if old.name not in names:
            remove(old)
    for path, source in links():
        remove(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(source)
    upsert_block(RULES, "omp-rules.md")
    if dross and DROSS_AGENTS.exists():
        upsert_block(DROSS_AGENTS, "dross.md", anchor="\n## Email")
    print(f"installed {', '.join(names)}; backup at {dest.relative_to(REPO)}")


def uninstall(dross):
    for path, source in links():
        if owned(path, source):
            path.unlink()
    remove_block(RULES)
    if RULES.exists() and not RULES.read_text().strip():
        RULES.unlink()
    if dross:
        remove_block(DROSS_AGENTS)
    manifest_path = BASELINE / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    restored = []
    for raw, name in manifest.items():
        path = Path(raw)
        # Instruction files keep later edits: only nstack's marked blocks come out of them.
        if name and not present(path) and path not in (RULES, DROSS_AGENTS, OMP / "AGENTS.md"):
            copy(BASELINE / name, path)
            restored.append(str(path.relative_to(HOME)))
    print("removed nstack links and blocks" + (f"; restored {', '.join(restored)}" if restored else ""))


def config_problems(names):
    config = OMP / "config.yml"
    if not config.exists():
        return []
    try:
        try:
            import yaml
            cfg = yaml.safe_load(config.read_text()) or {}
        except ImportError:  # omp ships with bun, which parses YAML natively
            js = "console.log(JSON.stringify(Bun.YAML.parse(await Bun.file(process.env.CFG).text()) ?? {}))"
            run = subprocess.run(["bun", "-e", js], env={**os.environ, "CFG": str(config)},
                                 capture_output=True, text=True, check=True)
            cfg = json.loads(run.stdout)
    except Exception as e:  # a parse failure makes the check meaningless, so it fails loudly
        return [f"cannot read {config}: {e}"]
    skills = cfg.get("skills") or {}
    if skills.get("enabled") is False:
        return ["config.yml sets skills.enabled: false"]
    include = skills.get("includeSkills") or []
    ignored = skills.get("ignoredSkills") or []
    disabled = set(cfg.get("disabledExtensions") or [])
    problems = []
    for name in names:
        if include and not any(fnmatchcase(name, pat) for pat in include):
            problems.append(f"config.yml includeSkills does not admit {name}")
        if any(fnmatchcase(name, pat) for pat in ignored) or f"skill:{name}" in disabled:
            problems.append(f"config.yml excludes {name}")
    return problems


def check(dross):
    problems = []
    names = repo_skills()
    for name in names:
        text = (REPO / "skills" / name / "SKILL.md").read_text()
        m = re.search(r"^name:\s*(\S+)", text, re.M)
        if not m or m.group(1) != name:
            problems.append(f"skill {name}: frontmatter name does not match its directory")
        if len(text) > MAX_STANDARD_CHARS:
            problems.append(f"skill {name}: {len(text)} chars, over the {MAX_STANDARD_CHARS} standard cap")
    for path, source in links():
        if not owned(path, source):
            problems.append(f"{path} is not linked to {source.relative_to(REPO)}")
    for p in SKILLS.glob("nstack*"):
        if p.name not in names:
            problems.append(f"stale skill {p} is still installed")
    for path, source in [(RULES, "omp-rules.md")] + ([(DROSS_AGENTS, "dross.md")] if dross else []):
        if not path.exists() or block(source) not in path.read_text():
            problems.append(f"{path} lacks the current block from {source}")
    for contract in CONTRACTS:
        if contract.exists():
            for task_type, name in json.loads(contract.read_text()).get("standards", {}).items():
                if name not in names:
                    problems.append(f"{contract}: taskType {task_type} maps to {name}, which nstack does not ship")
    problems += config_problems(names)
    for p in problems:
        print("FAIL", p)
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return not problems


if __name__ == "__main__":
    args = set(sys.argv[1:])
    dross = "--no-dross" not in args
    if "--check" in args:
        sys.exit(0 if check(dross) else 1)
    if "--uninstall" in args:
        uninstall(dross)
    else:
        install(dross)
        sys.exit(0 if check(dross) else 1)
