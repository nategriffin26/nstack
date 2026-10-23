#!/usr/bin/env python3
"""web: search and read the web for research, with a ledger of what each lane read.

  web search "<query>" [--type T] [--site D,..] [--exclude D,..] [--after DATE] [--before DATE]
             [--recency day|week|month|year] [--limit N] [--deep] [--provider P] [--json]
  web read <url>... [--grep REGEX] [--context N] [--max-chars N] [--fresh] [--no-archive] [--json]
  web github <owner>/<repo> [<path>] [--ref R] [--tree] [--filter S] [--grep REGEX]
  web reddit <thread-url> [--sort top new ...]
  web check <run-dir | dossier.json | note.md>
  web digest <run-dir | dossier.json> [--claims A-B]
  web save <NOTE.md | SYNTHESIS.md | run-dir> [--title T] [--why W]
  web prior "<question>" [--limit N]
  web log [--since DATE]    web keys [--test]    web gc [--days N]    web mcp

Search asks Exa; when Exa fails it falls back to TinyFish, Brave, then Serper and
says which answered. Read serves a stored copy under a day old, else TinyFish,
then Exa, then the Wayback Machine. Every page read is saved under $WEB_HOME/pages and
logged per lane (--lane or WEB_LANE; a run's lanes are <run-slug>/<Lane>) in
$WEB_HOME/ledger.db, which check, digest and log read. $WEB_HOME defaults to
~/.omp/local/web. Keys come from the environment or ~/.omp/agent/keys.env.

Exit 75: transient (rate limit or outage); re-run the same command. Exit 1: fatal.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import http.client
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

WEB_HOME = os.path.expanduser(os.environ.get("WEB_HOME") or "~/.omp/local/web")
LEDGER_PATH = os.path.join(WEB_HOME, "ledger.db")
STORE_PATH = os.path.join(WEB_HOME, "pages")
KEYS_FILE = os.path.expanduser("~/.omp/agent/keys.env")
# Provider endpoints; the overrides let tests point them at a local server.
EXA_URL = os.environ.get("WEB_EXA_URL") or "https://api.exa.ai"
SEARCH_URL = os.environ.get("WEB_TINYFISH_SEARCH_URL") or "https://api.search.tinyfish.ai"
FETCH_URL = os.environ.get("WEB_TINYFISH_FETCH_URL") or "https://api.fetch.tinyfish.ai"
MAX_FETCH_URLS = 10
RETRY_STATUS = (500, 503, 504)
WINDOW = 60.0
EX_RETRYABLE = 75  # EX_TEMPFAIL
DEFAULT_MAX_CHARS = 12000
DEFAULT_GREP_CONTEXT = 400   # chars each side of a --grep match
MAX_GREP_WINDOWS = 12
DIGEST_SOFT_LIMIT = 45000   # paginate above this
DIGEST_HARD_LIMIT = 50000   # the harness elides output above this
MAX_SELECTORS = 20
SNIPPET_CHARS = 320         # keeps a 10-result search near 5k chars
STORE_MAX_AGE = 24 * 3600   # older stored copies are read again (prices, versions, thin reads)
THIN_CHARS = 200            # a TinyFish read this short is often a JS stub: Exa is asked too
THIN_PAGE_CHARS = 500       # check warns on a citation whose best read is shorter

# TinyFish's published per-key ceilings (30 searches, 150 fetched URLs a
# minute), minus one slot of slack for clock jitter between our window and theirs.
LIMITS = {"search": 29, "fetch": 145}
DEFAULT_MAX_WAIT = float(os.environ.get("WEB_MAX_WAIT") or "240")

# Lane identity for the durable log. main() overwrites LANE from --lane.
LANE = os.environ.get("WEB_LANE") or "unknown"
CWD = os.getcwd()


class Retryable(Exception):
    """Transient failure. Re-running the command will work."""


class RateLimited(Retryable):
    """Every pooled TinyFish key is at its per-minute ceiling."""


class Fatal(Exception):
    """Auth, validation, or unrecoverable API failure. Retrying will not help."""


class HTTPFailure(OSError):
    def __init__(self, code: int, detail: str):
        super().__init__(f"HTTP {code}: {detail}")
        self.code = code


def note(msg: str) -> None:
    print(f"[web] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- keys

def key_from_file(var: str) -> str:
    try:
        with open(KEYS_FILE, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(rf'\s*(?:export\s+)?{var}=["\']?([^"\'\s]*)', line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ""


def env_key(var: str) -> str:
    return (os.environ.get(var) or key_from_file(var)).strip()


def funded_key() -> str:
    """TinyFish's one key with wallet funds. Never pooled: omp's built-in
    web_search spends it outside this ledger."""
    key = env_key("TINYFISH_API_KEY")
    if not key:
        raise Fatal("No funded TinyFish key: set TINYFISH_API_KEY")
    return key


def load_keys() -> list[str]:
    """The free TinyFish pool. Limits are per key, so each key adds a full
    30 searches and 150 fetched URLs a minute."""
    keys: list[str] = []
    for k in re.split(r"[,\s]+", env_key("TINYFISH_API_KEYS")):
        if k and k not in keys:
            keys.append(k)
    if not keys:
        raise Fatal(f"No TinyFish pool: set TINYFISH_API_KEYS (comma-separated) in {KEYS_FILE}")
    return keys


def key_id(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:12]


# ----------------------------------------------------------------- urls

def canon_url(url: str) -> str:
    """Store identity: scheme, `www.`, fragment and trailing slash stripped,
    host lowercased. Query strings stay (Reddit sorts are distinct pages)."""
    u = re.sub(r"#.*$", "", (url or "").strip())
    m = re.match(r"^(?:[a-z][a-z0-9+.-]*://)?(?:www\.)?([^/?]+)(.*)$", u, re.I)
    if not m:
        return u
    return m.group(1).lower() + m.group(2).rstrip("/")


_TRACKING = re.compile(r"^(utm_\w+|fbclid|gclid|dclid|gbraid|wbraid|msclkid|yclid|mc_cid|mc_eid|"
                       r"igshid|ref|ref_src|ref_url)$", re.I)


def cite_key(url: str) -> str:
    """Citation identity for `check`: canon_url without tracking parameters,
    plus the equivalences a worker legitimately blurs: arxiv abs/pdf/html
    (version and .pdf dropped), GitHub blob/raw across refs, Hugging Face
    blob/raw/resolve."""
    k = canon_url(url)
    if "?" in k:
        base, query = k.split("?", 1)
        keep = [p for p in query.split("&") if p and not _TRACKING.match(p.split("=", 1)[0])]
        k = base.rstrip("/") + ("?" + "&".join(keep) if keep else "")
    m = re.match(r"^arxiv\.org/(?:abs|pdf|html)/([0-9.]+?)(?:v\d+)?(?:\.pdf)?$", k)
    if m:
        return f"arxiv:{m.group(1)}"
    m = re.match(r"^github\.com/([^/]+)/([^/]+)/(?:blob|raw)/[^/]+/(.+)$", k)
    if m:
        return f"github:{m.group(1)}/{m.group(2)}/{m.group(3)}"
    m = re.match(r"^raw\.githubusercontent\.com/([^/]+)/([^/]+)/(?:refs/heads/)?[^/]+/(.+)$", k)
    if m:
        return f"github:{m.group(1)}/{m.group(2)}/{m.group(3)}"
    m = re.match(r"^huggingface\.co/([^/]+/[^/]+)/(?:blob|raw|resolve)/[^/]+/(.+)$", k)
    if m:
        return f"hf:{m.group(1)}/{m.group(2)}"
    return k


def store_paths(url: str, fmt: str = "markdown") -> tuple[str, str]:
    h = hashlib.sha1(canon_url(url).encode()).hexdigest()[:16]
    ext = {"markdown": "md", "html": "html", "json": "json"}.get(fmt, "md")
    return os.path.join(STORE_PATH, f"{h}.{ext}"), os.path.join(STORE_PATH, f"{h}.meta.json")


# -------------------------------------------------------------- ledger

SCHEMA = (
    "CREATE TABLE IF NOT EXISTS calls(surface TEXT, kid TEXT, ts REAL, cost INTEGER)",
    "CREATE INDEX IF NOT EXISTS calls_idx ON calls(surface, ts)",
    "CREATE TABLE IF NOT EXISTS blocks(surface TEXT, kid TEXT, until REAL, PRIMARY KEY(surface, kid))",
    # Durable record of what was read, never pruned by the rate window.
    "CREATE TABLE IF NOT EXISTS pages(ts REAL, lane TEXT, cwd TEXT, url TEXT, final_url TEXT, "
    "title TEXT, chars INTEGER, status TEXT, error TEXT, path TEXT, surface TEXT)",
    "CREATE INDEX IF NOT EXISTS pages_idx ON pages(lane, ts)",
    "CREATE TABLE IF NOT EXISTS queries(ts REAL, lane TEXT, cwd TEXT, query TEXT, params TEXT, "
    "provider TEXT, n INTEGER)",
    "CREATE INDEX IF NOT EXISTS queries_idx ON queries(lane, ts)",
)


class Ledger:
    """Cross-process token bucket for the TinyFish pool over one SQLite file,
    plus the durable per-lane record of pages read and searches run."""

    def __init__(self, path: str = LEDGER_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # Concurrent first-run processes race on WAL conversion and DDL; SQLite
        # returns SQLITE_BUSY for those regardless of busy_timeout.
        for attempt in range(20):
            try:
                db = sqlite3.connect(path, timeout=30, isolation_level=None)
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA busy_timeout=30000")
                if db.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
                    db.execute("PRAGMA journal_mode=WAL")
                for ddl in SCHEMA:
                    db.execute(ddl)
                self.db = db
                return
            except sqlite3.OperationalError:
                time.sleep(0.05 + 0.05 * attempt)
        raise Fatal(f"ledger unavailable at {path}")

    def _snapshot(self, surface: str, now: float) -> tuple[dict, dict, dict]:
        self.db.execute("DELETE FROM calls WHERE ts < ?", (now - WINDOW,))
        self.db.execute("DELETE FROM blocks WHERE until <= ?", (now,))
        load = {r[0]: r[1] for r in self.db.execute(
            "SELECT kid, SUM(cost) FROM calls WHERE surface=? GROUP BY kid", (surface,))}
        blocked = {r[0]: r[1] for r in self.db.execute(
            "SELECT kid, until FROM blocks WHERE surface=?", (surface,))}
        oldest = {r[0]: r[1] for r in self.db.execute(
            "SELECT kid, MIN(ts) FROM calls WHERE surface=? GROUP BY kid", (surface,))}
        return load, blocked, oldest

    def acquire(self, surface: str, keys: list[str], cost: int, max_wait: float) -> str:
        """Reserve `cost` units on the least-loaded healthy key, waiting if the
        whole pool is saturated. Raises RateLimited rather than dropping work."""
        limit = LIMITS[surface]
        if cost > limit:
            raise Fatal(f"{surface} request of {cost} units exceeds the "
                        f"{limit}/min per-key ceiling")
        start = time.time()
        announced = False
        while True:
            now = time.time()
            self.db.execute("BEGIN IMMEDIATE")
            try:
                load, blocked, oldest = self._snapshot(surface, now)
                free = [k for k in keys if key_id(k) not in blocked]
                best = min(free, key=lambda k: load.get(key_id(k), 0)) if free else None
                if best is not None and load.get(key_id(best), 0) + cost <= limit:
                    self.db.execute("INSERT INTO calls VALUES (?,?,?,?)",
                                    (surface, key_id(best), now, cost))
                    self.db.execute("COMMIT")
                    if announced:
                        note(f"{surface} capacity acquired after {now - start:.0f}s")
                    return best
                waits = [oldest[key_id(k)] + WINDOW - now
                         for k in free if key_id(k) in oldest]
                waits += [u - now for u in blocked.values()]
                self.db.execute("COMMIT")
            except sqlite3.Error:
                self.db.execute("ROLLBACK")
                raise
            if time.time() - start >= max_wait:
                raise RateLimited(
                    f"no TinyFish {surface} capacity across {len(keys)} keys after "
                    f"{max_wait:.0f}s of waiting")
            if not announced:
                note(f"all {len(keys)} TinyFish keys at the {limit}/min {surface} limit; "
                     f"waiting up to {max_wait:.0f}s for a slot")
                announced = True
            time.sleep(min(max(min(waits) if waits else 1.0, 0.25), 5.0))

    def penalize(self, surface: str, key: str, retry_after: float) -> None:
        self.db.execute("INSERT OR REPLACE INTO blocks VALUES (?,?,?)",
                        (surface, key_id(key), time.time() + max(retry_after, 5.0)))

    def report(self, keys: list[str]) -> None:
        now = time.time()
        for surface in ("search", "fetch"):
            self.db.execute("BEGIN IMMEDIATE")
            load, blocked, _ = self._snapshot(surface, now)
            self.db.execute("COMMIT")
            print(f"tinyfish {surface} (limit {LIMITS[surface]}/min per key):")
            for k in keys:
                kid = key_id(k)
                state = f"blocked {blocked[kid] - now:.0f}s" if kid in blocked else "ok"
                print(f"  {kid} …{k[-6:]}  used {load.get(kid, 0):>4}  {state}")

    # -- durable record -------------------------------------------------

    def record_page(self, *, url: str, final_url: str | None, title: str | None,
                    chars: int, status: str, error: str | None, path: str | None,
                    surface: str) -> None:
        self.db.execute("INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (time.time(), LANE, CWD, url, final_url, title, chars,
                         status, error, path, surface))

    def record_query(self, query: str, params: dict, provider: str, n: int) -> None:
        self.db.execute("INSERT INTO queries VALUES (?,?,?,?,?,?,?)",
                        (time.time(), LANE, CWD, query, json.dumps(params, sort_keys=True),
                         provider, n))

    def _rows(self, table: str, lane: str | None, since: float | None) -> list[sqlite3.Row]:
        where, args = [], []
        if lane is not None:
            where.append("lane=?")
            args.append(lane)
        if since is not None:
            where.append("ts>=?")
            args.append(since)
        sql = f"SELECT * FROM {table}" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY ts"
        return list(self.db.execute(sql, args))

    def pages(self, lane: str | None = None, since: float | None = None) -> list[sqlite3.Row]:
        return self._rows("pages", lane, since)

    def queries(self, lane: str | None = None, since: float | None = None) -> list[sqlite3.Row]:
        return self._rows("queries", lane, since)

    def counts(self) -> dict[str, int]:
        return {t: self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("calls", "blocks", "pages", "queries")}

    def gc(self, cutoff: float) -> tuple[int, int]:
        p = self.db.execute("DELETE FROM pages WHERE ts < ?", (cutoff,)).rowcount
        q = self.db.execute("DELETE FROM queries WHERE ts < ?", (cutoff,)).rowcount
        return p, q


LEDGER = Ledger()


def distinct_pages(rows: list[sqlite3.Row]) -> list[dict]:
    """One entry per distinct canonical URL, in first-seen order. An `ok`
    row wins over failures; the latest ok row supplies chars and path."""
    out: dict[str, dict] = {}
    for r in rows:
        k = canon_url(r["url"] or "")
        d = out.get(k)
        if d is None:
            d = out[k] = {"key": k, "url": r["url"], "final_url": r["final_url"],
                          "status": "failed", "chars": 0, "path": None, "error": None,
                          "surface": r["surface"], "lane": r["lane"], "ts": r["ts"],
                          "reads": 0, "failures": 0}
        d["reads"] += 1
        d["failures"] += r["status"] != "ok"
        if r["status"] == "ok":
            d.update(status="ok", chars=r["chars"], path=r["path"], error=None,
                     final_url=r["final_url"] or d["final_url"], surface=r["surface"])
        elif d["status"] != "ok":
            d["error"] = r["error"]
    return list(out.values())


# ------------------------------------------------------------ run scope
#
# Lane names recur across runs (CounterThesis, VerifyA), so a run's rows are
# the ones under <run-slug>/<Lane>, else under the bare <Lane> at or after the
# run dir's first file.

def run_dir_of(path: str) -> str:
    d = os.path.dirname(os.path.abspath(path))
    return os.path.dirname(d) if os.path.basename(d) == "verify" else d


@functools.lru_cache(maxsize=None)
def run_of(run_dir: str) -> tuple[str, float]:
    """(run slug, start): the dir's name and its earliest file time."""
    times = []
    for root, dirs, names in os.walk(run_dir):
        for n in [""] + dirs + names:
            try:
                st = os.stat(os.path.join(root, n))
            except OSError:
                continue
            times.append(min(getattr(st, "st_birthtime", st.st_mtime), st.st_mtime))
    return os.path.basename(os.path.normpath(run_dir)), min(times) if times else 0.0


