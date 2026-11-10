"""Tests for session_audit.py. Each runs a copy of the real script inside a
temporary repository tree with a temporary HOME holding fabricated omp session
logs, so no real session log is read and nothing under the real `local/` is
written.

    python3 -B -m unittest audit/scripts/session_audit_test.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_audit.py")


def read_nstack() -> dict:
    return {"type": "toolCall", "name": "read", "arguments": {"path": "skill://nstack"}}


def edit_file(path: str = "a.py") -> dict:
    return {"type": "toolCall", "name": "edit", "arguments": {"path": path}}


def user(text: str) -> tuple:
    return ("user", text)


def assistant(blocks: list, cost: float = 0.0, response_id: str | None = None) -> tuple:
    return ("assistant", blocks, cost, response_id)


def session_lines(sid: str, cwd: str, start: str, events: list) -> list[str]:
    """Lines in omp's session format. Timestamps rise one second per line from `start` (HH:MM:SS on 2026-11-01)."""
    hh, mm, ss = (int(x) for x in start.split(":"))
    base = hh * 3600 + mm * 60 + ss

    def ts(n: int) -> str:
        t = base + n
        return f"2026-11-01T{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}.000Z"

    lines = [{"type": "session", "id": sid, "cwd": cwd, "timestamp": ts(0)}]
    for n, ev in enumerate(events, 1):
        if ev[0] == "user":
            msg = {"role": "user", "content": [{"type": "text", "text": ev[1]}]}
        else:
            msg = {"role": "assistant", "content": ev[1], "model": "test-model",
                   "usage": {"cost": {"total": ev[2]}}}
            if ev[3]:
                msg["responseId"] = ev[3]
        lines.append({"type": "message", "timestamp": ts(n), "message": msg})
    return [json.dumps(x) for x in lines]


class AuditCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = os.path.join(self.tmp.name, "home")
        self.repo = os.path.join(self.tmp.name, "repo")
        scripts = os.path.join(self.repo, "audit", "scripts")
        os.makedirs(scripts)
        os.makedirs(self.home)
        self.script = os.path.join(scripts, os.path.basename(SCRIPT))
        shutil.copy(SCRIPT, self.script)

    def add_session(self, name: str, events: list, start: str = "10:00:00",
                    cwd: str = "/work/project", project: str = "-work-project") -> str:
        d = os.path.join(self.home, ".omp", "agent", "sessions", project)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name + ".jsonl"), "w") as fh:
            fh.write("\n".join(session_lines(name, cwd, start, events)) + "\n")
        return f"omp__{project}__{name}"

    def run_audit(self, *args: str) -> subprocess.CompletedProcess:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.home}
        return subprocess.run([sys.executable, "-B", self.script, *args], env=env, cwd=self.home,
                              capture_output=True, text=True, timeout=120)

    def files(self) -> set[str]:
        return {os.path.join(root, f) for root, _, fs in os.walk(self.tmp.name) for f in fs}

    def summary_row(self, stdout: str, label: str) -> list[str]:
        for line in stdout.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("|") and cells[0] == label:
                return cells[1:]
        self.fail(f"no row {label!r} in:\n{stdout}")


