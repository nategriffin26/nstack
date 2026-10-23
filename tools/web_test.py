"""Tests for web.py. Each runs the real CLI against a temp WEB_HOME and HOME
(so no real keys or ledger are touched); providers are a local server
replaying responses recorded on 2026-10-23, keys removed.

    python3 -m unittest tools/web_test.py
"""

from __future__ import annotations

import http.server
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web.py")

EXA_401 = {"requestId": "242510eb227189c64a263a9814ef02f9",
           "error": "Invalid API key. Provide a valid key using 'Authorization: Bearer <key>' or "
                    "'x-api-key: <key>'. Create a key at https://dashboard.exa.ai/api-keys",
           "tag": "INVALID_API_KEY"}
TINYFISH_SEARCH = {
    "query": "exa search api pricing", "total_results": 9, "page": 0,
    "results": [
        {"position": 1, "site_name": "exa.ai", "title": "Exa API Pricing | Pay-as-You-Go Plans for AI Search",
         "url": "https://exa.ai/pricing",
         "snippet": "Free tier and enterprise pricing available . Includes: Free $10 credits per month"},
        {"position": 2, "site_name": "exa.ai", "title": "Pricing", "url": "https://exa.ai/docs/admin/pricing",
         "snippet": "Search. From $4 / 1k requests Real-time search with token-efficient page contents."}]}
TINYFISH_FETCH_404 = {"results": [], "request_id": "531be6da-1c28-497c-8aed-2b34401b8986",
                      "errors": [{"url": "https://example.com/definitely-404-xyz-web-test",
                                  "error": "page_not_found", "status": 404}]}
EXA_CONTENTS = {
    "requestId": "e0a76e85c90e2fe0af5a230d9172c5ee", "searchTime": 412.0,
    "costDollars": {"total": 0.001, "contents": {"text": 0.001}},
    "results": [{"id": "https://example.com/definitely-404-xyz-web-test",
                 "url": "https://example.com/definitely-404-xyz-web-test",
                 "title": "Recovered page", "text": "# Recovered page\n\nThe body Exa could read."}],
    "statuses": [{"id": "https://example.com/definitely-404-xyz-web-test", "status": "success",
                  "source": "cached"}]}


class Fake(http.server.ThreadingHTTPServer):
    """Answers each path prefix with a fixed (status, body) and records requests."""

    def __init__(self, routes: dict[str, tuple[int, dict]]):
        super().__init__(("127.0.0.1", 0), Handler)
        self.routes = routes
        self.requests: list[str] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


class Handler(http.server.BaseHTTPRequestHandler):
    def _answer(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.server.requests.append(self.path)
        status, body = next((v for k, v in self.server.routes.items() if self.path.startswith(k)),
                            (404, {"error": "no route"}))
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = _answer

    def log_message(self, *args) -> None:
        pass


class WebCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.web_home = os.path.join(self.home, "web")
        self.fake: Fake | None = None

    def tearDown(self) -> None:
        if self.fake:
            self.fake.shutdown()
            self.fake.server_close()
        self.tmp.cleanup()

    def serve(self, routes: dict[str, tuple[int, dict]]) -> Fake:
        self.fake = Fake(routes)
        threading.Thread(target=self.fake.serve_forever, daemon=True).start()
        return self.fake

    def web(self, *args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.home, "WEB_HOME": self.web_home,
               "EXA_API_KEY": "test-exa", "TINYFISH_API_KEYS": "test-a,test-b"}
        if self.fake:
            env.update(WEB_EXA_URL=f"{self.fake.url}/exa",
                       WEB_TINYFISH_SEARCH_URL=f"{self.fake.url}/tf-search",
                       WEB_TINYFISH_FETCH_URL=f"{self.fake.url}/tf-fetch")
        return subprocess.run([sys.executable, WEB, *args], env=env, cwd=cwd or self.home,
                              capture_output=True, text=True, timeout=120)

    def db(self) -> sqlite3.Connection:
        self.web("log")   # creates the ledger schema
        return sqlite3.connect(os.path.join(self.web_home, "ledger.db"), isolation_level=None)


class SearchFallback(WebCase):
    def test_exa_failure_falls_back_to_tinyfish(self):
        """Bug: an Exa failure (bad key) ends the search instead of falling back."""
        self.serve({"/exa/search": (401, EXA_401), "/tf-search": (200, TINYFISH_SEARCH)})
        p = self.web("search", "exa search api pricing", "--json", "--lane", "t")
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["provider"], "tinyfish")
        self.assertTrue(out["failed"][0].startswith("exa failed: HTTP 401"), out["failed"])
        self.assertEqual([r["url"] for r in out["results"]],
                         ["https://exa.ai/pricing", "https://exa.ai/docs/admin/pricing"])
        row = self.db().execute("SELECT lane, provider, n FROM queries").fetchone()
        self.assertEqual(row, ("t", "tinyfish", 2))

    def test_text_output_names_the_fallback(self):
        """Bug: a fallback answer reads as if Exa had answered."""
        self.serve({"/exa/search": (401, EXA_401), "/tf-search": (200, TINYFISH_SEARCH)})
        p = self.web("search", "exa search api pricing")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("via tinyfish (exa failed: HTTP 401", p.stdout.splitlines()[0])

    def test_every_provider_down_is_retryable_not_empty(self):
        """Bug: all providers failing prints 'No results' and exits 0."""
        self.serve({"/exa/search": (503, {"error": "unavailable"}),
                    "/tf-search": (503, {"error": "unavailable"})})
        p = self.web("search", "anything")
        self.assertEqual(p.returncode, 75, p.stdout + p.stderr)
        self.assertNotIn("results for", p.stdout)
        self.assertIn("exa failed", p.stderr)
        self.assertIn("tinyfish failed", p.stderr)