def resolve_lane(cands: list[str], run: tuple[str, float] | None,
                 explicit: str | None = None) -> tuple[str, float | None]:
    """(lane, since) for the first candidate with page rows. A lane given with
    --lane counts whole; others try <slug>/<lane>, then the bare lane from the
    run's start."""
    for c in cands:
        options = [(c, None)] if c == explicit or not run else [(f"{run[0]}/{c}", None), (c, run[1])]
        for lane, since in options:
            if LEDGER.pages(lane, since):
                return lane, since
    if explicit:
        return explicit, None
    c = cands[0] if cands else "unknown"
    return (f"{run[0]}/{c}", None) if run else (c, None)


# ----------------------------------------------------------------- store

def _replace(path: str, write) -> None:
    """Write via a temp file and rename, so readers never see a partial file."""
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        write(fh)
    os.replace(tmp, path)


def store_page(r: dict, text: str, fmt: str, surface: str, plain: bool) -> str:
    """Write the full page text and its metadata to the store. Overwrites.
    `plain`: a whole-page markdown read, the only kind later served from store."""
    os.makedirs(STORE_PATH, exist_ok=True)
    url = r.get("url") or r.get("final_url") or ""
    path, meta = store_paths(url, fmt)
    _replace(path, lambda fh: fh.write(text))
    _replace(meta, lambda fh: json.dump(
        {"url": url, "final_url": r.get("final_url"), "title": r.get("title"),
         "published_date": r.get("published_date"), "chars": len(text),
         "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "archived_at": r.get("archivedAt"), "route": r.get("route"), "plain": plain,
         "lane": LANE, "surface": surface}, fh, indent=1))
    return path


def stored_page(url: str) -> dict | None:
    """The store's plain markdown copy of a URL as a read result, or None when
    it is missing, older than STORE_MAX_AGE, or a selector/format-shaped read."""
    path, meta = store_paths(url)
    try:
        if time.time() - os.path.getmtime(path) > STORE_MAX_AGE:
            return None
        with open(meta, encoding="utf-8") as fh:
            m = json.load(fh)
        if m.get("plain") is not True:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except (OSError, ValueError, AttributeError):
        return None
    if not text.strip():
        return None
    return {"url": url, "final_url": m.get("final_url"), "title": m.get("title"), "text": text,
            "storePath": path, "route": "store", "storedAt": m.get("fetched_at"),
            "archivedAt": m.get("archived_at")}


_TEXT_CACHE: dict[str, str | None] = {}
_PATH_INDEX: dict[str, str] | None = None


def _read_cached(path: str) -> str | None:
    if path not in _TEXT_CACHE:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                _TEXT_CACHE[path] = fh.read()
        except OSError:
            _TEXT_CACHE[path] = None
    return _TEXT_CACHE[path]


def stored_text(url: str) -> tuple[str | None, str | None]:
    """(text, path) for a URL: the store file at the URL's hash, else the
    latest ok log row (any lane) whose url or final_url has the same
    citation identity, so arxiv abs/pdf and redirect targets resolve."""
    global _PATH_INDEX
    for fmt in ("markdown", "html", "json"):
        path = store_paths(url, fmt)[0]
        text = _read_cached(path)
        if text is not None:
            return text, path
    if _PATH_INDEX is None:
        _PATH_INDEX = {}
        for row in LEDGER.db.execute(
                "SELECT url, final_url, path FROM pages WHERE status='ok' AND path IS NOT NULL ORDER BY ts"):
            for u in (row["url"], row["final_url"]):
                if u:
                    _PATH_INDEX[cite_key(u)] = row["path"]  # latest wins
    path = _PATH_INDEX.get(cite_key(url))
    if path:
        text = _read_cached(path)
        if text is not None:
            return text, path
    return None, None


# ------------------------------------------------------------- transport

def request(url: str, *, surface: str, keys: list[str], max_wait: float,
            cost: int = 1, body: dict | None = None, timeout: int = 180,
            retries: int = 5) -> dict:
    """One TinyFish call through the pooled-key rate gate."""
    data = json.dumps(body).encode() if body is not None else None
    delay = 2.0
    rate_limited = 0
    for attempt in range(retries + 1):
        key = LEDGER.acquire(surface, keys, cost, max_wait)
        headers = {"X-API-Key": key, "Accept": "application/json"}
        if data:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:  # URLError subclass: must stay first
            detail = exc.read().decode(errors="replace")[:400]
            if exc.code == 429:
                rate_limited += 1
                retry_after = float(exc.headers.get("Retry-After") or WINDOW)
                LEDGER.penalize(surface, key, retry_after)
                note(f"tinyfish key …{key[-6:]} returned 429; parked {retry_after:.0f}s")
                continue  # acquire() picks another key or waits it out
            if exc.code in RETRY_STATUS and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            if exc.code in RETRY_STATUS:
                raise Retryable(f"tinyfish {surface} HTTP {exc.code}: {detail}")
            raise Fatal(f"tinyfish {surface} HTTP {exc.code}: {detail}")
        except (OSError, http.client.HTTPException, ValueError) as exc:
            # URLError, socket timeouts, resets, a truncated body: all transient.
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise Retryable(f"tinyfish {surface} transport failure: {exc}")
    if rate_limited:
        raise RateLimited(f"every TinyFish key rate limited for {surface} across "
                          f"{rate_limited} attempts")
    raise Retryable(f"tinyfish {surface} failed after retries")


def _json_call(url: str, headers: dict, body: dict | None = None,
               timeout: int = 60) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {**headers, "Accept": "application/json", "User-Agent": "web"}
    if data:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:   # providers wrap the reason in {"error": "..."} or {"error": {"message": ...}}
            err = json.loads(detail).get("error")
            detail = err.get("message") if isinstance(err, dict) else err if isinstance(err, str) else detail
        except (ValueError, AttributeError):
            pass
        raise HTTPFailure(exc.code, str(detail)[:200])


def exa_call(path: str, body: dict, key: str, timeout: int = 60) -> dict:
    """POST to Exa; a 429 gets two short retries."""
    for attempt in range(3):
        try:
            return _json_call(EXA_URL + path, {"x-api-key": key}, body, timeout)
        except HTTPFailure as exc:
            if exc.code != 429 or attempt == 2:
                raise
            time.sleep(1 + attempt)
    raise AssertionError("unreachable")


def _host(url: str) -> str:
    return re.sub(r"^www\.", "", urllib.parse.urlsplit(url).hostname or "")