class Audit(AuditCase):
    def test_help_prints_usage_and_writes_nothing(self):
        """Bug: asking for help runs the audit and overwrites the last output."""
        self.add_session("s1", [user("go"), assistant([edit_file()])])
        before = self.files()
        p = self.run_audit("--help")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("usage:", p.stdout)
        self.assertEqual(self.files(), before)

    def test_skill_read_after_first_edit_is_not_counted_as_read_before(self):
        """Bug: a session that read the skill only after its first edit counts as having read it."""
        self.add_session("a", [user("go"), assistant([read_nstack()]), assistant([edit_file()])], "10:00:00")
        self.add_session("b", [user("go"), assistant([edit_file()]), assistant([read_nstack()])], "11:00:00")
        self.add_session("c", [user("go"), assistant([edit_file()])], "12:00:00")
        self.add_session("d", [user("go"), assistant([read_nstack()])], "13:00:00")
        # one message holding the read before the edit counts as before
        self.add_session("e", [user("go"), assistant([read_nstack(), edit_file()])], "14:00:00")
        p = self.run_audit("--out", os.path.join(self.tmp.name, "out"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.summary_row(p.stdout, "Root sessions"), ["5"])
        self.assertEqual(self.summary_row(p.stdout, "Edited a file"), ["4"])
        self.assertEqual(self.summary_row(p.stdout, "Read nstack before the first edit"), ["2"])
        self.assertEqual(self.summary_row(p.stdout, "Read nstack after the first edit"), ["1"])
        self.assertEqual(self.summary_row(p.stdout, "Never read nstack"), ["1"])
        with open(os.path.join(self.tmp.name, "out", "summary.md")) as fh:
            self.assertIn("| Never read nstack | 1 |", fh.read())

    def test_a_tool_call_or_message_sent_through_write_is_not_an_edit(self):
        """Bug: a write to xd://, agent://, proc://, out:// or cfg:// counts as the session's first file edit."""
        def send(path: str) -> dict:
            return {"type": "toolCall", "name": "write", "arguments": {"path": path, "content": "{}"}}
        self.add_session("a", [user("go"), assistant([send("xd://mcp__memory_search")]),
                               assistant([read_nstack()]), assistant([edit_file()])], "10:00:00")
        self.add_session("b", [user("go"), assistant([send("agent://Worker"), send("proc://bg_1/kill"),
                                                      send("out://"), send("cfg://task/save")])], "11:00:00")
        p = self.run_audit("--out", os.path.join(self.tmp.name, "out"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.summary_row(p.stdout, "Edited a file"), ["1"])
        self.assertEqual(self.summary_row(p.stdout, "Read nstack before the first edit"), ["1"])
        self.assertEqual(self.summary_row(p.stdout, "Read nstack after the first edit"), ["0"])

    def test_an_owner_runs_report_files_are_not_edits(self):
        """Bug: an owner run that only wrote its report and DONE.txt counts as editing without reading the skill."""
        owners = os.path.join(self.home, ".dross", "core", "owners", "learning")

        def write(path: str) -> dict:
            return {"type": "toolCall", "name": "write", "arguments": {"path": path, "content": "x"}}
        self.add_session("a", [user("go"), assistant([write("report.json"), write(f"{owners}/r1/DONE.txt")])],
                         "10:00:00", cwd=f"{owners}/r1", project="-owners-r1")
        self.add_session("b", [user("go"), assistant([write("DONE.txt")]), assistant([write("/work/page/index.html")])],
                         "11:00:00", cwd=f"{owners}/r2", project="-owners-r2")
        self.add_session("c", [user("go"), assistant([write("question.json")]), assistant([read_nstack()]),
                               assistant([write("/work/page/index.html")])],
                         "12:00:00", cwd=f"{owners}/r3", project="-owners-r3")
        p = self.run_audit("--out", os.path.join(self.tmp.name, "out"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.summary_row(p.stdout, "Edited a file"), ["2"])
        self.assertEqual(self.summary_row(p.stdout, "Read nstack after the first edit"), ["0"])
        self.assertEqual(self.summary_row(p.stdout, "Owner runs that edited outside their run folder"), ["2"])
        self.assertEqual(self.summary_row(p.stdout, "Owner runs that read nstack before that edit"), ["1"])

    def test_rerun_does_not_replace_the_earlier_run(self):
        """Bug: a rerun replaces the earlier run."""
        self.add_session("s1", [user("go"), assistant([edit_file()])])
        for _ in range(2):
            p = self.run_audit()
            self.assertEqual(p.returncode, 0, p.stderr)
        runs = os.path.join(self.repo, "local", "audit", "runs")
        dirs = sorted(os.listdir(runs))
        self.assertEqual(len(dirs), 2, dirs)
        self.assertTrue(dirs[1].startswith(dirs[0]) and dirs[1].endswith("-2"), dirs)
        for d in dirs:
            for name in ("sessions.jsonl", "summary.md", "corrections.md"):
                self.assertTrue(os.path.isfile(os.path.join(runs, d, name)), (d, name))
        self.assertEqual(p.stdout.splitlines()[-1], os.path.join(runs, dirs[1]))

    def test_follow_up_messages_are_collected_verbatim(self):
        """Bug: follow-up messages are lost, so nobody can see what was corrected."""
        key = self.add_session("a", [user("build the thing"), assistant([edit_file()]),
                                     user("no, keep the old flag"), assistant([], 0.0),
                                     user("thanks, now the tests")])
        self.add_session("b", [user("one message only, never followed up"), assistant([edit_file()])], "11:00:00")
        # a run started by one of Dross's owners: its follow-ups are not Nate's corrections
        owner_cwd = os.path.join(self.home, ".dross", "core", "owners", "mail")
        self.add_session("o", [user("brief"), assistant([edit_file()]), user("owner follow-up")],
                         "12:00:00", cwd=owner_cwd, project="-owner")
        out = os.path.join(self.tmp.name, "out")
        p = self.run_audit("--out", out)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.summary_row(p.stdout, "Follow-up messages"), ["2"])
        with open(os.path.join(out, "corrections.md")) as fh:
            text = fh.read()
        self.assertIn(key, text)
        self.assertIn("no, keep the old flag", text)
        self.assertIn("thanks, now the tests", text)
        self.assertNotIn("build the thing", text)
        self.assertNotIn("one message only", text)
        self.assertNotIn("owner follow-up", text)

    def test_forked_session_cost_is_counted_once(self):
        """Bug: a forked session's cost is counted twice."""
        shared = assistant([], 1.0, "resp-shared")
        self.add_session("parent", [user("go"), shared], "10:00:00")
        self.add_session("fork", [user("go"), shared, assistant([], 0.5, "resp-new")], "11:00:00")
        out = os.path.join(self.tmp.name, "out")
        self.assertEqual(self.run_audit("--out", out).returncode, 0)
        with open(os.path.join(out, "sessions.jsonl")) as fh:
            recs = [json.loads(line) for line in fh]
        self.assertEqual(sum(r["total_cost_dedup"] for r in recs), 1.5)


class Masking(AuditCase):
    def test_pasted_credentials_are_not_copied_into_the_outputs(self):
        """Bug: a key Nate pasted into a message is copied into the corrections file (and the digests)."""
        pasted = ("fine, but use sk-test0123456789abcdefghij for it. Also\nPASSWORD=hunter2hunter2\n"
                  "and password: swordfish99 here. The word pneumonoultramicroscopicsilicovolcanoconiosis stays. "
                  "Commit 0123456789abcdef0123456789abcdef01234567 is masked too: the 32-character rule cannot "
                  "tell a git SHA from a secret, which is accepted.")
        self.add_session("a", [user("build it"), assistant([edit_file()]), user(pasted)])
        out = os.path.join(self.tmp.name, "out")
        self.assertEqual(self.run_audit("--out", out, "--digests").returncode, 0)
        for path in (os.path.join(out, "corrections.md"), os.path.join(out, "md", "omp__-work-project__a.md")):
            with open(path) as fh:
                text = fh.read()
            for secret in ("sk-test0123456789abcdefghij", "hunter2hunter2", "swordfish99",
                           "0123456789abcdef0123456789abcdef01234567"):
                self.assertNotIn(secret, text, path)
            self.assertIn("PASSWORD=[redacted]", text, path)
            self.assertIn("password: [redacted] here. The word pneumonoultramicroscopicsilicovolcanoconiosis stays.",
                          text, path)
            self.assertIn("fine, but use [redacted] for it.", text, path)


if __name__ == "__main__":
    unittest.main()