class ReadFallback(WebCase):
    URL = "https://example.com/definitely-404-xyz-web-test"

    def test_tinyfish_failure_reads_via_exa_then_store(self):
        """Bug: a page TinyFish cannot read is reported failed instead of read
        through Exa; and a stored page is fetched again instead of served."""
        fake = self.serve({"/tf-fetch": (200, TINYFISH_FETCH_404), "/exa/contents": (200, EXA_CONTENTS)})
        p = self.web("read", self.URL, "--no-archive", "--lane", "t")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("| via exa =====", p.stdout)
        self.assertIn("The body Exa could read.", p.stdout)
        rows = self.db().execute("SELECT url, status, path FROM pages WHERE lane='t' ORDER BY rowid").fetchall()
        ok = [r for r in rows if r[1] == "ok"]
        self.assertEqual([r[0] for r in ok], [self.URL])
        with open(ok[0][2], encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "# Recovered page\n\nThe body Exa could read.")

        seen = len(fake.requests)
        again = self.web("read", self.URL, "--lane", "t2")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("| via store ", again.stdout)
        self.assertEqual(len(fake.requests), seen)
        lanes = self.db().execute("SELECT lane FROM pages WHERE status='ok' ORDER BY rowid").fetchall()
        self.assertEqual(lanes, [("t",), ("t2",)])

    def test_stored_copy_older_than_a_day_is_read_again(self):
        """Bug: a 2-day-old stored copy (stale price, thin read) is served forever."""
        fake = self.serve({"/tf-fetch": (200, TINYFISH_FETCH_404), "/exa/contents": (200, EXA_CONTENTS)})
        self.assertEqual(self.web("read", self.URL, "--no-archive").returncode, 0)
        path = self.db().execute("SELECT path FROM pages WHERE status='ok'").fetchone()[0]
        old = time.time() - 2 * 86400
        os.utime(path, (old, old))
        seen = len(fake.requests)
        p = self.web("read", self.URL, "--no-archive", "--lane", "t2")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("| via exa =====", p.stdout)
        self.assertGreater(len(fake.requests), seen)
        self.assertGreater(os.path.getmtime(path), time.time() - 3600)

    def test_empty_null_or_missing_tinyfish_results_fall_back_to_exa(self):
        """Bug: TinyFish's empty, null or omitted results count as ok reads,
        get logged ok with 0-4 chars, and never reach Exa."""
        urls = [f"https://e.example/{n}" for n in ("empty", "null", "missing")]
        tinyfish = {"results": [{"url": urls[0], "text": ""}, {"url": urls[1], "text": None}], "errors": []}
        exa = {"results": [{"id": u, "url": u, "title": "T", "text": f"full text of {u}"} for u in urls],
               "statuses": [{"id": u, "status": "success"} for u in urls]}
        self.serve({"/tf-fetch": (200, tinyfish), "/exa/contents": (200, exa)})
        p = self.web("read", *urls, "--no-archive", "--lane", "t")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(p.stdout.count("| via exa ====="), 3, p.stdout)
        for u in urls:
            self.assertIn(f"full text of {u}", p.stdout)
        ok = self.db().execute("SELECT url, chars FROM pages WHERE status='ok' ORDER BY url").fetchall()
        self.assertEqual(ok, [(u, len(f"full text of {u}")) for u in sorted(urls)])

    def test_selector_read_is_not_served_to_a_plain_read(self):
        """Bug: a --include-selector read overwrites the stored page, and plain
        reads then get only that fragment from the store for a day."""
        fragment = {"results": [{"url": self.URL, "title": "T", "text": "FOOTER ONLY"}], "errors": []}
        fake = self.serve({"/tf-fetch": (200, fragment)})
        self.assertEqual(self.web("read", self.URL, "--include-selector", "footer").returncode, 0)
        seen = len(fake.requests)
        p = self.web("read", self.URL)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("| via store ", p.stdout)
        self.assertGreater(len(fake.requests), seen)

    def test_javascript_stub_from_tinyfish_is_replaced_by_exa_text(self):
        """Bug: TinyFish returns a ~150-char JavaScript stub, it is logged as an ok
        read, and Exa (which has the real page) is never asked."""
        stub = "You need to enable JavaScript to run this app. " * 3
        a, b = "https://spa.example/a", "https://spa.example/b"
        tinyfish = {"results": [{"url": a, "text": stub}, {"url": b, "text": stub}], "errors": []}
        exa = {"results": [{"id": a, "url": a, "title": "A", "text": "the real page " * 40}],
               "statuses": [{"id": a, "status": "success"}]}
        self.serve({"/tf-fetch": (200, tinyfish), "/exa/contents": (200, exa)})
        p = self.web("read", a, b, "--no-archive", "--lane", "t")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        headers = [line for line in p.stdout.splitlines() if line.startswith("=====")]
        self.assertTrue(headers[0].startswith(f"===== {a} ") and headers[0].endswith("| via exa ====="), headers)
        self.assertTrue(headers[1].startswith(f"===== {b} ") and headers[1].endswith("| via tinyfish ====="), headers)
        ok = self.db().execute("SELECT url, chars FROM pages WHERE status='ok' ORDER BY url").fetchall()
        self.assertEqual(ok, [(a, len("the real page " * 40)), (b, len(stub))])

    def test_tinyfish_auth_failure_still_reads_via_exa(self):
        """Bug: a TinyFish 401 aborts the read before Exa is tried."""
        self.serve({"/tf-fetch": (401, {"error": "Invalid API key"}), "/exa/contents": (200, EXA_CONTENTS)})
        p = self.web("read", self.URL, "--no-archive")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("| via exa =====", p.stdout)
        self.assertIn("HTTP 401", p.stdout)