def _clip(text: str, n: int = SNIPPET_CHARS) -> str:
    text = re.sub(r"<[^>]+>|[#*`]+|\s+", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------------------------------------------------------- search

TYPES = {"paper": "research paper", "news": "news", "github": "github", "pdf": "pdf",
         "company": "company", "people": "people", "financial": "financial report"}
INDEX_TYPES = ("company", "people")   # Exa's dedicated indices: no date or exclude filters
RECENCY_DAYS = {"day": 1, "week": 7, "month": 31, "year": 366}
PROVIDERS = ("exa", "tinyfish", "brave", "serper")
PROVIDER_KEYS = {"exa": "EXA_API_KEY", "tinyfish": "TINYFISH_API_KEYS",
                 "brave": "BRAVE_API_KEY", "serper": "SERPER_API_KEY"}


def parse_date(s: str, flag: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise Fatal(f"{flag} expects YYYY-MM-DD, got {s!r}")


def _domains(s: str | None) -> list[str]:
    return [d.strip() for d in (s or "").split(",") if d.strip()]


def search_window(a: argparse.Namespace) -> tuple[datetime | None, datetime | None]:
    """Validated [lo, hi] publication window from --after/--before/--recency."""
    if a.recency and a.after:
        raise Fatal("--recency and --after both set the start date; pass one")
    if not 1 <= a.limit <= 100:
        raise Fatal(f"--limit takes 1-100, got {a.limit}")
    if a.type in INDEX_TYPES and (a.after or a.before or a.recency or a.exclude):
        raise Fatal(f"--type {a.type} searches a dedicated index that takes no "
                    f"--after, --before, --recency or --exclude")
    lo = parse_date(a.after, "--after") if a.after else None
    if a.recency:
        lo = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS[a.recency])
    hi = parse_date(a.before, "--before") if a.before else None
    if lo and hi and lo > hi:
        raise Fatal("the start date is after --before")
    return lo, hi


def _site_query(a: argparse.Namespace) -> str:
    """--site/--exclude as query operators, for engines without a filter."""
    return (a.query + "".join(f" site:{d}" for d in _domains(a.site))
            + "".join(f" -site:{d}" for d in _domains(a.exclude)))


def exa_search(a: argparse.Namespace, lo, hi, key: str) -> list[dict]:
    body: dict = {"query": a.query, "type": "deep" if a.deep else "lite",
                  "numResults": a.limit, "contents": {"highlights": True}}
    if a.type:
        body["category"] = TYPES[a.type]
    if a.site:
        body["includeDomains"] = _domains(a.site)
    if a.exclude:
        body["excludeDomains"] = _domains(a.exclude)
    if lo:
        body["startPublishedDate"] = lo.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    if hi:
        body["endPublishedDate"] = hi.strftime("%Y-%m-%dT23:59:59.999Z")
    out = []
    for r in exa_call("/search", body, key, timeout=120).get("results") or []:
        url = r.get("url") or ""
        highlights = [h for h in r.get("highlights") or [] if isinstance(h, str)]
        row = {"title": r.get("title") or "", "url": url, "site_name": _host(url),
               "snippet": _clip(" ".join(highlights)), "highlights": highlights}
        if r.get("publishedDate"):
            row["date"] = r["publishedDate"][:10]
        if r.get("author"):
            row["author"] = r["author"]
        out.append(row)
    return out


def tinyfish_search(a: argparse.Namespace, lo, hi, fallback: bool) -> list[dict]:
    """TinyFish pages of ~10. As a fallback it waits seconds, not minutes, for
    pool capacity so the next provider can answer instead."""
    keys = load_keys()
    base = {"query": a.query}
    site = a.site or ("github.com" if a.type == "github" else None)
    if site:
        base["include_domains"] = ",".join(_domains(site))
    if a.exclude:
        base["exclude_domains"] = ",".join(_domains(a.exclude))
    kind = {"news": "news", "paper": "research_paper"}.get(a.type or "")
    if kind:
        base["domain_type"] = kind
    if lo:
        base["after_date"] = lo.strftime("%Y-%m-%d")
    if hi:
        base["before_date"] = hi.strftime("%Y-%m-%d")
    rows: list[dict] = []
    seen: set[str] = set()
    for page in range((a.limit + 9) // 10):
        params = dict(base)
        if page:
            params["page"] = str(page)
        try:
            payload = request(f"{SEARCH_URL}?{urllib.parse.urlencode(params)}", surface="search",
                              keys=keys, max_wait=5 if fallback else a.max_wait, timeout=90,
                              retries=1 if fallback else 5)
        except Retryable as exc:
            if page == 0:
                raise
            note(f"tinyfish page {page} unavailable ({exc}); returning {len(rows)} results")
            break
        got = payload.get("results") or []
        for r in got:
            k = re.sub(r"^https?://(www\.)?|/$", "", (r.get("url") or "").strip())
            if k and k not in seen:
                seen.add(k)
                rows.append(r)
        if not got or len(rows) >= a.limit:
            break
    return rows[: a.limit]


def brave_search(a: argparse.Namespace, lo, hi, key: str) -> list[dict]:
    news = a.type == "news"
    params: dict = {"q": _site_query(a), "count": min(a.limit, 20)}
    if lo or hi:
        params["freshness"] = (f"{lo or datetime(1970, 1, 1):%Y-%m-%d}"
                               f"to{hi or datetime.now(timezone.utc):%Y-%m-%d}")
    data = _json_call("https://api.search.brave.com/res/v1/"
                      f"{'news' if news else 'web'}/search?{urllib.parse.urlencode(params)}",
                      {"X-Subscription-Token": key})
    rows = data.get("results") if news else (data.get("web") or {}).get("results")
    out = []
    for r in rows or []:
        url = r.get("url") or ""
        row = {"title": r.get("title") or "", "url": url, "site_name": _host(url),
               "snippet": _clip(r.get("description") or "")}
        if r.get("page_age"):
            row["date"] = r["page_age"][:10]
        out.append(row)
    return out[: a.limit]


def serper_search(a: argparse.Namespace, lo, hi, key: str) -> list[dict]:
    endpoint = {"news": "news", "paper": "scholar"}.get(a.type or "", "search")
    body: dict = {"q": _site_query(a), "num": max(10, a.limit)}
    if endpoint == "scholar":
        if lo:
            body["as_ylo"] = lo.year
        if hi:
            body["as_yhi"] = hi.year
    elif lo or hi:
        body["tbs"] = ("cdr:1" + (f",cd_min:{lo:%m/%d/%Y}" if lo else "")
                       + (f",cd_max:{hi:%m/%d/%Y}" if hi else ""))
    data = _json_call(f"https://google.serper.dev/{endpoint}", {"X-API-KEY": key}, body)
    out = []
    for r in data.get("organic") or data.get("news") or []:
        url = r.get("link") or ""
        row = {"title": r.get("title") or "", "url": url, "site_name": _host(url),
               "snippet": _clip(r.get("snippet") or "")}
        for src, dst in (("date", "date"), ("year", "year"), ("citedBy", "cited_by_count"),
                         ("pdfUrl", "pdf_url"), ("publicationInfo", "venue")):
            if r.get(src):
                row[dst] = r[src]
        out.append(row)
    return out[: a.limit]


def provider_search(name: str, a: argparse.Namespace, lo, hi, fallback: bool) -> list[dict]:
    if name == "tinyfish":
        return tinyfish_search(a, lo, hi, fallback)
    key = env_key(PROVIDER_KEYS[name])
    if not key:
        raise Fatal(f"{name}: {PROVIDER_KEYS[name]} is not set")
    return {"exa": exa_search, "brave": brave_search, "serper": serper_search}[name](a, lo, hi, key)


def _transient(exc: Exception) -> bool:
    if isinstance(exc, HTTPFailure):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, (Retryable, OSError, http.client.HTTPException, ValueError))


def run_search(a: argparse.Namespace) -> int:
    lo, hi = search_window(a)
    failures: list[str] = []
    transient = False
    for name in [a.provider] if a.provider else PROVIDERS:
        try:
            rows = provider_search(name, a, lo, hi, fallback=bool(failures))
        except (Fatal, Retryable, OSError, ValueError, http.client.HTTPException) as exc:
            transient |= _transient(exc)
            failures.append(f"{name} failed: {_clip(str(exc), 100)}")
            continue
        break
    else:
        raise (Retryable if transient else Fatal)("search failed: " + "; ".join(failures))
    logged = {k: v for k, v in (("type", a.type), ("site", a.site), ("exclude", a.exclude),
                                ("after", a.after), ("before", a.before), ("recency", a.recency),
                                ("deep", a.deep), ("limit", a.limit)) if v}
    LEDGER.record_query(a.query, logged, name, len(rows))
    via = name + (f" ({'; '.join(failures)})" if failures else "")
    if a.json:
        json.dump({"query": a.query, "count": len(rows), "provider": name, "providers": [name],
                   "failed": failures, "results": rows}, sys.stdout, indent=1)
        print()
        return 0
    print(f'{len(rows) or "No"} results for "{a.query}" · via {via}')
    for i, r in enumerate(rows, 1):
        url = r.get("url") or ""
        head = [r.get("title") or "(untitled)", r.get("site_name") or _host(url),
                r.get("date") or r.get("year")]
        print(f"\n[{i}] {' · '.join(str(x) for x in head if x)}\n    {url}")
        if r.get("pdf_url") and r["pdf_url"] != url:
            print(f"    pdf: {r['pdf_url']}")
        snippet = _clip(r.get("snippet") or "")
        if snippet:
            print(f"    {snippet}")
    return 0


# ------------------------------------------------------------------ read

def validate_selectors(a: argparse.Namespace) -> None:
    """Reject what the API would reject, before spending a request on it."""
    for attr in ("include_selector", "exclude_selector"):
        values = getattr(a, attr, None) or []
        flag = "--" + attr.replace("_", "-")
        if len(values) > MAX_SELECTORS:
            raise Fatal(f"{flag}: at most {MAX_SELECTORS} selectors, got {len(values)}")
        for v in values:
            if not v or not v.strip():
                raise Fatal(f"{flag}: empty selector")


def fetch_urls(urls: list[str], a: argparse.Namespace) -> tuple[dict, list[str]]:
    """TinyFish Fetch in batches. Returns (payload, unretrieved_urls): a batch
    that fails transiently is reported, never silently dropped. Every URL ends
    up in results (with text) or errors, so the caller's fallbacks see it: an
    empty, null or missing result and a TinyFish failure (auth, no pool) are
    errors, not reads."""
    validate_selectors(a)
    try:
        keys = load_keys()
        down = None
    except Fatal as exc:
        keys, down = [], str(exc)
    merged: dict = {"results": [], "errors": []}
    pending: list[str] = []
    for i in range(0, len(urls), MAX_FETCH_URLS):
        chunk = urls[i:i + MAX_FETCH_URLS]
        body: dict = {"urls": chunk, "format": a.format}
        if getattr(a, "fresh", False):
            body["ttl"] = 0
        if a.include_selector:
            body["include_selectors"] = a.include_selector
        if a.exclude_selector:
            body["exclude_selectors"] = a.exclude_selector
        try:
            if down:
                raise Fatal(down)
            payload = request(FETCH_URL, surface="fetch", keys=keys,
                              max_wait=a.max_wait, cost=len(chunk), body=body,
                              timeout=240)
        except Retryable as exc:
            note(f"tinyfish: {len(chunk)} URLs deferred: {exc}")
            merged["deferredCause"] = ("rate limit" if isinstance(exc, RateLimited)
                                       and merged.get("deferredCause") != "outage/transport"
                                       else "outage/transport")
            pending.extend(chunk)
            continue
        except Fatal as exc:
            merged["errors"] += [{"url": u, "error": f"tinyfish failed: {exc}", "status": None}
                                 for u in chunk]
            continue
        answered: set[str] = set()
        for r in payload.get("results") or []:
            url = r.get("url") or r.get("final_url") or ""
            answered.add(canon_url(url))
            text = r.get("text")
            if text is None or (isinstance(text, str) and not text.strip()):
                merged["errors"].append({"url": url, "error": "empty_content", "status": None})
                continue
            r["route"] = "tinyfish"
            merged["results"].append(r)
        for e in payload.get("errors") or []:
            answered.add(canon_url(e.get("url") or ""))
            merged["errors"].append(e)
        merged["errors"] += [{"url": u, "error": "missing from tinyfish response", "status": None}
                             for u in chunk if canon_url(u) not in answered]
    return merged, pending


def exa_read(urls: list[str], fresh: bool) -> dict[str, dict]:
    """Exa /contents for URLs TinyFish could not read: {requested url: result}."""
    key = env_key("EXA_API_KEY")
    if not key or not urls:
        return {}
    body: dict = {"urls": urls, "text": True}
    if fresh:
        body["maxAgeHours"] = 0
    try:
        data = exa_call("/contents", body, key, timeout=120)
    except (OSError, ValueError, http.client.HTTPException) as exc:
        note(f"exa read failed: {exc}")
        return {}
    by_canon = {canon_url(u): u for u in urls}
    out: dict[str, dict] = {}
    for r in data.get("results") or []:
        text = r.get("text") if isinstance(r.get("text"), str) else ""
        orig = by_canon.get(canon_url(r.get("id") or "")) or by_canon.get(canon_url(r.get("url") or ""))
        if orig and text.strip():
            out[orig] = {"url": orig, "final_url": r.get("url"), "title": r.get("title"),
                         "published_date": r.get("publishedDate"), "text": text, "route": "exa"}
    return out


def page_text(r: dict) -> str:
    text = r.get("text")
    return text if isinstance(text, str) else json.dumps(text, indent=1)


def print_header(r: dict, chars: int, path: str) -> None:
    url = r.get("url") or r.get("final_url") or ""
    if r.get("final_url") and canon_url(r["final_url"]) != canon_url(url):
        url += f" -> {r['final_url']}"
    route = r.get("route") or "tinyfish"
    if route == "store" and r.get("storedAt"):
        route += f" {r['storedAt'][:10]}"
    print(f"\n===== {url} | {r.get('title') or '(untitled)'} | {chars} chars | saved {path} "
          f"| via {route} =====")
    if r.get("archivedAt"):
        print(f"[Wayback snapshot {_wb_date(r['archivedAt'])}: the live page failed; "
              f"cite the original URL and note the archived read in toolHealth]")
    if r.get("unmatched_selectors"):
        print(f"[unmatched selectors: {r['unmatched_selectors']}]")


def print_page(r: dict, text: str, path: str, max_chars: int) -> bool:
    """Header + preview. Returns True when the preview was truncated."""
    full = len(text)
    truncated = False
    if max_chars and full > max_chars:
        text = (text[:max_chars]
                + f"\n…[truncated {full - max_chars} of {full} chars; full text at {path}: "
                  f"grep it or read {path}:<start>-<end>]")
        truncated = True
    print_header(r, full, path)
    print(text)
    return truncated


def print_matches(r: dict, text: str, path: str, pattern: re.Pattern, context: int) -> int:
    """Header + windows around each --grep match instead of the preview, each
    labelled with the store line so `read path:line` lands on it. Returns the
    number of windows found."""
    print_header(r, len(text), path)
    spans: list[list[int]] = []
    for m in pattern.finditer(text):
        lo, hi = max(0, m.start() - context), min(len(text), m.end() + context)
        if spans and lo <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], hi)
        else:
            spans.append([lo, hi])
    if not spans:
        print(f"[no match for /{pattern.pattern}/ in {len(text)} chars; full text at {path}]")
        return 0
    for lo, hi in spans[:MAX_GREP_WINDOWS]:
        print(f"--- {path}:{text.count(chr(10), 0, lo) + 1} (chars {lo}-{hi}) ---")
        print(text[lo:hi].strip())
    if len(spans) > MAX_GREP_WINDOWS:
        print(f"…[{len(spans) - MAX_GREP_WINDOWS} more match windows; grep {path}]")
    return len(spans)


def compile_grep(patterns: list[str] | None) -> re.Pattern | None:
    if not patterns:
        return None
    try:
        return re.compile(patterns[0] if len(patterns) == 1
                          else "|".join(f"(?:{p})" for p in patterns), re.I)
    except re.error as exc:
        raise Fatal(f"--grep: invalid regex: {exc}")


def _wb_date(ts: str) -> str:
    ts = str(ts or "")
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ts or "?"


ARCHIVE_STATUSES = {401, 403, 404, 410, 429, 500, 502, 503, 504}
_ARCHIVE_ERRORS = re.compile(r"empty_content|target_unreachable|not_found|forbidden|blocked|timeout|"
                             r"access_denied|unavailable|missing", re.I)


