"""Tests for judge.py. Each runs the real script as a subprocess with a fake `omp` first on PATH; none reach a model."""
import json, os, pathlib, subprocess, sys, tempfile, unittest

JUDGE = pathlib.Path(__file__).with_name("judge.py")

FAKE_OMP = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_OMP_LOG"], "a") as f:
    f.write(json.dumps(sys.argv) + "\\n")
plan = json.load(open(os.environ["FAKE_OMP_PLAN"]))
files = [a[1:] for a in sys.argv if a.startswith("@")]
contents = [open(p).read() for p in files]
rule = "work_first" if contents and contents[0] == "WORK" else "work_second" if "WORK" in contents else "any"
reply = plan[rule] if rule in plan else plan["any"]
sys.stdout.write(reply.get("stdout", ""))
sys.stderr.write(reply.get("stderr", ""))
sys.exit(reply.get("code", 0))
"""

ROSTER = """[agents.opus]
model = "test/opus-model"

[agents.sol]
model = "test/sol-model"
"""


def answer(winner: str) -> dict:
    return {"stdout": json.dumps({"winner": winner, "dimensions": {}, "reason": "r", "gaps": []})}


class JudgeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = pathlib.Path(self._tmp.name)
        fake = self.dir / "omp"
        fake.write_text(FAKE_OMP)
        fake.chmod(0o755)
        (self.dir / "roster.toml").write_text(ROSTER)
        (self.dir / "ours.txt").write_text("WORK")
        (self.dir / "chatgpt.txt").write_text("EXEMPLAR")
        (self.dir / "checks.md").write_text("- first\n- second\n- third\n")
        self.log = self.dir / "calls.jsonl"

    def judge(self, plan: dict, *args: str) -> subprocess.CompletedProcess:
        (self.dir / "plan.json").write_text(json.dumps(plan))
        env = {**os.environ, "PATH": f"{self.dir}{os.pathsep}{os.environ['PATH']}",
               "FAKE_OMP_LOG": str(self.log), "FAKE_OMP_PLAN": str(self.dir / "plan.json")}
        return subprocess.run(
            [sys.executable, "-B", str(JUDGE), *args, "--work", str(self.dir / "ours.txt"), "--context", "test",
             "--roster", str(self.dir / "roster.toml"), "--out", str(self.dir / "out.json")],
            capture_output=True, text=True, env=env, timeout=60)

    def pairwise(self, plan: dict, *extra: str) -> subprocess.CompletedProcess:
        return self.judge(plan, "pairwise", "--exemplar", f"chatgpt={self.dir / 'chatgpt.txt'}", "--judges", "opus", *extra)

    def test_failed_judge_is_not_zero_checks_passed(self):
        """Bug: a judge that failed is printed as 0 of N checks passed."""
        r = self.judge({"any": {"code": 1, "stderr": "boom"}}, "checks", "--checks", str(self.dir / "checks.md"),
                       "--judges", "opus")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("opus: error", r.stdout)
        self.assertNotIn("0/3", r.stdout)
        entry = json.loads((self.dir / "out.json").read_text())["result"]["opus"]
        self.assertIn("error", entry)
        self.assertNotIn("passed", entry)

    def test_failure_in_one_order_is_not_split(self):
        """Bug: a judge that failed in one order is printed as split."""
        r = self.pairwise({"work_first": {"code": 1, "stderr": "boom"}, "work_second": answer("2")})
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("opus|chatgpt: error\n", r.stdout)

    def test_disagreeing_orders_are_split(self):
        """Bug: a verdict counts when the two orders disagree (a judge that prefers whichever came first)."""
        r = self.pairwise({"any": answer("1")})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("opus|chatgpt: split\n", r.stdout)

    def test_work_wins_only_in_both_orders(self):
        """Bug: the work wins only when it wins in both orders; the mirror is an exemplar win."""
        r = self.pairwise({"work_first": answer("1"), "work_second": answer("2")})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("opus|chatgpt: work\n", r.stdout)
        r = self.pairwise({"work_first": answer("2"), "work_second": answer("1")})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("opus|chatgpt: exemplar\n", r.stdout)

    def test_attachment_names_do_not_reveal_the_work(self):
        """Bug: an attachment's file name tells the judge which item is ours."""
        r = self.pairwise({"work_first": answer("1"), "work_second": answer("2")})
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        for argv in calls:
            for arg in argv[1:]:
                self.assertNotIn("ours", arg)
                self.assertNotIn("chatgpt", arg)

    def test_judge_names_resolve_from_the_roster(self):
        """Bug: judge names resolve from a private copy of model ids instead of the roster."""
        r = self.judge({"any": answer("1")}, "pairwise", "--exemplar", f"chatgpt={self.dir / 'chatgpt.txt'}",
                       "--judges", "nosuch")
        self.assertEqual(r.returncode, 2)
        self.assertIn("opus", r.stderr)
        self.assertIn("sol", r.stderr)
        r = self.judge({"any": answer("1")}, "pairwise", "--exemplar", f"chatgpt={self.dir / 'chatgpt.txt'}",
                       "--judges", "sol")
        self.assertEqual(r.returncode, 0, r.stderr)
        for line in self.log.read_text().splitlines():
            argv = json.loads(line)
            self.assertEqual(argv[argv.index("--model") + 1], "test/sol-model")


if __name__ == "__main__":
    unittest.main()