class Log(WebCase):
    def test_repeat_ok_reads_are_not_counted_as_retries(self):
        """Bug: reading a page twice (store hit, then --fresh) is reported as
        'ok after a failed attempt' though nothing failed."""
        db = self.db()
        rows = [("https://a.example/", "ok"), ("https://a.example/", "ok"),
                ("https://b.example/", "failed"), ("https://b.example/", "ok")]
        for i, (url, status) in enumerate(rows):
            db.execute("INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (time.time() + i, "t", "/", url, None, None, 10, status, None, None, "fetch"))
        p = self.web("log", "--lane", "t")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("2 distinct URLs read (2 ok, 0 failed, 1 ok after a failed attempt)", p.stdout)


def dossier(urls: list[str]) -> dict:
    claims = [{"claim": f"Claim number {i} about the subject, stated plainly for the test.",
               "kind": "fact", "confidence": "medium", "support": "x" * 400,
               "sources": [{"url": u, "readDepth": "page", "sourceType": "primary", "datum": "short"}]}
              for i, u in enumerate(urls, 1)]
    return {"slice": "CounterThesis", "status": "complete", "stoppedBecause": "done", "claims": claims}


class LaneScoping(WebCase):
    OLD = "https://old-run.example/page"
    NEW = "https://new-run.example/page"

    def make_run(self, files: dict[str, str]) -> str:
        run = os.path.join(self.home, "proj", "local", "research", "new-run-2026-10")
        os.makedirs(run)
        for name, text in files.items():
            with open(os.path.join(run, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        return run

    def add_page(self, db: sqlite3.Connection, lane: str, url: str, ts: float, chars: int = 5000) -> None:
        db.execute("INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (ts, lane, "/", url, None, "t", chars, "ok", None, None, "fetch"))

    def unfetched(self, out: str) -> list[str]:
        return [line.split()[2] for line in out.splitlines() if line.startswith("FAIL UNFETCHED_CITATION")]

    def test_scoped_lane_ignores_older_bare_lane_rows(self):
        """Bug: an older run's reads under the bare lane name count for this run."""
        db = self.db()
        run = self.make_run({"CounterThesis.json": json.dumps(dossier([self.OLD, self.NEW]))})
        self.add_page(db, "CounterThesis", self.OLD, time.time() - 3 * 86400)
        self.add_page(db, "new-run-2026-10/CounterThesis", self.NEW, time.time() + 5)
        p = self.web("check", os.path.join(run, "CounterThesis.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.unfetched(p.stdout), [self.OLD])
        self.assertIn("lane new-run-2026-10/CounterThesis", p.stdout)

    def test_bare_lane_counts_only_rows_since_the_run_started(self):
        """Bug: a bare lane name reused across runs counts every run's reads."""
        db = self.db()
        run = self.make_run({"CounterThesis.json": json.dumps(dossier([self.OLD, self.NEW]))})
        self.add_page(db, "CounterThesis", self.OLD, time.time() - 3 * 86400)
        self.add_page(db, "CounterThesis", self.NEW, time.time() + 5)
        p = self.web("check", os.path.join(run, "CounterThesis.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.unfetched(p.stdout), [self.OLD])

    def test_synthesis_url_read_only_by_an_older_run_is_flagged(self):
        """Bug: check of a run dir accepts a URL read by an older run's same-named lane."""
        db = self.db()
        run = self.make_run({"CounterThesis.json": json.dumps(dossier([self.NEW])),
                             "SYNTHESIS.md": f"# Answer\n\nOld [1], new [2].\n\n{self.OLD}\n{self.NEW}\n"})
        self.add_page(db, "CounterThesis", self.OLD, time.time() - 3 * 86400)
        self.add_page(db, "CounterThesis", self.NEW, time.time() + 5)
        p = self.web("check", run)
        self.assertEqual(p.returncode, 0, p.stderr)
        flagged = [line for line in p.stdout.splitlines() if line.startswith(("FAIL", "WARN"))]
        self.assertEqual(len(flagged), 1, p.stdout)
        self.assertTrue(flagged[0].startswith(f"WARN OTHER_RUN_URL {self.OLD}"), flagged)

    def test_dossier_with_no_reads_fails_its_citations(self):
        """Bug: a lane with no reads at all skips citation checks and passes with 0 FAIL."""
        self.db()
        run = self.make_run({"CounterThesis.json": json.dumps(dossier([self.OLD, self.NEW]))})
        p = self.web("check", os.path.join(run, "CounterThesis.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.unfetched(p.stdout), [self.OLD, self.NEW])

    def test_note_sources_must_be_one_url_per_number(self):
        """Bug: a Dig note passes with a Sources entry that has no URL, one URL
        under two numbers, and text after a URL."""
        db = self.db()
        run = self.make_run({"NOTE.md": "# Q\nDig · as of 2026-10-23 · new-run-2026-10\n"
                                        "A [1] B [2] C [3] D [4].\n## Sources\n"
                                        f"[1] A · {self.NEW}\n"
                                        f"[2] Same page again · {self.NEW}\n"
                                        "[3] Passage in [1], no link\n"
                                        f"[4] D · {self.NEW}/d (see section 2)\n"})
        self.add_page(db, "new-run-2026-10/dig", self.NEW, time.time() + 5)
        self.add_page(db, "new-run-2026-10/dig", self.NEW + "/d", time.time() + 5)
        p = self.web("check", run)
        fails = sorted(line.split()[1] + " " + line.split()[2]
                       for line in p.stdout.splitlines() if line.startswith("FAIL"))
        self.assertEqual(fails, ["DUPLICATE_SOURCE [2]", "NO_SOURCE_URL [3]", "TEXT_AFTER_URL [4]"], p.stdout)

    def test_citation_query_must_match_the_read(self):
        """Bug: a read of ?id=A passes a citation of ?id=B (queries dropped);
        tracking parameters alone must still match."""
        db = self.db()
        run = self.make_run({"NOTE.md": "# Q\nDig · as of 2026-10-23 · new-run-2026-10\n"
                                        "A [1] B [2].\n## Sources\n"
                                        "[1] A · https://q.example/view?id=B\n"
                                        "[2] B · https://q.example/doc?utm_source=x&id=7\n"})
        self.add_page(db, "new-run-2026-10/dig", "https://q.example/view?id=A", time.time() + 5)
        self.add_page(db, "new-run-2026-10/dig", "https://q.example/doc?id=7&fbclid=z", time.time() + 5)
        p = self.web("check", run)
        fails = [line for line in p.stdout.splitlines() if line.startswith("FAIL")]
        self.assertEqual(len(fails), 1, p.stdout)
        self.assertTrue(fails[0].startswith("FAIL UNFETCHED_URL https://q.example/view?id=B"), fails)


if __name__ == "__main__":
    unittest.main()