def wayback_recover(errors: list[dict], a: argparse.Namespace) -> list[dict]:
    """For URLs nothing else could read, fetch the closest Wayback Machine
    snapshot (raw `id_` form, no toolbar) through TinyFish. The recovered row
    keeps the ORIGINAL url (final_url = snapshot), so the store, the log and
    `check` all resolve on the URL the worker cites; the failure row stays."""
    recovered: list[dict] = []
    for e in errors:
        url = e.get("url") or ""
        if not url or not (e.get("status") in ARCHIVE_STATUSES
                           or _ARCHIVE_ERRORS.search(str(e.get("error") or ""))):
            continue
        try:
            avail = _json_call("https://archive.org/wayback/available?url="
                               + urllib.parse.quote(url, safe=""), {}, timeout=20)
        except (OSError, ValueError, http.client.HTTPException) as exc:
            note(f"wayback: availability lookup failed for {url}: {exc}")
            continue
        closest = (avail.get("archived_snapshots") or {}).get("closest") or {}
        snap = closest.get("url") if closest.get("available") else None
        if not snap:
            note(f"wayback: no snapshot of {url}")
            continue
        snap = re.sub(r"^http://", "https://", snap)
        snap = re.sub(r"(/web/\d+)/", r"\1id_/", snap, count=1)
        try:
            payload = request(FETCH_URL, surface="fetch", keys=load_keys(), max_wait=a.max_wait,
                              cost=1, body={"urls": [snap], "format": a.format}, timeout=240)
        except (Retryable, Fatal) as exc:
            note(f"wayback: snapshot read deferred for {url}: {exc}")
            continue
        rows = payload.get("results") or []
        if not rows or not page_text(rows[0]).strip():
            note(f"wayback: snapshot of {url} came back empty")
            continue
        r = rows[0]
        r.update(url=url, final_url=snap, archivedAt=closest.get("timestamp"), route="wayback")
        e["recovered"] = "wayback"
        recovered.append(r)
    return recovered


def emit_fetch(payload: dict, pending: list[str], a: argparse.Namespace,
               surface: str = "fetch") -> int:
    results = payload.get("results", [])
    errors = payload.get("errors", [])
    fmt = getattr(a, "format", "markdown")
    plain = fmt == "markdown" and not (getattr(a, "include_selector", None)
                                       or getattr(a, "exclude_selector", None))
    texts: list[str] = []
    for r in results:
        text = page_text(r)
        texts.append(text)
        if r.get("route") != "store":
            r["storePath"] = store_page(r, text, fmt, surface, plain)
        LEDGER.record_page(url=r.get("url") or r.get("final_url") or "",
                           final_url=r.get("final_url"), title=r.get("title"),
                           chars=len(text), status="ok", error=None,
                           path=r["storePath"], surface=surface)
    for e in errors:
        err = f"{e.get('error')} status={e.get('status')}"
        if e.get("recovered"):
            err += f"; read via {e['recovered']}"
        LEDGER.record_page(url=e.get("url") or "", final_url=None, title=None, chars=0,
                           status="failed", error=err, path=None, surface=surface)
    for u in pending:
        LEDGER.record_page(url=u, final_url=None, title=None, chars=0, status="failed",
                           error="deferred: never read (exit 75); re-run",
                           path=None, surface=surface)
    if a.json:
        json.dump({**payload, "unretrieved": pending}, sys.stdout, indent=1)
        print()
    else:
        truncated = 0
        pat = getattr(a, "grep_re", None)
        for r, text in zip(results, texts):
            if pat is not None:
                print_matches(r, text, r["storePath"], pat, getattr(a, "context", DEFAULT_GREP_CONTEXT))
            else:
                truncated += print_page(r, text, r["storePath"], a.max_chars)
        for e in errors:
            if e.get("recovered"):
                print(f"\n[web] {e.get('url')}: tinyfish: {e.get('error')} "
                      f"status={e.get('status')}; read via {e['recovered']}")
            else:
                print(f"\n!!!!! READ FAILED {e.get('url')} :: {e.get('error')} "
                      f"status={e.get('status')} {e.get('candidate_selectors') or ''}")
        routes: dict[str, int] = {}
        for r in results:
            routes[r.get("route") or "tinyfish"] = routes.get(r.get("route") or "tinyfish", 0) + 1
        failed = sum(1 for e in errors if not e.get("recovered"))
        tail = f" ({', '.join(f'{n} via {k}' for k, n in routes.items())})" if routes else ""
        tail += f", {failed} failed" if failed else ""
        tail += f", {len(pending)} deferred" if pending else ""
        tail += f", {truncated} truncated (full text in store)" if truncated else ""
        print(f"\n[web] {len(results)} ok{tail}")
    if pending:
        cause = payload.get("deferredCause") or "outage/transport"
        advice = (f"capacity frees within {WINDOW:.0f} s" if cause == "rate limit"
                  else "re-run in a few minutes or record the gap in toolHealth")
        print(f"\n[web] RETRYABLE ({cause}): {len(pending)} URL(s) were never read; {advice}. "
              f"Re-run with exactly these:")
        for u in pending:
            print(f"  {u}")
        return EX_RETRYABLE
    return 0


def run_read(a: argparse.Namespace) -> int:
    """Store, then TinyFish, then Exa, then Wayback; results in argument order."""
    validate_selectors(a)
    shaped = a.include_selector or a.exclude_selector or a.format != "markdown"
    hits: list[dict] = []
    live: list[str] = []
    for u in a.urls:
        hit = None if a.fresh or shaped else stored_page(u)
        if hit:
            hits.append(hit)
        else:
            live.append(u)
    payload, pending = fetch_urls(live, a) if live else ({"results": [], "errors": []}, [])
    errors = payload["errors"]
    # A TinyFish result under THIN_CHARS is often a JavaScript stub: ask Exa too, keep the longer.
    thin = {r["url"]: r for r in payload["results"]
            if r.get("url") and len(page_text(r).strip()) < THIN_CHARS}
    retry = [e["url"] for e in errors if e.get("url")] + pending + list(thin)
    if retry and a.format == "markdown":
        got = exa_read(retry, a.fresh)
        for u, r in thin.items():
            if u in got and len(got[u]["text"].strip()) > len(page_text(r).strip()):
                payload["results"][payload["results"].index(r)] = got.pop(u)
            else:
                got.pop(u, None)
        for e in errors:
            if e.get("url") in got:
                e["recovered"] = "exa"
        payload["results"] += [got[u] for u in retry if u in got]
        pending = [u for u in pending if u not in got]
    if not a.no_archive:
        payload["results"] += wayback_recover([e for e in errors if not e.get("recovered")], a)
    order = {u: i for i, u in reversed(list(enumerate(a.urls)))}
    payload["results"] = sorted(hits + payload["results"],
                                key=lambda r: order.get(r.get("url"), len(order)))
    return emit_fetch(payload, pending, a)


# ---------------------------------------------------------------- reddit

def run_reddit(a: argparse.Namespace) -> int:
    base = a.url.split("?")[0].rstrip("/")
    if not re.search(r"reddit\.com/r/[^/]+/comments/", base):
        raise Fatal("reddit expects a canonical "
                    "https://www.reddit.com/r/<sub>/comments/<id>/... URL")
    base = re.sub(r"^https?://(old|new|np|i)\.reddit\.com", "https://www.reddit.com", base)
    a.urls = [f"{base}/?sort={s}" for s in a.sort]
    payload, pending = fetch_urls(a.urls, a)
    return emit_fetch(payload, pending, a, surface="reddit")


# ---------------------------------------------------------------- github

