"""Tests for install.py. Each runs the real installer against a temporary HOME, a small roster and a model
catalog written by the test, so neither ~/.omp nor `omp models` is touched.

    python3 -B -m unittest install_test.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

INSTALL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install.py")

ROLES = {
    "author": ("Default author", "implementation and review", ["opus"]),
    "systems": ("Hard systems work", "complex debugging and concurrency", ["astra"]),
    "taste": ("Taste-critical work", "anything visual", ["opus"]),
    "implementer": ("Medium and easy tasks", "bounded fixes and tests", ["sonnet"]),
    "reader": ("Bulk reading", "extraction of large logs", ["muse"]),
    "research": ("Research lanes", "one research lane each", ["researcher"]),
    "verify": ("Verification lanes", "re-reads cited pages", ["verifier"]),
}
AGENTS = {
    "opus": ("anthropic/claude-opus-5-5", "Claude Opus 5.5", "anthropic", "medium", None),
    "astra": ("openai-codex/gpt-6-astra", "GPT-6 Astra", "openai", "medium", None),
    "sonnet": ("anthropic/claude-sonnet-5-5", "Claude Sonnet 5.5", "anthropic", "medium", "fast"),
    "muse": ("openrouter/meta/muse-spark-1.3-contributor", "Muse Spark 1.3", "meta", "medium", "near-free"),
    "researcher": ("anthropic/claude-sonnet-5-5", "Claude Sonnet 5.5", "anthropic", "high", None),
    "verifier": ("anthropic/claude-sonnet-5-5", "Claude Sonnet 5.5", "anthropic", "high", None),
}
SPARE = {"spare": ("anthropic/claude-haiku-5", "Claude Haiku 5", "anthropic", "medium", None)}
MODELS = sorted({a[0] for a in {**AGENTS, **SPARE}.values()})


def roster_toml(roles: dict, agents: dict) -> str:
    lines = []
    for role, (title, does, names) in roles.items():
        lines += [f"[roles.{role}]", f"title = {json.dumps(title)}", f"does = {json.dumps(does)}",
                  f"agents = {json.dumps(names)}", ""]
    for name, (model, label, family, thinking, note) in agents.items():
        lines += [f"[agents.{name}]", f"model = {json.dumps(model)}", f"label = {json.dumps(label)}",
                  f"family = {json.dumps(family)}", f"thinking = {json.dumps(thinking)}"]
        lines += [f"note = {json.dumps(note)}"] if note else []
        lines.append("")
    return "\n".join(lines)


class InstallCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.omp = os.path.join(self.home, ".omp", "agent")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install(self, config: str | None = None, roles: dict = ROLES, agents: dict = AGENTS,
                omit: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
        """Run `install.py` with the given roster, catalog (every test model except `omit`) and config.yml;
        stdout and stderr come back together."""
        work = os.path.join(self.home, "work")
        os.makedirs(work)
        roster, catalog = os.path.join(work, "roster.toml"), os.path.join(work, "catalog.json")
        with open(roster, "w") as f:
            f.write(roster_toml(roles, agents))
        with open(catalog, "w") as f:
            json.dump({"models": [{"selector": m, "thinking": ["medium", "high"]} for m in MODELS if m not in omit]}, f)
        if config is not None:
            os.makedirs(self.omp, exist_ok=True)
            with open(os.path.join(self.omp, "config.yml"), "w") as f:
                f.write(config)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.home}
        return subprocess.run([sys.executable, "-B", INSTALL, "--roster", roster, "--catalog", catalog], env=env,
                              cwd=self.home, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)

    def installed(self, *parts: str) -> str:
        with open(os.path.join(self.omp, *parts)) as f:
            return f.read()

    def lines(self, p: subprocess.CompletedProcess, prefix: str) -> list[str]:
        return [line for line in p.stdout.splitlines() if line.startswith(prefix + " ")]


class SwitchedOff(InstallCase):
    def test_off_agent_is_left_out_of_routing(self):
        """Bug: an agent Nate switched off in omp blocks every install."""
        p = self.install("task:\n  disabledAgents: [astra]\n")
        self.assertEqual(p.returncode, 0, p.stdout)
        routing = self.installed("AGENTS.md")
        self.assertIn("Hard systems work: no agent is enabled; the default author takes it.", routing)
        self.assertIn("Switched off in omp or missing from its catalog, so not spawnable: `astra`.", routing)
        self.assertTrue(os.path.isfile(os.path.join(self.omp, "agents", "astra.md")))
        notes = [line for line in self.lines(p, "NOTE") if "astra" in line]
        self.assertEqual(len(notes), 1, p.stdout)
        self.assertIn("task.disabledAgents", notes[0])
        self.assertFalse([line for line in self.lines(p, "WARN") if "astra" in line], p.stdout)

    def test_reviews_do_not_go_to_off_agent(self):
        """Bug: routing sends reviews to an agent omp will not spawn."""
        p = self.install("task:\n  disabledAgents: [astra]\n")
        self.assertEqual(p.returncode, 0, p.stdout)
        routing = self.installed("AGENTS.md")
        self.assertIn("none is enabled, so say in your report that the change had no review", routing)
        self.assertNotIn("work goes to `astra`", routing)

    def test_off_reader_is_not_offered_to_authors(self):
        """Bug: an author is told to delegate reading to an agent omp will not spawn."""
        p = self.install("task:\n  disabledAgents: [muse]\n")
        self.assertEqual(p.returncode, 0, p.stdout)
        author = self.installed("agents", "opus.md")
        self.assertNotIn("muse", author)
        self.assertIn("none enabled", author)

    def test_off_agent_in_no_role_is_not_offered(self):
        """Bug: an agent in no role that omp will not spawn is still offered by name."""
        p = self.install("task:\n  disabledAgents: [spare, astra]\n", agents={**AGENTS, **SPARE})
        self.assertEqual(p.returncode, 0, p.stdout)
        routing = self.installed("AGENTS.md")
        self.assertNotIn("Only when Nate names it", routing)
        self.assertIn("not spawnable: `astra`, `spare`.", routing)


class Catalog(InstallCase):
    def test_model_missing_from_catalog_warns(self):
        """Bug: a model whose provider omp no longer lists blocks every install."""
        p = self.install(omit=("openrouter/meta/muse-spark-1.3-contributor",))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertTrue([line for line in self.lines(p, "WARN") if "muse" in line], p.stdout)
        self.assertIn("- Bulk reading: no agent is enabled; the default author takes it.", self.installed("AGENTS.md"))


class Pinned(InstallCase):
    def test_pinned_model_is_named_in_routing(self):
        """Bug: a model Nate pinned in omp is refused, and the routing names the roster's older model."""
        p = self.install("task:\n  agentModelOverrides:\n    sonnet: anthropic/claude-opus-5-5:medium\n")
        self.assertEqual(p.returncode, 0, p.stdout)
        notes = [line for line in self.lines(p, "NOTE") if "sonnet" in line]
        self.assertEqual(len(notes), 1, p.stdout)
        self.assertIn("anthropic/claude-opus-5-5", notes[0])
        self.assertFalse([line for line in self.lines(p, "WARN") if "sonnet" in line], p.stdout)
        self.assertIn("`sonnet` (pinned in omp to anthropic/claude-opus-5-5)", self.installed("AGENTS.md"))


class Roster(InstallCase):
    def test_invalid_roster_installs_nothing(self):
        """Bug: an invalid roster installs anyway."""
        roles = {**ROLES, "systems": ("Hard systems work", "complex debugging and concurrency", ["astra", "ghost"])}
        p = self.install(roles=roles)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertIn("nothing installed", p.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.omp, "AGENTS.md")))

    def test_routing_unchanged_when_nothing_is_switched(self):
        """Bug: with nothing switched, the routing changes."""
        p = self.install()
        self.assertEqual(p.returncode, 0, p.stdout)
        routing = self.installed("AGENTS.md").splitlines()
        self.assertIn("- Hard systems work: `astra` (GPT-6 Astra). Complex debugging and concurrency.", routing)
        self.assertIn("work goes to `astra`", "\n".join(routing))
        self.assertFalse(self.lines(p, "NOTE") + self.lines(p, "WARN"), p.stdout)


if __name__ == "__main__":
    unittest.main()