def github_token() -> str:
    """GITHUB_TOKEN from env, keys.env, or the gh CLI's stored login."""
    tok = env_key("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def parse_github_target(spec: str, path: str | None, ref: str | None) -> tuple[str, str, str | None, str]:
    """(owner, repo, path, ref) from `owner/repo`, a github.com blob/tree/raw
    URL, or a raw.githubusercontent.com URL. --ref beats a ref in the URL;
    both beat the HEAD default."""
    s = spec.strip()
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/#?]+)"
                 r"(?:/(?:blob|tree|raw)/([^/#?]+)(?:/([^#?]*))?)?/?$", s)
    if m:
        o, r, url_ref, url_path = m.groups()
        return o, re.sub(r"\.git$", "", r), path or (url_path or None), ref or url_ref or "HEAD"
    m = re.match(r"^(?:https?://)?raw\.githubusercontent\.com/([^/]+)/([^/]+)/"
                 r"(?:refs/heads/)?([^/]+)/([^#?]+)$", s)
    if m:
        o, r, url_ref, url_path = m.groups()
        return o, r, path or url_path, ref or url_ref
    m = re.match(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$", s)
    if m:
        return m.group(1), m.group(2), path, ref or "HEAD"
    raise Fatal(f"github expects <owner>/<repo> or a github.com URL, got {spec!r}")


def github_raw(owner: str, repo: str, ref: str, path: str) -> tuple[str, str, str]:
    """(text, url, resolved_ref). HEAD resolves to the default branch on
    raw.githubusercontent.com; if it is rejected, main then master are tried."""
    refs = [ref] + (["main", "master"] if ref == "HEAD" else [])
    last = ""
    for candidate in refs:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{candidate}/{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "web"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace"), url, candidate
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code != 404:
                raise Fatal(f"github {url}: {last}")
        except (OSError, http.client.HTTPException) as exc:
            raise Retryable(f"github transport failure for {url}: {exc}")
    raise Fatal(f"{last} for {owner}/{repo}@{ref}:{path}. Run "
                f"`web github {owner}/{repo} --tree --filter <name>` to find the real path.")


def run_github(a: argparse.Namespace) -> int:
    owner, repo, path, ref = parse_github_target(a.repo, a.path, a.ref)
    if a.tree:
        token = github_token()
        if not token:
            note("no GITHUB_TOKEN: unauthenticated GitHub API allows 60 requests/hour "
                 f"(set GITHUB_TOKEN in {KEYS_FILE})")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
        try:
            data = _json_call(url, headers)
        except HTTPFailure as exc:
            if exc.code in (403, 429):
                raise Fatal(f"GitHub API rate limit for {owner}/{repo} ({exc}). Set "
                            f"GITHUB_TOKEN, or `web read https://github.com/{owner}/{repo}` "
                            f"for the rendered file list.")
            if exc.code == 404:
                raise Fatal(f"{owner}/{repo}@{ref} not found on the GitHub API "
                            f"(private repo, wrong ref, or wrong name)")
            raise Retryable(f"github tree {owner}/{repo}: {exc}")
        except (OSError, ValueError, http.client.HTTPException) as exc:
            raise Retryable(f"github tree {owner}/{repo}: {exc}")
        entries = [t for t in data.get("tree") or [] if t.get("type") == "blob"]
        if a.filter:
            needle = a.filter.lower()
            entries = [t for t in entries if needle in t["path"].lower()]
        LEDGER.record_query(f"github tree {owner}/{repo}@{ref}",
                            {"filter": a.filter or ""}, "github", len(entries))
        if a.json:
            json.dump({"repo": f"{owner}/{repo}", "ref": ref, "sha": data.get("sha"),
                       "truncated": bool(data.get("truncated")),
                       "files": [{"path": t["path"], "size": t.get("size")} for t in entries]},
                      sys.stdout, indent=1)
            print()
            return 0
        flt = f" matching {a.filter!r}" if a.filter else ""
        trunc = "; the API truncated this listing, narrow with --filter" if data.get("truncated") else ""
        print(f"{owner}/{repo}@{ref} ({(data.get('sha') or '')[:10]}): {len(entries)} files{flt}{trunc}")
        for t in entries:
            print(f"  {t.get('size') or 0:>8}  {t['path']}")
        return 0
    if not path:
        raise Fatal("github needs a <path> to read, or --tree to list the repository")
    try:
        text, url, resolved = github_raw(owner, repo, ref, path)
    except Fatal as exc:
        LEDGER.record_page(url=f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}",
                           final_url=None, title=None, chars=0, status="failed",
                           error=str(exc)[:200], path=None, surface="github")
        raise
    r = {"url": url, "final_url": f"https://github.com/{owner}/{repo}/blob/{resolved}/{path}",
         "title": f"{owner}/{repo}:{path}@{resolved}", "text": text, "route": "github"}
    a.format = "markdown"
    return emit_fetch({"results": [r], "errors": []}, [], a, surface="github")


# ------------------------------------------------------------------- log

def _since_ts(s: str | None) -> float | None:
    return parse_date(s, "--since").timestamp() if s else None


def _ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def run_log(a: argparse.Namespace) -> int:
    lane = LANE if a.lane_explicit else None
    since = _since_ts(a.since)
    pages = distinct_pages(LEDGER.pages(lane, since))
    queries = LEDGER.queries(lane, since)
    ok = [p for p in pages if p["status"] == "ok"]
    if a.json:
        json.dump({"lane": lane or "*", "since": a.since,
                   "distinctUrls": len(pages), "okUrls": len(ok), "failedUrls": len(pages) - len(ok),
                   "urls": pages,
                   "queries": [dict(q) for q in queries]}, sys.stdout, indent=1)
        print()
        return 0
    scope = f"lane {lane}" if lane else "all lanes"
    when = f" since {a.since}" if a.since else ""
    retried = sum(1 for p in pages if p["status"] == "ok" and p["failures"])
    print(f"[web] log {scope}{when}: {len(pages)} distinct URLs read "
          f"({len(ok)} ok, {len(pages) - len(ok)} failed, {retried} ok after a failed attempt), "
          f"{len(queries)} queries")
    if pages:
        print("URLS:")
    for p in pages:
        lane_col = "" if lane else f" [{p['lane']}]"
        tries = (f" [reads {p['reads']}" + (f", {p['failures']} failed" if p["failures"] else "") + "]"
                 if p["reads"] > 1 else "")
        if p["status"] == "ok":
            print(f"  ok     {p['chars']:>7}  {p['surface']:<6} {p['path']}  {p['url']}{lane_col}{tries}")
        else:
            print(f"  FAILED       -  {p['surface']:<6} {p['url']}{lane_col}{tries} :: {p['error']}")
    if queries:
        print("QUERIES:")
    for q in queries:
        lane_col = "" if lane else f" [{q['lane']}]"
        params = q["params"] if q["params"] not in ("{}", None) else ""
        print(f"  {_ts(q['ts'])}  {q['provider']:<8} n={q['n']:<3} {q['query']!r}{lane_col} {params}")
    return 0


# ----------------------------------------------------------------- check

DEPTHS_READ = {"page", "full", "source-code", "social-thread"}
DEPTHS_UNLOGGED = {"snippet", "measured"}
TIER_CAPPED = {"vendor", "aggregator", "reporting", "practitioner", "social-thread"}
X_HOSTS = ("x.com", "twitter.com", "api.fxtwitter.com")
X_SITE_HOSTS = {"docs.x.com", "developer.x.com", "developer.twitter.com", "help.x.com",
                "help.twitter.com", "about.x.com", "business.x.com", "blog.x.com", "blog.twitter.com"}
UGC_HOSTS = X_HOSTS + ("reddit.com", "wikipedia.org", "news.ycombinator.com", "quora.com",
                       "medium.com", "substack.com", "linkedin.com")
LOGGED_SURFACES = {"search", "fetch", "reddit", "github"}
DOC_NAMES = ("SYNTHESIS.md", "SYNTHESIS.json", "NOTE.md")
_NOT_USED = re.compile(r"\bnot (invoked|used|required|needed|called|attempted)\b|\bunused\b|"
                       r"\bno (browser|reddit|github|search|x) (use|calls?|reads?|fetch(es)?)\b|"
                       r"\b0 (calls?|queries|fetches|reads)\b|\bn/a\b", re.I)
_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
                         "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"'})


def norm_text(s: str) -> str:
    s = (s or "").lower().translate(_QUOTES)
    s = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", s)
    s = re.sub(r"[`*_>#|\[\]()]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def shingles(words: list[str], n: int = 5) -> set[tuple[str, ...]]:
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


_SHINGLE_CACHE: dict[int, set] = {}


def quote_in_text(datum: str, text: str) -> bool:
    """Substring, else >=50% 5-word shingle overlap, else any material
    numeric token (>=2 chars, not a bare year) present."""
    nd, nt = norm_text(datum), norm_text(text)
    if nd in nt:
        return True
    words = nd.split()
    dsh = shingles(words)
    if dsh:
        key = id(text)
        if key not in _SHINGLE_CACHE:
            _SHINGLE_CACHE[key] = shingles(nt.split())
        if len(dsh & _SHINGLE_CACHE[key]) / len(dsh) >= 0.5:
            return True
    for tok in re.findall(r"\d[\d.,]*", nd):
        tok = tok.strip(".,")
        if len(tok) >= 2 and not re.fullmatch(r"(19|20)\d\d", tok) and tok in nt:
            return True
    return False


def _host_in(url: str, hosts: tuple[str, ...]) -> bool:
    host = canon_url(url).split("/")[0]
    if host in X_SITE_HOSTS:
        return False   # developer/help/company pages, not posts
    return any(host == h or host.endswith("." + h) for h in hosts)


def is_x_url(url: str) -> bool:
    """A post/timeline read through xurl, which the ledger never sees."""
    return _host_in(url, X_HOSTS)


def is_ugc_url(url: str) -> bool:
    """Forum, wiki, X and blog-platform hosts: practitioner tier whatever the
    worker labelled them (one poisoned Reddit page reaches 38-51% of reports)."""
    return _host_in(url, UGC_HOSTS)


def lane_candidates(path: str, data: dict, explicit: str | None) -> list[str]:
    cands = [explicit] if explicit else []
    stem = os.path.splitext(os.path.basename(path))[0]
    for c in (stem, data.get("slice") if isinstance(data, dict) else None):
        if c and c not in cands:
            cands.append(c)
    return cands


def check_dossier(path: str, explicit_lane: str | None = None) -> dict:
    """Mechanical checks. Returns {flags: [(level, code, detail)], ...}."""
    res: dict = {"path": path, "flags": [], "lane": None, "since": None, "logged": 0, "failed": 0,
                 "kind": None, "data": None, "bytes": 0, "checkable": 0, "unverified": 0}
    flags = res["flags"]
    try:
        res["bytes"] = os.path.getsize(path)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        flags.append(("FAIL", "PARSE_ERROR", str(exc)))
        return res
    res["data"] = data
    if not isinstance(data, dict):
        flags.append(("FAIL", "PARSE_ERROR", "top level is not an object"))
        return res
    claims = data.get("claims") if isinstance(data.get("claims"), list) else None
    verdicts = data.get("verdicts") if isinstance(data.get("verdicts"), list) else None
    directions = data.get("directions") if isinstance(data.get("directions"), list) else None
    res["kind"] = "verdicts" if verdicts is not None else "claims" if claims is not None \
        else "directions" if directions is not None else None

    # lane + log, scoped to this run
    run = run_of(run_dir_of(path))
    lane, since = resolve_lane(lane_candidates(path, data, explicit_lane), run, explicit_lane)
    res["lane"], res["since"] = lane, since
    rows = LEDGER.pages(lane, since)
    log = distinct_pages(rows)
    logged_keys = {cite_key(p["url"]) for p in log if p["status"] == "ok"}
    best_chars: dict[str, int] = {}
    for r in rows:
        if r["status"] == "ok":
            k = cite_key(r["url"] or "")
            best_chars[k] = max(best_chars.get(k, 0), r["chars"] or 0)
    failed_keys = {cite_key(p["url"]) for p in log if p["status"] != "ok"}
    # Reads made without a lane land under 'unknown'; they still prove a read
    # through web happened, so they downgrade the citation flag to WARN.
    unknown_keys = {cite_key(p["url"]) for p in distinct_pages(LEDGER.pages("unknown", run[1]))
                    if p["status"] == "ok"} if lane != "unknown" else set()
    res["logged"] = len(logged_keys)
    res["failed"] = len(failed_keys)
    have_log = bool(log)
    if not have_log:
        flags.append(("WARN", "NO_FETCH_LOG", f"no pages read under lane {lane!r} in this run; "
                      f"pass --lane if the reads were logged under another name"))

    # stub
    if res["bytes"] < 2000:
        flags.append(("FAIL", "STUB", f"{res['bytes']} bytes"))
    if res["kind"] is None:
        flags.append(("FAIL", "STUB", "no claims, verdicts or directions"))
    elif claims is not None and not claims and data.get("status") == "complete":
        flags.append(("FAIL", "STUB", "claims empty with status complete"))

    tool_health = data.get("toolHealth") if isinstance(data.get("toolHealth"), list) else []
    # A page the worker read through the browser tool after web failed on it
    # is the one sanctioned outside read; it downgrades to WARN, nothing else does.
    used_browser = any(isinstance(t, dict) and t.get("surface") == "browser"
                       and not _NOT_USED.search(str(t.get("detail") or ""))
                       for t in tool_health)

    def cite_check(url: str, depth: str, where: str) -> None:
        if depth in DEPTHS_UNLOGGED or not url or is_x_url(url):
            return
        k = cite_key(url)
        if k not in logged_keys:
            if k in unknown_keys:
                flags.append(("WARN", "UNFETCHED_CITATION",
                              f"{url} read under lane 'unknown'; pass --lane ({where}, readDepth {depth})"))
                return
            if k in failed_keys and used_browser:
                flags.append(("WARN", "UNFETCHED_CITATION",
                              f"{url} (web read failed; browser read per toolHealth) ({where}, readDepth {depth})"))
                return
            extra = " (read failed)" if k in failed_keys else ""
            flags.append(("FAIL", "UNFETCHED_CITATION", f"{url}{extra} ({where}, readDepth {depth})"))
        elif best_chars.get(k, 0) < THIN_PAGE_CHARS:
            flags.append(("WARN", "THIN_PAGE", f"{url} ({best_chars.get(k, 0)} chars; {where})"))

    def quote_check(datum: str, urls: list[str], where: str) -> None:
        if not isinstance(datum, str) or len(datum) < 30:
            return
        texts = [t for t in (stored_text(u)[0] for u in urls if u) if t]
        if not texts:
            return
        res["checkable"] += 1
        if not any(quote_in_text(datum, t) for t in texts):
            res["unverified"] += 1
            flags.append(("WARN", "UNVERIFIED_QUOTE", f"{where} {datum[:70]!r} not in stored text of {urls[0]}"))

    if claims is not None:
        confs = []
        for i, c in enumerate(claims, 1):
            if not isinstance(c, dict):
                flags.append(("FAIL", "NO_SOURCE_CLAIM", f"{i}: claim is not an object"))
                continue
            confs.append(c.get("confidence"))
            sources = [s for s in (c.get("sources") or []) if isinstance(s, dict)]
            if not sources:
                flags.append(("FAIL", "NO_SOURCE_CLAIM", f"{i}: {str(c.get('claim'))[:70]!r}"))
                continue
            depths = [s.get("readDepth") for s in sources]
            if all(d == "snippet" for d in depths):
                flags.append(("FAIL", "SNIPPET_ONLY_CLAIM", f"{i}: {str(c.get('claim'))[:70]!r}"))
            types = {"social-thread" if is_ugc_url(s.get("url") or "") else s.get("sourceType")
                     for s in sources}
            if c.get("confidence") == "high" and types and types <= TIER_CAPPED:
                ugc = any(is_ugc_url(s.get("url") or "") for s in sources)
                flags.append(("WARN", "TIER_CAP_VIOLATION",
                              f"{i}: high on {'/'.join(sorted(t or '?' for t in types))} sources only"
                              + (" (forum/wiki/X hosts count as social-thread whatever the label)"
                                 if ugc else "")))
            text = f"{c.get('claim') or ''} {c.get('support') or ''}"
            if re.search(r"\b(MIT|BSD|MPL|GPL|LGPL|AGPL|CC0|RAIL)\b", text) or \
                    re.search(r"\b(apache|cc-by|openrail|creative commons|non-?commercial|"
                              r"licen[cs]ed (under|as)|license:)\b", text, re.I):
                urls = [s.get("url") or "" for s in sources]
                if not any("license" in u.lower()
                           or re.match(r"^huggingface\.co/[^/]+/[^/]+$", canon_url(u))
                           or "/api/v1/models/" in u or "huggingface.co/api/models/" in u
                           for u in urls):
                    flags.append(("WARN", "UNSOURCED_LICENSE", f"{i}: no LICENSE file or model-card source"))
            for j, s in enumerate(sources, 1):
                depth = s.get("readDepth") or ""
                cite_check(s.get("url") or "", depth, f"claim {i}.{j}")
                if depth in DEPTHS_READ:
                    quote_check(s.get("datum") or "", [s.get("url") or ""], f"{i}.{j}")
        if len(confs) >= 5 and all(x == "high" for x in confs):
            flags.append(("WARN", "ALL_HIGH", f"{len(confs)} claims, 100% high"))
        stop = data.get("stoppedBecause")
        if not isinstance(stop, str) or not stop.strip():
            flags.append(("WARN", "NO_STOP_REASON", "stoppedBecause missing or empty"))

    if verdicts is not None:
        for i, v in enumerate(verdicts, 1):
            if not isinstance(v, dict):
                continue
            urls = [u for u in (v.get("reFetchedUrls") or []) if isinstance(u, str)]
            for u in urls:
                cite_check(u, "full", f"verdict {i}")
            quote_check(v.get("decidingQuote") or "", urls, f"{i}")

    if directions is not None:
        for i, d in enumerate(directions, 1):
            if not isinstance(d, dict):
                continue
            for j, s in enumerate(d.get("inspiredBy") or [], 1):
                if isinstance(s, dict):
                    cite_check(s.get("url") or "", s.get("readDepth") or "page", f"direction {i}.{j}")
                elif isinstance(s, str):
                    cite_check(s, "page", f"direction {i}.{j}")

    if res["checkable"] and res["unverified"] / res["checkable"] > 0.5:
        flags.append(("FAIL", "UNVERIFIED_QUOTES",
                      f"{res['unverified']}/{res['checkable']} checkable datums not found in stored text"))

    reported = data.get("fetchedUrlCount")
    if have_log and isinstance(reported, (int, float)) and logged_keys:
        if abs(reported - len(logged_keys)) / len(logged_keys) > 0.25:
            flags.append(("WARN", "COUNT_DRIFT",
                          f"fetchedUrlCount {reported} reported vs {len(logged_keys)} logged ok URLs"))
    if have_log and tool_health:
        # A surface the worker reports as used must show up in its own log.
        seen = {p["surface"] for p in rows}
        for q in LEDGER.queries(lane, since):
            seen.add("github" if q["provider"] == "github" else "search")
        for t in tool_health:
            if not isinstance(t, dict):
                continue
            surface = str(t.get("surface") or "").lower()
            surface = "fetch" if surface == "read" else surface
            if surface not in LOGGED_SURFACES or surface in seen or \
                    _NOT_USED.search(str(t.get("detail") or "")):
                continue
            flags.append(("WARN", "TOOLHEALTH_UNLOGGED_SURFACE",
                          f"toolHealth reports {surface} {t.get('outcome') or '?'} but the lane "
                          f"log has no {surface} rows; say 'not used' or drop the entry"))
    if have_log and failed_keys and tool_health and \
            all(isinstance(t, dict) and t.get("outcome") == "ok" for t in tool_health):
        flags.append(("WARN", "TOOLHEALTH_OK_WITH_FAILURES",
                      f"{len(failed_keys)} failed URL(s) in the read log, every toolHealth outcome is ok"))
    return res


def flag_lines(res: dict) -> list[str]:
    return [f"{lvl} {code} {detail}" for lvl, code, detail in res["flags"]]


def flag_summary(res: dict) -> str:
    n_fail = sum(1 for f in res["flags"] if f[0] == "FAIL")
    n_warn = sum(1 for f in res["flags"] if f[0] == "WARN")
    return f"{n_fail} FAIL, {n_warn} WARN"


_URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")


def _urls_in_text(text: str) -> list[str]:
    out: list[str] = []
    for m in _URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;:!?*'\"")
        if u not in out:
            out.append(u)
    return out


def note_flags(text: str) -> list[tuple[str, str, str]]:
    """A Dig note cites [n] in its answer and lists each n under ## Sources as
    `[n] title · url`: one URL per number, nothing after it, no URL twice."""
    body, head, rest = text.partition("\n## Sources")
    if not head:
        return [("FAIL", "NO_SOURCES", "no ## Sources section")]
    sources = re.split(r"\n## ", rest, maxsplit=1)[0]
    flags: list[tuple[str, str, str]] = []
    listed: set[str] = set()
    first: dict[str, str] = {}
    for n, entry in re.findall(r"^\s*\[(\d+)\](.*)$", sources, re.M):
        listed.add(n)
        m = re.search(r"https?://\S+", entry)
        if not m:
            flags.append(("FAIL", "NO_SOURCE_URL", f"[{n}] has no URL: {entry.strip()[:80]}"))
            continue
        url = m.group(0).rstrip(".,;")
        if entry[m.end():].strip(" .,;"):
            flags.append(("FAIL", "TEXT_AFTER_URL", f"[{n}] has text after its URL: {entry[m.end():].strip()[:60]}"))
        k = cite_key(url)
        if k in first:
            flags.append(("FAIL", "DUPLICATE_SOURCE", f"[{n}] repeats the URL of [{first[k]}]: {url}"))
        first.setdefault(k, n)
    cited = sorted(set(re.findall(r"\[(\d+)\]", body)) - listed, key=int)
    return flags + [("FAIL", "MISSING_SOURCE", f"[{n}] cited but not listed under ## Sources") for n in cited]


def run_lane_names(run_dir: str) -> set[str]:
    """Bare lane names a run's workers may have logged under."""
    names = {"Orchestrator", "dig"}
    for f in _dossier_files(run_dir):
        label = _lane_label(run_dir, f)
        names.update({label, os.path.basename(label)})
        try:
            with open(f, encoding="utf-8") as fh:
                s = json.load(fh).get("slice")
            if isinstance(s, str) and s:
                names.add(s)
        except (OSError, ValueError, AttributeError):
            continue
    return names


def check_docs(files: list[str], run_dir: str | None, explicit: str | None) -> int:
    """Every URL in a synthesis or note must be a page read through web,
    by this run when there is one, so nothing cited points at a page nobody opened."""
    urls: list[str] = []
    flags: list[tuple[str, str, str]] = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            text = fh.read()
        if os.path.basename(f) == "NOTE.md":
            flags += note_flags(text)
        for u in _urls_in_text(text):
            if u not in urls:
                urls.append(u)
    in_run = None
    if run_dir:
        slug, start = run_of(run_dir)
        bare = run_lane_names(run_dir)

        def in_run(lane: str, ts: float) -> bool:
            return (lane == explicit or lane.startswith(slug + "/")
                    or (lane in bare and ts >= start))
    by_key: dict[str, list[tuple[str, float, int]]] = {}
    for p in LEDGER.db.execute("SELECT url, lane, ts, chars FROM pages WHERE status='ok' AND url IS NOT NULL"):
        by_key.setdefault(cite_key(p["url"]), []).append((p["lane"], p["ts"], p["chars"] or 0))
    matched = via_repo = skipped = 0
    for u in urls:
        if is_x_url(u):
            skipped += 1   # xurl reads are outside the ledger
            continue
        reads = by_key.get(cite_key(u))
        repo = False
        if not reads:
            # A repository or model root cited for files read from it
            # (README.md, LICENSE, model card) is the normal citation form.
            m = re.match(r"^(github\.com|huggingface\.co)/([^/]+)/([^/]+)$", canon_url(u))
            if m:
                prefix = f"{'github' if m.group(1) == 'github.com' else 'hf'}:{m.group(2)}/{m.group(3)}/"
                reads = [r for k, v in by_key.items() if k.startswith(prefix) for r in v]
                repo = bool(reads)
        if not reads:
            host = canon_url(u).split("/")[0]
            near = [k for k in by_key if k.split("/")[0] == host][:3]
            hint = f"; pages read on that host: {', '.join(near)}" if near else ""
            flags.append(("FAIL", "UNFETCHED_URL", f"{u} never read through web{hint}"))
        elif in_run is not None and not any(in_run(lane, ts) for lane, ts, _ in reads):
            lanes = sorted({lane for lane, _, _ in reads})
            flags.append(("WARN", "OTHER_RUN_URL",
                          f"{u} read only by other runs (lanes {', '.join(lanes[:5])})"))
        else:
            matched += 1
            via_repo += repo
            best = max(c for lane, ts, c in reads if in_run is None or in_run(lane, ts))
            if not repo and best < THIN_PAGE_CHARS:
                flags.append(("WARN", "THIN_PAGE", f"{u} ({best} chars)"))
    for lvl, code, detail in flags:
        print(f"{lvl} {code} {detail}")
    n_fail = sum(1 for f in flags if f[0] == "FAIL")
    n_warn = sum(1 for f in flags if f[0] == "WARN")
    scope = "this run" if in_run is not None else "any lane"
    repo_note = f" ({via_repo} as repository/model roots whose files were read)" if via_repo else ""
    print(f"[web] check {', '.join(os.path.basename(f) for f in files)}: {n_fail} FAIL, {n_warn} WARN; "
          f"{len(urls)} URLs, {matched} read by {scope}{repo_note}, {skipped} x.com skipped")
    return 0


def run_check(a: argparse.Namespace) -> int:
    target = os.path.abspath(os.path.expanduser(a.target))
    explicit = LANE if a.lane_explicit else None
    if os.path.isdir(target):
        docs = [os.path.join(target, n) for n in DOC_NAMES if os.path.isfile(os.path.join(target, n))]
        if not docs:
            raise Fatal(f"no {', '.join(DOC_NAMES)} under {target}")
        return check_docs(docs, target, explicit)
    if not os.path.isfile(target):
        raise Fatal(f"{target} is neither a run directory nor a file")
    name = os.path.basename(target)
    if name in DOC_NAMES:
        return check_docs([target], os.path.dirname(target), explicit)
    if target.endswith(".md"):
        return check_docs([target], None, explicit)
    res = check_dossier(target, explicit)
    for line in flag_lines(res):
        print(line)
    kind = res["kind"] or "?"
    n = len(res["data"].get(kind) or []) if isinstance(res["data"], dict) and kind != "?" else 0
    print(f"[web] check {a.target}: {flag_summary(res)}; lane {res['lane']}, {kind} {n}, "
          f"{res['logged']} logged ok URLs, {res['failed']} failed, "
          f"{res['checkable']} checkable datums, {res['unverified']} unverified")
    return 1 if any(code == "PARSE_ERROR" for _, code, _ in res["flags"]) else 0


# ---------------------------------------------------------------- digest

def _dossier_files(d: str) -> list[str]:
    files = sorted(f for f in os.listdir(d) if f.endswith(".json") and f != "SYNTHESIS.json")
    out = [os.path.join(d, f) for f in files]
    vdir = os.path.join(d, "verify")
    if os.path.isdir(vdir):
        out += [os.path.join(vdir, f) for f in sorted(os.listdir(vdir)) if f.endswith(".json")]
    return out


def _lane_label(d: str, path: str) -> str:
    rel = os.path.relpath(path, d)
    return os.path.splitext(rel)[0]


def _source_urls(data: dict) -> list[str]:
    urls = []
    for c in data.get("claims") or []:
        if isinstance(c, dict):
            urls += [s.get("url") for s in c.get("sources") or [] if isinstance(s, dict) and s.get("url")]
    for v in data.get("verdicts") or []:
        if isinstance(v, dict):
            urls += [u for u in v.get("reFetchedUrls") or [] if isinstance(u, str)]
    for dd in data.get("directions") or []:
        if isinstance(dd, dict):
            for s in dd.get("inspiredBy") or []:
                urls.append(s.get("url") if isinstance(s, dict) else s)
    return [u for u in urls if isinstance(u, str) and u]


def _fmt_list(items, indent: str = "  - ") -> list[str]:
    out = []
    for it in items or []:
        out.append(indent + (it if isinstance(it, str) else json.dumps(it, ensure_ascii=False)))
    return out


def render_claim(i: int, c: dict) -> str:
    lines = [f"[{i}] ({c.get('kind') or '?'}, {c.get('confidence') or '?'}) {c.get('claim') or ''}"]
    if c.get("support"):
        lines.append(f"    support: {c['support']}")
    for s in c.get("sources") or []:
        if isinstance(s, dict):
            lines.append(f"    - {s.get('readDepth') or '?'} {s.get('sourceType') or '?'} "
                         f"{s.get('url') or ''} :: {s.get('datum') or ''}")
        else:
            lines.append(f"    - {json.dumps(s, ensure_ascii=False)}")
    if c.get("caveats"):
        cav = c["caveats"] if isinstance(c["caveats"], list) else [c["caveats"]]
        lines.append("    caveats: " + " | ".join(str(x) for x in cav))
    extra = {k: v for k, v in c.items() if k not in
             ("claim", "kind", "confidence", "support", "sources", "caveats")}
    if extra:
        lines.append(f"    extra: {json.dumps(extra, ensure_ascii=False)}")
    return "\n".join(lines)


def render_verdict(i: int, v: dict) -> str:
    lines = [f"[{i}] {v.get('verdict') or '?'} :: {v.get('claim') or ''}"]
    for sv in v.get("subVerdicts") or []:
        lines.append(f"    sub: {json.dumps(sv, ensure_ascii=False)}")
    if v.get("decidingQuote"):
        lines.append(f"    quote: {v['decidingQuote']}")
    for u in v.get("reFetchedUrls") or []:
        lines.append(f"    - refetched {u}")
    if v.get("correction"):
        lines.append(f"    correction: {v['correction']}")
    return "\n".join(lines)


def render_direction(i: int, d: dict) -> str:
    lines = [f"[{i}] {d.get('direction') or ''}"]
    for k in ("rationale", "nearestExistingWork", "risk"):
        if d.get(k):
            lines.append(f"    {k}: {d[k]}")
    for s in d.get("inspiredBy") or []:
        lines.append(f"    - {json.dumps(s, ensure_ascii=False) if not isinstance(s, str) else s}")
    return "\n".join(lines)


KNOWN_KEYS = {"slice", "asOf", "status", "verdict", "stoppedBecause", "claims", "verdicts",
              "directions", "contradictions", "gaps", "toolHealth", "queries",
              "uniqueSourceCount", "fetchedUrlCount"}


def render_lane(path: str, res: dict, window: tuple[int, int] | None) -> str:
    """Complete single-lane rendering, paginated by the claim window so no
    call exceeds the harness elision threshold."""
    data = res["data"]
    if not isinstance(data, dict):
        return "\n".join(flag_lines(res)) + f"\n[web] digest {path}: {flag_summary(res)}"
    kind = res["kind"] or "claims"
    items = data.get(kind) or []
    n = len(items)
    header = [f"== {data.get('slice') or _lane_label(os.path.dirname(path), path)} ({path})",
              f"status {data.get('status') or '?'} | asOf {data.get('asOf') or '?'} | {kind} {n} | "
              f"uniqueSourceCount {data.get('uniqueSourceCount', '?')} | fetchedUrlCount "
              f"{data.get('fetchedUrlCount', '?')} reported / {res['logged']} logged (lane {res['lane']}) | "
              f"{res['bytes']} bytes",
              f"VERDICT: {data.get('verdict') or '(none)'}",
              f"STOPPED BECAUSE: {data.get('stoppedBecause') or '(missing)'}",
              f"CHECK: {flag_summary(res)}"]
    tail = []
    if data.get("contradictions"):
        tail.append("CONTRADICTIONS:")
        for x in data["contradictions"]:
            if isinstance(x, dict):
                tail.append(f"  - {x.get('topic') or ''} :: positions: "
                            f"{' | '.join(str(p) for p in x.get('positions') or [])} :: "
                            f"resolution: {x.get('resolution') or ''}")
            else:
                tail.append(f"  - {x}")
    tail.append("GAPS:" if data.get("gaps") else "GAPS: (none)")
    tail += _fmt_list(data.get("gaps"))
    tail.append("TOOLHEALTH:" if data.get("toolHealth") else "TOOLHEALTH: (none)")
    for t in data.get("toolHealth") or []:
        if isinstance(t, dict):
            tail.append(f"  - {t.get('surface') or '?'} {t.get('outcome') or '?'} :: {t.get('detail') or ''}")
        else:
            tail.append(f"  - {t}")
    q = data.get("queries")
    tail.append(f"QUERIES: {len(q) if isinstance(q, list) else q if q is not None else 0}")
    for k in data:
        if k not in KNOWN_KEYS:
            tail.append(f"EXTRA {k}: {json.dumps(data[k], ensure_ascii=False)}")
    tail.append("FLAGS:" if res["flags"] else "FLAGS: (none)")
    tail += ["  " + line for line in flag_lines(res)]

    render = {"claims": render_claim, "verdicts": render_verdict, "directions": render_direction}[kind]
    lo, hi = window or (1, n)
    lo, hi = max(1, lo), min(n, hi)
    fixed = "\n".join(header) + "\n" + "\n".join(tail)
    budget = DIGEST_SOFT_LIMIT - len(fixed) - 200
    blocks: list[str] = []
    used = 0
    last = lo - 1
    for i in range(lo, hi + 1):
        block = render(i, items[i - 1]) if isinstance(items[i - 1], dict) \
            else f"[{i}] {json.dumps(items[i - 1], ensure_ascii=False)}"
        if blocks and used + len(block) > budget:
            break
        if not blocks and len(block) > budget:
            block = block[:budget] + "\n    …[claim rendering cut at the output limit]"
        blocks.append(block)
        used += len(block) + 1
        last = i
    body = (f"{kind.upper()} {lo}-{last} of {n}:\n" + "\n".join(blocks) if blocks
            else f"{kind.upper()}: (none in window {lo}-{hi}; {n} total)")
    cont = f"\n[web] digest continues: --claims {last + 1}-{hi}" if last < hi else ""
    out = "\n".join(header) + "\n" + body + cont + "\n" + "\n".join(tail)
    if len(out) > DIGEST_HARD_LIMIT:
        out = out[:DIGEST_HARD_LIMIT - 60] + "\n…[digest cut at the hard output limit]"
    return out


def _parse_window(s: str | None) -> tuple[int, int] | None:
    if not s:
        return None
    m = re.fullmatch(r"(\d+)-(\d+)", s.strip())
    if not m or int(m.group(1)) < 1 or int(m.group(2)) < int(m.group(1)):
        raise Fatal(f"--claims expects A-B with 1 <= A <= B, got {s!r}")
    return int(m.group(1)), int(m.group(2))


def _lane_minutes(res: dict, path: str) -> str:
    """Minutes from the lane's first logged call in this run to the dossier write."""
    try:
        end = os.path.getmtime(path)
    except OSError:
        return "-"
    since = max(res["since"] or 0.0, end - 12 * 3600)
    lane = res["lane"]
    ts = [r["ts"] for r in LEDGER.pages(lane, since)] + [r["ts"] for r in LEDGER.queries(lane, since)]
    ts = [t for t in ts if t <= end + 60]
    return f"{(end - min(ts)) / 60:.0f}" if ts else "-"


def run_digest(a: argparse.Namespace) -> int:
    target = os.path.expanduser(a.target)
    explicit = LANE if a.lane_explicit else None
    window = _parse_window(a.claims)
    if os.path.isfile(target):
        res = check_dossier(target, explicit)
        if a.json:
            json.dump({"file": target, "lane": res["lane"], "flags": flag_lines(res),
                       "logged": res["logged"], "dossier": res["data"]}, sys.stdout, indent=1)
            print()
            return 0
        print(render_lane(target, res, window))
        return 0
    if not os.path.isdir(target):
        raise Fatal(f"{target} is neither a file nor a directory")
    files = _dossier_files(target)
    if explicit:
        pick = [f for f in files if _lane_label(target, f) in (explicit, f"verify/{explicit}")]
        if not pick:
            for f in files:
                try:
                    with open(f, encoding="utf-8") as fh:
                        if json.load(fh).get("slice") == explicit:
                            pick.append(f)
                except (OSError, ValueError, AttributeError):
                    continue
        if not pick:
            raise Fatal(f"no dossier for lane {explicit!r} under {target}")
        res = check_dossier(pick[0], None)   # --lane picked the dossier; its reads resolve run-scoped
        if a.json:
            json.dump({"file": pick[0], "lane": res["lane"], "flags": flag_lines(res),
                       "logged": res["logged"], "dossier": res["data"]}, sys.stdout, indent=1)
            print()
            return 0
        print(render_lane(pick[0], res, window))
        return 0
    if not files:
        print(f"no *.json dossiers under {target}")
        return 0
    rows = []
    cited: dict[str, set[str]] = {}
    for f in files:
        res = check_dossier(f, None)
        data = res["data"] if isinstance(res["data"], dict) else {}
        label = _lane_label(target, f)
        for u in _source_urls(data):
            cited.setdefault(cite_key(u), set()).add(label)
        codes: dict[str, int] = {}
        for lvl, code, _ in res["flags"]:
            key = f"{'!' if lvl == 'FAIL' else ''}{code}"
            codes[key] = codes.get(key, 0) + 1
        confs = [c.get("confidence") for c in data.get("claims") or [] if isinstance(c, dict)] \
            if isinstance(data.get("claims"), list) else []
        rows.append({
            "lane": label, "status": data.get("status") or ("?" if data else "PARSE"),
            "claims": len(data.get("claims") or []) if isinstance(data.get("claims"), list) else 0,
            "verdicts": len(data.get("verdicts") or []) if isinstance(data.get("verdicts"), list) else 0,
            "confidence": {k: confs.count(k) for k in ("high", "medium", "low")},
            "hml": "/".join(str(confs.count(k)) for k in ("high", "medium", "low")) if confs else "-",
            "minutes": _lane_minutes(res, f),
            "uniq": data.get("uniqueSourceCount", "-"),
            "fetchedReported": data.get("fetchedUrlCount", "-"), "fetchedLogged": res["logged"],
            "bytes": res["bytes"],
            "gaps": len(data.get("gaps") or []) if isinstance(data.get("gaps"), list) else 0,
            "contradictions": len(data.get("contradictions") or []) if isinstance(data.get("contradictions"), list) else 0,
            "fail": sum(1 for x in res["flags"] if x[0] == "FAIL"),
            "warn": sum(1 for x in res["flags"] if x[0] == "WARN"),
            "flags": " ".join(f"{k}{'×' + str(v) if v > 1 else ''}" for k, v in sorted(codes.items())),
            "stoppedBecause": bool(data.get("stoppedBecause")),
        })
    shared = sorted((k, sorted(v)) for k, v in cited.items() if len(v) >= 2)
    if a.json:
        json.dump({"dir": target, "lanes": rows, "uniqueUrls": len(cited),
                   "sharedUrls": [{"url": k, "lanes": v} for k, v in shared]}, sys.stdout, indent=1)
        print()
        return 0
    widths = {"lane": max(4, max(len(r["lane"]) for r in rows))}
    print(f"[web] digest {target}: {len(rows)} dossiers")
    print(f"{'lane':<{widths['lane']}}  status    claims verd   H/M/L   min  uniq  fetched rep/log     KB  gaps contra stop  flags")
    for r in rows:
        fetched = f"{r['fetchedReported']}/{r['fetchedLogged']}"
        flags = (f"F:{r['fail']} W:{r['warn']} {r['flags']}" if r["flags"] else "-")
        print(f"{r['lane']:<{widths['lane']}}  {str(r['status']):<9} {r['claims']:>5} {r['verdicts']:>5} "
              f"{r['hml']:>7} {r['minutes']:>5} "
              f"{str(r['uniq']):>5}  {fetched:>15} {r['bytes'] / 1024:>6.1f} {r['gaps']:>5} {r['contradictions']:>6} "
              f"{'y' if r['stoppedBecause'] else '-':>4}  {flags}")
    print(f"\nunique URLs across the wave: {len(cited)}")
    print(f"URLs cited by two or more lanes: {len(shared)}")
    for k, lanes in shared:
        print(f"  {k}  <- {', '.join(lanes)}")
    print(f"\n[web] one lane in full: web digest {target} --lane <lane>")
    return 0


# ------------------------------------------------------------ save, prior

def nbrain_bin() -> str:
    path = os.environ.get("NBRAIN_BIN") or shutil.which("nbrain")
    if not path:
        raise Fatal("nbrain is not on PATH; install it or set NBRAIN_BIN")
    return path


def run_nbrain(argv: list[str], text: str | None = None) -> int:
    try:
        return subprocess.run([nbrain_bin(), *argv], input=text, text=True).returncode
    except OSError as exc:
        raise Fatal(f"cannot run nbrain: {exc}")


def run_save(a: argparse.Namespace) -> int:
    target = os.path.abspath(os.path.expanduser(a.target))
    if os.path.isdir(target):
        found = [os.path.join(target, n) for n in ("SYNTHESIS.md", "NOTE.md")
                 if os.path.isfile(os.path.join(target, n))]
        if not found:
            raise Fatal(f"no SYNTHESIS.md or NOTE.md under {target}")
        target = found[0]
    try:
        with open(target, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise Fatal(f"cannot read {target}: {exc}")
    if not text.strip():
        raise Fatal(f"{target} is empty")
    title = a.title
    if not title:
        m = re.search(r"^# +(.+?)\s*$", text, re.M)
        if not m:
            raise Fatal(f"{target} has no `# ` title line; pass --title")
        title = m.group(1)
    why = a.why
    if not why:
        kind = {"NOTE.md": "Dig", "SYNTHESIS.md": "Wave"}.get(os.path.basename(target))
        if not kind:
            raise Fatal(f"{os.path.basename(target)} is not NOTE.md or SYNTHESIS.md; pass --why")
        m = re.search(r"as of (\d{4}-\d{2}-\d{2})", text)
        date = m.group(1) if m else datetime.fromtimestamp(os.path.getmtime(target)).strftime("%Y-%m-%d")
        why = f"research note ({kind}) {os.path.basename(os.path.dirname(target))}, as of {date}"
    return run_nbrain(["save", "-", "--title", title, "--why", why, "--as", "research"], text)


def run_prior(a: argparse.Namespace) -> int:
    return run_nbrain(["search", a.question, "--source", "research", "--limit", str(a.limit)])


# ------------------------------------------------------------------- gc

def store_stats() -> tuple[int, int]:
    n = size = 0
    try:
        for name in os.listdir(STORE_PATH):
            p = os.path.join(STORE_PATH, name)
            try:
                size += os.path.getsize(p)
                n += 1
            except OSError:
                pass
    except OSError:
        pass
    return n, size


def run_gc(a: argparse.Namespace) -> int:
    cutoff = time.time() - a.days * 86400
    removed = freed = 0
    try:
        names = os.listdir(STORE_PATH)
    except OSError:
        names = []
    for name in names:
        p = os.path.join(STORE_PATH, name)
        try:
            st = os.stat(p)
            if st.st_mtime < cutoff:
                os.remove(p)
                removed += 1
                freed += st.st_size
        except OSError:
            pass
    pages, queries = LEDGER.gc(cutoff)
    n, size = store_stats()
    print(f"[web] gc: removed {removed} store files ({freed / 1e6:.1f} MB), {pages} pages rows, "
          f"{queries} queries rows older than {a.days} days; store now {n} files, {size / 1e6:.1f} MB")
    return 0


# ------------------------------------------------------------------ keys

def run_keys(a: argparse.Namespace) -> int:
    try:
        keys = load_keys()
        src = "environment" if os.environ.get("TINYFISH_API_KEYS") else KEYS_FILE
        print(f"tinyfish pool: {len(keys)} keys (from {src})")
    except Fatal as exc:
        keys = []
        print(f"tinyfish pool: NONE ({exc})")
    print("tinyfish funded key: " + ("set, not pooled" if env_key("TINYFISH_API_KEY") else "not set"))
    for name in ("exa", "brave", "serper"):
        var = PROVIDER_KEYS[name]
        print(f"{name}: {'set' if env_key(var) else 'NOT SET (' + var + ')'}")
    print(f"search order: {' -> '.join(PROVIDERS)}")
    if keys:
        LEDGER.report(keys)
    n, size = store_stats()
    print(f"page store {STORE_PATH}: {n} files, {size / 1e6:.1f} MB")
    print(f"ledger {LEDGER_PATH}: " + ", ".join(f"{t} {c}" for t, c in LEDGER.counts().items()))
    if not a.test:
        return 0
    print("\nlive probe (one search per key):")
    bad = 0
    exa = env_key("EXA_API_KEY")
    if exa:
        try:
            n = len(exa_call("/search", {"query": "web key probe", "type": "lite", "numResults": 1},
                             exa, timeout=30).get("results") or [])
            print(f"  exa  ok ({n} results)")
        except (OSError, ValueError, http.client.HTTPException) as e:
            bad += 1
            print(f"  exa  {e}")
    for k in keys:
        LEDGER.acquire("search", [k], 1, a.max_wait)
        url = SEARCH_URL + "?" + urllib.parse.urlencode({"query": "web key probe"})
        req = urllib.request.Request(url, headers={"X-API-Key": k})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                n = len(json.loads(r.read().decode()).get("results") or [])
            print(f"  tinyfish {key_id(k)} …{k[-6:]}  ok ({n} results)")
        except urllib.error.HTTPError as e:
            bad += 1
            print(f"  tinyfish {key_id(k)} …{k[-6:]}  HTTP {e.code} "
                  f"retry_after={e.headers.get('Retry-After')}")
        except Exception as e:
            bad += 1
            print(f"  tinyfish {key_id(k)} …{k[-6:]}  {e}")
    return 1 if bad else 0


# ------------------------------------------------------------------- mcp

MCP_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
_STRINGS = {"type": "array", "items": {"type": "string"}}
MCP_TOOLS = [
    {"name": "search", "title": "Web search",
     "description": "Search the web (Exa; falls back to TinyFish, Brave, Serper). Returns numbered "
                    "results: title · host · date, URL, a clipped highlight. Read a page before "
                    "relying on it.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["query"],
                     "properties": {
                         "query": {"type": "string"},
                         "type": {"type": "string", "enum": list(TYPES)},
                         "site": {**_STRINGS, "description": "only these domains"},
                         "exclude": {**_STRINGS, "description": "never these domains"},
                         "after": {"type": "string", "description": "published on or after YYYY-MM-DD"},
                         "before": {"type": "string", "description": "published on or before YYYY-MM-DD"},
                         "recency": {"type": "string", "enum": list(RECENCY_DAYS)},
                         "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                         "deep": {"type": "boolean", "description": "slower, more thorough Exa search"},
                         "provider": {"type": "string", "enum": list(PROVIDERS),
                                      "description": "use only this provider"}}},
     "annotations": {"title": "Web search", "readOnlyHint": True, "openWorldHint": True}},
    {"name": "read", "title": "Read web pages",
     "description": "Read web pages as text: a stored copy under a day old, else TinyFish, Exa, then the Wayback "
                    "Machine. Each page header names its store path and route. grep returns only "
                    "the passages around matches.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["urls"],
                     "properties": {
                         "urls": {**_STRINGS, "minItems": 1},
                         "grep": {**_STRINGS, "description": "case-insensitive regexes"},
                         "context": {"type": "integer", "minimum": 0,
                                     "description": f"chars around each grep match (default {DEFAULT_GREP_CONTEXT})"},
                         "max_chars": {"type": "integer", "minimum": 0,
                                       "description": f"preview cap per page (default {DEFAULT_MAX_CHARS}; 0 = all)"},
                         "fresh": {"type": "boolean", "description": "skip the stored copy and read live"},
                         "no_archive": {"type": "boolean", "description": "never fall back to the Wayback Machine"},
                         "format": {"type": "string", "enum": ["markdown", "html", "json"]},
                         "include_selector": {**_STRINGS, "description": "CSS selectors to keep"},
                         "exclude_selector": {**_STRINGS, "description": "CSS selectors to drop"}}},
     "annotations": {"title": "Read web pages", "readOnlyHint": True, "openWorldHint": True}},
]


def _strs(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return v
    raise ValueError(f"expected a string or a list of strings, got {v!r}")


def mcp_argv(name: str, args: dict) -> list[str]:
    """The CLI argv for an MCP tool call; positionals follow `--` so a value
    starting with '-' is never read as a flag."""
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    known = MCP_TOOLS[0 if name == "search" else 1]["inputSchema"]["properties"]
    unknown = set(args) - set(known)
    if unknown:
        raise ValueError(f"unknown argument(s): {', '.join(sorted(unknown))}")
    opts: list[str] = []
    if name == "search":
        if not isinstance(args.get("query"), str) or not args["query"].strip():
            raise ValueError("query is required")
        for k in ("type", "after", "before", "recency", "provider"):
            if args.get(k):
                opts += [f"--{k}", str(args[k])]
        for k in ("site", "exclude"):
            if args.get(k):
                opts += [f"--{k}", ",".join(_strs(args[k]))]
        if args.get("limit") is not None:
            opts += ["--limit", str(int(args["limit"]))]
        if args.get("deep"):
            opts.append("--deep")
        return ["search", *opts, "--", args["query"]]
    urls = _strs(args.get("urls"))
    if not urls:
        raise ValueError("urls is required")
    for g in _strs(args.get("grep")):
        opts += ["--grep", g]
    for k in ("context", "max_chars"):
        if args.get(k) is not None:
            opts += [f"--{k.replace('_', '-')}", str(int(args[k]))]
    if args.get("format"):
        opts += ["--format", str(args["format"])]
    for k in ("include_selector", "exclude_selector"):
        for s in _strs(args.get(k)):
            opts += [f"--{k.replace('_', '-')}", s]
    if args.get("fresh"):
        opts.append("--fresh")
    if args.get("no_archive"):
        opts.append("--no-archive")
    return ["read", *opts, "--", *urls]


def mcp_call(parser: argparse.ArgumentParser, name: str, args) -> dict:
    out, err = io.StringIO(), io.StringIO()
    try:
        argv = mcp_argv(name, args if args is not None else {})
    except (ValueError, TypeError) as exc:
        return {"content": [{"type": "text", "text": f"bad arguments: {exc}"}], "isError": True}
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            a = parser.parse_args(argv)
            a.lane_explicit = True
            rc = run(a)
        except SystemExit as exc:   # argparse rejected the arguments; its last line says why
            rc = exc.code if isinstance(exc.code, int) else 2
            err = io.StringIO(err.getvalue().strip().splitlines()[-1] if err.getvalue().strip() else "")
        except Exception as exc:    # a tool failure is a result, never a dead server
            print(f"[web] internal error: {exc!r}", file=sys.stderr)
            rc = 1
    text = out.getvalue()
    if rc:
        text = (text + err.getvalue()).strip() or f"failed with exit {rc}"
    return {"content": [{"type": "text", "text": text}], "isError": bool(rc)}


def run_mcp(a: argparse.Namespace) -> int:
    """Line-delimited JSON-RPC 2.0 over stdio: initialize, ping, tools/list, tools/call."""
    parser = build_parser()
    stdout = sys.stdout

    def send(msg: dict) -> None:
        stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
        stdout.flush()

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        if not isinstance(msg, dict) or not isinstance(msg.get("method"), str):
            if isinstance(msg, dict) and "method" not in msg:
                continue   # a response to nothing we sent
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}})
            continue
        if "id" not in msg:
            continue   # notifications: initialized, cancelled
        mid, method, params = msg["id"], msg["method"], msg.get("params") or {}
        if method == "initialize":
            asked = params.get("protocolVersion") if isinstance(params, dict) else None
            result = {"protocolVersion": asked if asked in MCP_VERSIONS else MCP_VERSIONS[0],
                      "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "web", "version": "1.0.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": MCP_TOOLS}
        elif method == "tools/call":
            name = params.get("name") if isinstance(params, dict) else None
            if name not in ("search", "read"):
                send({"jsonrpc": "2.0", "id": mid,
                      "error": {"code": -32602, "message": f"unknown tool: {name}"}})
                continue
            result = mcp_call(parser, name, params.get("arguments"))
        else:
            send({"jsonrpc": "2.0", "id": mid,
                  "error": {"code": -32601, "message": f"method not found: {method}"}})
            continue
        send({"jsonrpc": "2.0", "id": mid, "result": result})
    return 0


# ------------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="web", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser, wait: bool = True) -> None:
        sp.add_argument("--lane", default=argparse.SUPPRESS,
                        help="lane the reads are logged under (env WEB_LANE)")
        if wait:
            sp.add_argument("--max-wait", type=float, default=DEFAULT_MAX_WAIT,
                            help="seconds to wait for TinyFish pool capacity before "
                                 "exiting 75 (default %(default)s)")

    s = sub.add_parser("search", help="search the web: Exa, else TinyFish, Brave, Serper")
    s.add_argument("query")
    s.add_argument("--type", choices=tuple(TYPES), help="result kind")
    s.add_argument("--site", help="only these domains, comma-separated")
    s.add_argument("--exclude", help="never these domains, comma-separated")
    s.add_argument("--after", help="published on or after YYYY-MM-DD")
    s.add_argument("--before", help="published on or before YYYY-MM-DD")
    s.add_argument("--recency", choices=tuple(RECENCY_DAYS), help="published within the last …")
    s.add_argument("--limit", type=int, default=10, help="results (1-100, default %(default)s)")
    s.add_argument("--deep", action="store_true", help="Exa deep search: slower, more thorough")
    s.add_argument("--provider", choices=PROVIDERS, help="use only this provider, no fallback")
    s.add_argument("--json", action="store_true", help="every field, full highlights")
    add_common(s)
    s.set_defaults(func=run_search)

    def add_read_opts(fp: argparse.ArgumentParser) -> None:
        fp.add_argument("--format", choices=("markdown", "html", "json"), default="markdown")
        fp.add_argument("--include-selector", action="append",
                        help=f"CSS selector to keep (repeatable, max {MAX_SELECTORS})")
        fp.add_argument("--exclude-selector", action="append", help="CSS selector to drop (repeatable)")
        fp.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                        help="preview cap per page (default %(default)s; 0 = all); "
                             "the store keeps the full text")
        fp.add_argument("--grep", action="append", metavar="REGEX",
                        help="print windows around matches (case-insensitive) instead of the preview")
        fp.add_argument("--context", type=int, default=DEFAULT_GREP_CONTEXT,
                        help="chars each side of a --grep match (default %(default)s)")
        fp.add_argument("--json", action="store_true", help="the payload as JSON, with storePath")
        add_common(fp)

    f = sub.add_parser("read", help="read pages: store, else TinyFish, Exa, Wayback")
    f.add_argument("urls", nargs="+")
    add_read_opts(f)
    f.add_argument("--fresh", action="store_true", help="skip the stored copy and read live")
    f.add_argument("--no-archive", action="store_true", help="never fall back to the Wayback Machine")
    f.set_defaults(func=run_read)

    r = sub.add_parser("reddit", help="read a Reddit thread under several comment sorts")
    r.add_argument("url")
    r.add_argument("--sort", nargs="+", default=["top", "new"],
                   choices=("top", "new", "best", "controversial", "old", "qa"))
    add_read_opts(r)
    r.set_defaults(func=run_reddit)

    g = sub.add_parser("github", help="read a repository file, or list the tree")
    g.add_argument("repo", help="<owner>/<repo>, a github.com blob/tree URL, or a raw URL")
    g.add_argument("path", nargs="?", help="file path inside the repository")
    g.add_argument("--ref", default=None, help="branch, tag or SHA (default: the default branch)")
    g.add_argument("--tree", action="store_true", help="list the repository's files")
    g.add_argument("--filter", help="case-insensitive substring filter for --tree")
    g.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                   help="preview cap (default %(default)s; 0 = all)")
    g.add_argument("--grep", action="append", metavar="REGEX",
                   help="print windows around matches instead of the preview")
    g.add_argument("--context", type=int, default=DEFAULT_GREP_CONTEXT,
                   help="chars each side of a --grep match (default %(default)s)")
    g.add_argument("--json", action="store_true")
    add_common(g, wait=False)
    g.set_defaults(func=run_github)

    c = sub.add_parser("check", help="flags against the ledger: a run dir's SYNTHESIS or NOTE, "
                                    "a lane dossier, or any .md's URLs")
    c.add_argument("target", help="run dir, dossier .json, or .md")
    add_common(c, wait=False)
    c.set_defaults(func=run_check)

    d = sub.add_parser("digest", help="lane table for a run dir, or one lane in full")
    d.add_argument("target", help="run dir, or one dossier file")
    d.add_argument("--claims", help="A-B claim window (1-indexed, inclusive)")
    d.add_argument("--json", action="store_true")
    add_common(d, wait=False)
    d.set_defaults(func=run_digest)

    sv = sub.add_parser("save", help="save a Dig note or Wave synthesis to nbrain")
    sv.add_argument("target", help="NOTE.md, SYNTHESIS.md, or a run dir")
    sv.add_argument("--title", help="default: the first `# ` line")
    sv.add_argument("--why", help="default: research note (Dig|Wave) <run-slug>, as of <date>")
    sv.set_defaults(func=run_save)

    pr = sub.add_parser("prior", help="earlier research on a question, from nbrain")
    pr.add_argument("question")
    pr.add_argument("--limit", type=int, default=8)
    pr.set_defaults(func=run_prior)

    lg = sub.add_parser("log", help="URLs read and queries run, per lane")
    lg.add_argument("--since", help="YYYY-MM-DD lower bound")
    lg.add_argument("--json", action="store_true")
    add_common(lg, wait=False)
    lg.set_defaults(func=run_log)

    k = sub.add_parser("keys", help="configured keys, TinyFish pool usage, store and ledger size")
    k.add_argument("--test", action="store_true", help="spend one search per key to verify it")
    add_common(k)
    k.set_defaults(func=run_keys)

    gc = sub.add_parser("gc", help="delete stored pages and ledger rows older than N days")
    gc.add_argument("--days", type=int, default=30)
    gc.set_defaults(func=run_gc)

    m = sub.add_parser("mcp", help="stdio MCP server with tools search and read")
    m.set_defaults(func=run_mcp)
    return p


def run(a: argparse.Namespace) -> int:
    """Run a parsed command; errors become an exit code and a stderr line."""
    try:
        a.grep_re = compile_grep(getattr(a, "grep", None))
        return a.func(a) or 0
    except RateLimited as exc:
        print(f"\n[web] RETRYABLE (rate limit): {exc}; capacity frees within {WINDOW:.0f} s, "
              f"re-run this exact command.", file=sys.stderr, flush=True)
        return EX_RETRYABLE
    except Retryable as exc:
        print(f"\n[web] RETRYABLE (outage/transport): {exc}. Re-run in a few minutes or record "
              f"the gap in toolHealth.", file=sys.stderr, flush=True)
        return EX_RETRYABLE
    except Fatal as exc:
        print(f"\n[web] FATAL: {exc}", file=sys.stderr, flush=True)
        return 1


def main() -> int:
    global LANE
    a = build_parser().parse_args()
    a.lane_explicit = getattr(a, "lane", None) is not None or bool(os.environ.get("WEB_LANE"))
    LANE = getattr(a, "lane", None) or os.environ.get("WEB_LANE") or (
        "mcp" if a.cmd == "mcp" else "unknown")
    try:
        return run(a)
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        # Output was piped into head/less and the reader closed early.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())
