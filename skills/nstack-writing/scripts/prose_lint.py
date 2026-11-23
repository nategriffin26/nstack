#!/usr/bin/env python3
"""Offline deterministic prose linter for nstack-writing.

Flags mechanical AI-writing patterns, banned consultancy/promo words,
uncommon verbifications / noun-verb ambiguity stacks, sentence/paragraph
density walls, and formatting slips. Skips fenced code blocks, inline code,
blockquotes, double-quoted spans (user/source quotes), and markdown link URLs.

Usage:
    python3 prose_lint.py <file> [file ...]
    python3 prose_lint.py -               # read from stdin
    python3 prose_lint.py --json <file>

Exit codes:
    0  no high-precision flags
    1  one or more high-precision flags
    2  usage or I/O error

High-precision flags ("flag") are almost always worth fixing; review items
("review") are cues for editorial judgment, never hard bans.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Finding:
    file: str
    line: int
    severity: str  # "flag" | "review"
    rule: str
    match: str
    fix: str


# High-precision AI/consultancy/promotional filler vocabulary.
AI_VOCAB = [
    "delve", "delves", "delving", "delved",
    "tapestry", "testament", "pivotal", "paramount",
    "multifaceted", "nuanced", "seamless", "seamlessly",
    "transformative", "groundbreaking", "game-changing", "game-changer",
    "cutting-edge", "synergy", "holistic", "paradigm",
    "utilize", "utilizes", "utilizing", "utilized",
    "leverage", "leverages", "leveraging", "leveraged",
    "underscore", "underscores", "underscoring", "underscored",
    "showcase", "showcases", "showcasing", "showcased",
    "foster", "fosters", "fostering", "fostered",
    "garner", "garners", "garnering", "garnered",
    "embark", "embarks", "embarking", "embarked",
    "intricacies", "interplay", "commendable", "meticulous", "meticulously",
    "vibrant", "enduring", "whilst", "playbook", "north star",
    "table stakes", "unleash", "supercharge", "supercharging",
]
AI_VOCAB_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in AI_VOCAB) + r")\b", re.I
)

# Promotional adjectives that usually hide missing numbers/evidence (review, not flag).
PROMO_WORDS_RE = re.compile(
    r"\b(robust|powerful|elegant|comprehensive|innovative|unlock|unlocks|unlocking|moat|ecosystem|landscape)\b",
    re.I,
)

# High-precision stock openers, throat-clearing, chatbot leftovers, and announcement frames.
HIGH_PRECISION_PHRASES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "chatbot-residue",
        re.compile(
            r"\b(I hope this helps|Great question|Let's dive in|Let's unpack|Feel free to|Happy to help|As an AI|As of my knowledge cutoff)\b",
            re.I,
        ),
        "Delete chatbot boilerplate.",
    ),
    (
        "throat-clearing",
        re.compile(
            r"\b(It'?s worth noting(?: that)?|It is worth noting(?: that)?|Here'?s the thing[,:]|Let me be clear[,:]|Let that sink in|The bottom line is|In today'?s fast-(?:paced|moving) (?:world|landscape)|Needless to say|At the end of the day|In conclusion,|To summarize,|In summary,)\b",
            re.I,
        ),
        "Delete the announcement and start with the claim.",
    ),
    (
        "announced-importance",
        re.compile(
            r"\b(This matters because|The key insight is|The real (?:gap|story|question|issue|reason|problem|win|risk|test) is|What nobody tells you|The part everyone misses|Crucially,|Notably,|Importantly,|Interestingly,)\b",
            re.I,
        ),
        "Show the consequence or concrete fact directly.",
    ),
    (
        "significance-inflation",
        re.compile(
            r"\b(marks? a (?:pivotal|turning|defining|watershed) (?:moment|point|shift)|a testament to|plays? a (?:pivotal|crucial|vital|key) role in|stands? as a (?:beacon|reminder|testament)|cannot be overstated)\b",
            re.I,
        ),
        "State what changed with a number, date, or observable effect.",
    ),
    (
        "vague-attribution",
        re.compile(
            r"\b(experts agree|studies show|research shows|industry leaders say|best practice is|many engineers find|community reports note|widely regarded as)\b",
            re.I,
        ),
        "Name and link the source, label as your inference, or cut it.",
    ),
    (
        "stacked-hedge",
        re.compile(
            r"\b(may potentially|might possibly|could potentially|likely could|seemingly appears|arguably may|tends to often)\b",
            re.I,
        ),
        "State the single real uncertainty once.",
    ),
    (
        "moralized-precision",
        re.compile(
            r"\b(honest numbers|honestly speaking|calibrated assessment|smoking gun)\b",
            re.I,
        ),
        "Name the actual property (measured on device, held-out set, p95, exact cause).",
    ),
    (
        "process-leak",
        re.compile(
            r"\b(as requested|per our (?:discussion|conversation)|as we discussed|in the previous turn|earlier in this (?:chat|session))\b",
            re.I,
        ),
        "Write for a reader who never saw the chat; state the fact or constraint itself.",
    ),
]

# Sentence-level patterns (review unless pileup).
NEGATIVE_PARALLELISM_RE = re.compile(
    r"\b(?:It'?s|It is|It isn'?t|This is|This isn'?t|That'?s|That is|That isn'?t|They'?re|They aren'?t|We'?re|We aren'?t)\s+(?:not\s+)?(?:just\s+|merely\s+|only\s+|simply\s+)?[^.?!;]{2,60}(?:[,;—–]|\s+—)\s*(?:it'?s|it is|this is|that'?s|that is|but\s+(?:a|an|the|rather)?)\b",
    re.I,
)
CONTRAST_TAIL_RE = re.compile(
    r",\s+not\s+(?:a|an|the|by|from|in|for|to|with|just|merely|simply)\s+[^.?!]{2,50}[.?!]$",
    re.I,
)
PARTICIPLE_TAIL_RE = re.compile(
    r",\s+(?:highlighting|underscoring|demonstrating|ensuring|enabling|showcasing|reflecting|making it|creating a|leaving the|providing a|turning it into|allowing (?:teams|users|you) to)\b[^.?!]*[.?!]?$",
    re.I,
)
COPULA_AVOIDANCE_RE = re.compile(
    r"\b(serves as|stands as|functions as|acts as a|boasts a)\b",
    re.I,
)
FALSE_RANGE_RE = re.compile(
    r"\bFrom\s+[a-z][a-z\s-]{2,30}\s+to\s+[a-z][a-z\s-]{2,30},",
)
SELF_ANSWERED_Q_RE = re.compile(
    r"(?:^|\.\s+)(?:The result|The catch|The problem|The reason|The fix|The takeaway|So what changed|Why does this matter|What does this mean)\?\s+\S",
    re.I,
)
DRAMATIC_FRAGMENT_RE = re.compile(
    r"(?:^|\.\s+|[!?]\s+)(That'?s it\.|That'?s the whole (?:thing|story|point)\.|Full stop\.|Period\.|Simple as that\.)",
    re.I,
)
METAPHOR_HABIT_RE = re.compile(
    r"\b(load-bearing|buys (?:us|you|nothing|little)|quietly|lands well|pays a tax|tax on|guardrail against|north star)\b",
    re.I,
)

# Uncommon verbifications / Claude-Astra noun-verb ambiguity tells.
# Catches verb uses of words native English normally uses as nouns in prose
# (e.g. "the root sizes the work", "the check witnesses the invariant",
# "it gates the merge", "we surfaced the gap", "this impacts latency").
UNCOMMON_VERB_RE = re.compile(
    r"\b(?:"
    r"(?:re-?sizes|sizes(?!\s+(?:of|in|for|are|were|stay|win|range|vary|and|or|\W*$)))\s+(?:the|a|an|each|every|this|that|its|our|his|their|work|fix|task|ask|buffer|pool|cache|change)"
    r"|(?:witnesses|witnessed)\s+(?:the|a|an|that|this|its|each)\b"
    r"|(?:gates|gated)\s+(?:the|a|an|each|every|this|that|release|merge|deploy|build|check|write)\b"
    r"|(?:surfaces|surfaced|surfacing)\s+(?:the|a|an|each|every|this|that|errors|bugs|gaps|risks|blockers|issues)\b"
    r"|(?:impacts|impacted|impacting)\s+(?:the|a|an|this|that|our|his|user|latency|cost|speed|performance)\b"
    r"|(?:anchors|anchored)\s+(?:the|a|an|this|that|each|every)\b"
    r"|(?:hardens|hardened)\s+(?:the|a|an|this|that)\b"
    r"|(?:authorizes|underwrites|invoices|operationalizes|productizes)\b"
    r")\b",
    re.I,
)

# Ambiguous noun/verb stack: three or more polysemous audit/agent words in one 8-word window.
AMBIGUOUS_STACK_WORDS = {
    "target", "witness", "claim", "audit", "check", "flag", "gate",
    "probe", "patch", "guard", "lease", "scope", "frame", "slice", "pass",
}

# Bold-lead bullet: "- **Something:** rest" or "- **Something**: rest" or "- **Something.** rest"
BOLD_LEAD_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\*\*[^*]{2,60}[:.—–-]?\*\*(\s*[:.—–-]|\s+[A-Z])")
# Title Case heading check
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "via", "with"}

# Slogan / explaining headings
EXPLAINING_HEADING_RE = re.compile(
    r"^#{1,6}\s+(?:Why|Why it matters|How it works|What this means|Who it'?s for|The verdict|Verdict:.*|Key takeaways|Summary|TL;?DR|Conclusion|Next steps and challenges|Challenges and next steps)\s*$",
    re.I,
)

# Inline arrow chain used as sentence glue (not menu › or numeric 10% → 2%)
SENTENCE_ARROW_RE = re.compile(r"[A-Za-z]{3,}\s*(?:→|->)\s*[A-Za-z]{3,}\s*(?:→|->)\s*[A-Za-z]{3,}")

# Filler intensifiers
INTENSIFIER_RE = re.compile(r"\b(genuinely|truly|actually|literally|dramatically|fundamentally|remarkably)\b", re.I)

# Vague quantifiers where a concrete number often belongs
VAGUE_QTY_RE = re.compile(r"\b(several|numerous|a range of|a variety of|a number of|various|many different)\b", re.I)


def strip_inline_code_and_urls(line: str) -> str:
    line = re.sub(r"`[^`]*`", " CODE ", line)
    line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"https?://\S+", " URL ", line)
    return line


def strip_inline_quotes(line: str) -> str:
    """Remove double-quoted spans so quoted user/source text is not flagged."""
    line = re.sub(r"“[^”]*”", " QUOTE ", line)
    line = re.sub(r'"[^"]*"', " QUOTE ", line)
    return line


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])", text) if s.strip()]


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9'’-]*", text)


def check_title_case_heading(line: str) -> bool:
    m = re.match(r"^#{1,6}\s+(.+)$", line)
    if not m:
        return False
    title = strip_inline_code_and_urls(m.group(1)).strip()
    words = [w.strip(".,:;!?()\"'") for w in title.split()]
    words = [w for w in words if w and w.isalpha() and not w.isupper()]
    if len(words) < 4:
        return False
    content_words = [w for w in words[1:] if w.lower() not in SMALL_WORDS]
    if len(content_words) < 3:
        return False
    caps = sum(1 for w in content_words if w[0].isupper())
    return caps / len(content_words) >= 0.75


def lint_text(text: str, filename: str) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    lines = text.splitlines()

    in_fence = False
    in_frontmatter = False
    bold_lead_lines: list[int] = []
    em_dash_lines: list[int] = []
    neg_par_lines: list[int] = []
    metaphor_hits: list[tuple[int, str]] = []
    intensifier_hits: list[tuple[int, str]] = []
    vague_qty_hits: list[tuple[int, str]] = []

    prose_blocks: list[tuple[int, str]] = []
    cur_block_start = 0
    cur_block: list[str] = []

    def flush_block():
        nonlocal cur_block, cur_block_start
        if cur_block:
            prose_blocks.append((cur_block_start, " ".join(cur_block)))
            cur_block = []

    for idx, raw in enumerate(lines, start=1):
        stripped = raw.strip()

        # Skip YAML frontmatter at top of file
        if idx == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        # Skip fenced code blocks
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_block()
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # Skip blockquotes (quoted text / Nate's words are never edited)
        if stripped.startswith(">"):
            flush_block()
            continue

        # Skip empty lines, markdown tables, horizontal rules, and HTML tags
        if not stripped or stripped.startswith("|") or re.match(r"^[-*_]{3,}$", stripped) or stripped.startswith("<"):
            flush_block()
            continue

        # Headings
        if stripped.startswith("#"):
            flush_block()
            if EXPLAINING_HEADING_RE.match(stripped):
                findings.append(Finding(
                    filename, idx, "review", "explaining-heading", stripped,
                    "Name the topic directly instead of explaining the explanation or stating a slogan.",
                ))
            elif check_title_case_heading(stripped):
                findings.append(Finding(
                    filename, idx, "review", "title-case-heading", stripped,
                    "Use sentence case in headings.",
                ))
            continue

        clean = strip_inline_code_and_urls(raw)
        check_text = strip_inline_quotes(clean)

        # Track bold-lead bullets
        if BOLD_LEAD_BULLET_RE.match(raw):
            bold_lead_lines.append(idx)

        # Accumulate plain prose paragraphs (non-list)
        if re.match(r"^\s*(?:[-*+]|\d+\.)\s+", raw):
            flush_block()
        else:
            if not cur_block:
                cur_block_start = idx
            cur_block.append(clean.strip())

        # Line-level high-precision checks (quote-stripped)
        for m in AI_VOCAB_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "flag", "ai-vocabulary", m.group(0),
                "Replace with the plain everyday verb/noun or state the concrete evidence.",
            ))

        for rule, pat, fix in HIGH_PRECISION_PHRASES:
            for m in pat.finditer(check_text):
                findings.append(Finding(filename, idx, "flag", rule, m.group(0), fix))

        for m in UNCOMMON_VERB_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "flag", "uncommon-verb", m.group(0),
                "Avoid verbifying nouns or uncommon parts of speech; use the plain verb (e.g. 'sets the size of', 'blocks', 'proves', 'affects').",
            ))

        for m in SENTENCE_ARROW_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "review", "arrow-glue", m.group(0),
                "Use verbs for prose chains; keep arrows for menu paths or value deltas (10% → 2%).",
            ))

        for m in COPULA_AVOIDANCE_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "review", "copula-avoidance", m.group(0),
                "Use 'is', 'are', or 'has' instead of 'serves as' / 'stands as'.",
            ))

        for m in FALSE_RANGE_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "review", "false-range", m.group(0),
                "Check if 'From X to Y' is a real scale; otherwise list the items plainly.",
            ))

        for m in DRAMATIC_FRAGMENT_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "flag", "dramatic-fragment", m.group(0),
                "Cut the filler punchline or fold it into a real sentence.",
            ))

        for m in SELF_ANSWERED_Q_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "review", "self-answered-question", m.group(0).strip(),
                "State the answer directly without staging a question first.",
            ))

        for m in PROMO_WORDS_RE.finditer(check_text):
            findings.append(Finding(
                filename, idx, "review", "promotional-word", m.group(0),
                "Replace adjective praise with a concrete number, mechanism, or test result.",
            ))

        if "—" in check_text:
            em_dash_lines.append(idx)

        for m in METAPHOR_HABIT_RE.finditer(check_text):
            metaphor_hits.append((idx, m.group(0)))

        for m in INTENSIFIER_RE.finditer(check_text):
            intensifier_hits.append((idx, m.group(0)))

        for m in VAGUE_QTY_RE.finditer(check_text):
            vague_qty_hits.append((idx, m.group(0)))

        # Sentence-level checks on this line
        for sent in split_sentences(check_text):
            if NEGATIVE_PARALLELISM_RE.search(sent):
                neg_par_lines.append(idx)
                findings.append(Finding(
                    filename, idx, "review", "negative-parallelism", sent[:110],
                    "State the positive claim on its own; keep 'not X' only if a reader would plausibly assume X.",
                ))
            elif CONTRAST_TAIL_RE.search(sent):
                findings.append(Finding(
                    filename, idx, "review", "contrast-tail", sent[:110],
                    "Cut the trailing ', not ...' contrast unless it prevents a likely misreading.",
                ))

            m_part = PARTICIPLE_TAIL_RE.search(sent)
            if m_part:
                findings.append(Finding(
                    filename, idx, "review", "participle-tail", m_part.group(0).strip()[:100],
                    "End the sentence before the participle tail, or state the concrete causal link.",
                ))

            # Ambiguous noun/verb stack: 3+ distinct polysemous words in an 8-word window
            toks = [t.lower().rstrip("s") for t in word_tokens(sent)]
            for i in range(max(0, len(toks) - 7)):
                win = toks[i : i + 8]
                hits = [w for w in win if w in AMBIGUOUS_STACK_WORDS]
                if len(set(hits)) >= 3:
                    findings.append(Finding(
                        filename, idx, "review", "ambiguous-pos-stack",
                        " ".join(win),
                        "Dense stack of noun/verb-ambiguous words; unpack into plain actor + verb + object.",
                    ))
                    break

    flush_block()

    # Document-level density and repetition checks
    all_words = []
    sent_lengths = []
    long_sents: list[tuple[int, int, str]] = []
    long_paras: list[tuple[int, int]] = []

    for start_line, para in prose_blocks:
        sents = split_sentences(para)
        if len(sents) > 6:
            long_paras.append((start_line, len(sents)))
        for s in sents:
            ws = word_tokens(s)
            if ws:
                sent_lengths.append(len(ws))
                all_words.extend(ws)
                if len(ws) > 35:
                    long_sents.append((start_line, len(ws), s[:100]))

    total_words = len(all_words)

    if len(bold_lead_lines) >= 3:
        findings.append(Finding(
            filename, bold_lead_lines[0], "review", "bold-lead-list",
            f"{len(bold_lead_lines)} bold-lead bullets (lines {', '.join(map(str, bold_lead_lines[:5]))})",
            "Drop bold lead-ins that the sentence restates; open with the subject directly.",
        ))

    em_limit = max(2, total_words // 200)
    if len(em_dash_lines) > em_limit:
        findings.append(Finding(
            filename, em_dash_lines[0], "review", "em-dash-overuse",
            f"{len(em_dash_lines)} lines with em dashes (words: {total_words})",
            "Replace parenthetical em dashes with periods, commas, or separate sentences.",
        ))

    if len(neg_par_lines) >= 3:
        findings.append(Finding(
            filename, neg_par_lines[0], "flag", "negative-parallelism-pileup",
            f"{len(neg_par_lines)} 'not X, Y' constructions in one piece",
            "Keep at most one real correction; rewrite the rest as direct positive claims.",
        ))

    if len(metaphor_hits) >= 2:
        findings.append(Finding(
            filename, metaphor_hits[0][0], "review", "recurring-metaphor",
            ", ".join(f"{w} (L{ln})" for ln, w in metaphor_hits[:5]),
            "One apt metaphor is fine; cut repeated pet metaphors.",
        ))

    if len(intensifier_hits) >= 3:
        findings.append(Finding(
            filename, intensifier_hits[0][0], "review", "filler-intensifiers",
            ", ".join(f"{w} (L{ln})" for ln, w in intensifier_hits[:5]),
            "Cut filler intensifiers ('genuinely', 'truly', 'actually'); let the fact carry the weight.",
        ))

    if len(vague_qty_hits) >= 2:
        findings.append(Finding(
            filename, vague_qty_hits[0][0], "review", "vague-quantifiers",
            ", ".join(f"{w} (L{ln})" for ln, w in vague_qty_hits[:5]),
            "Give the exact count or range when known instead of 'several' / 'a range of'.",
        ))

    for ln, n_sents in long_paras:
        findings.append(Finding(
            filename, ln, "review", "long-paragraph",
            f"{n_sents} sentences in one paragraph",
            "Split at one idea per paragraph (aim for 1–4 sentences; over 6 is usually two ideas).",
        ))

    for ln, n_words, snippet in long_sents:
        findings.append(Finding(
            filename, ln, "review", "long-sentence",
            f"{n_words} words: {snippet}…",
            "Split into shorter sentences (target ~15–22 words; cut stacked clauses).",
        ))

    if len(sent_lengths) >= 6:
        stdev = statistics.stdev(sent_lengths)
        median_len = statistics.median(sent_lengths)
        if stdev < 3.0:
            findings.append(Finding(
                filename, 1, "review", "uniform-rhythm",
                f"sentence length stdev={stdev:.1f}, median={median_len:.0f} across {len(sent_lengths)} sentences",
                "Vary sentence length so short claims and longer explanations alternate naturally.",
            ))
    else:
        median_len = statistics.median(sent_lengths) if sent_lengths else 0
        stdev = 0.0

    findings.sort(key=lambda f: (f.line, 0 if f.severity == "flag" else 1, f.rule))

    stats = {
        "words": total_words,
        "sentences": len(sent_lengths),
        "paragraphs": len(prose_blocks),
        "median_sentence_words": round(median_len, 1),
        "sentence_stdev": round(stdev, 1),
        "flags": sum(1 for f in findings if f.severity == "flag"),
        "reviews": sum(1 for f in findings if f.severity == "review"),
    }
    return findings, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic prose linter for nstack-writing.")
    ap.add_argument("files", nargs="+", help="Markdown or text files to lint ('-' for stdin)")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args()

    all_findings: list[Finding] = []
    all_stats: dict[str, dict] = {}

    for target in args.files:
        try:
            if target == "-":
                text = sys.stdin.read()
                label = "<stdin>"
            else:
                text = Path(target).read_text(encoding="utf-8")
                label = target
        except OSError as e:
            print(f"error reading {target}: {e}", file=sys.stderr)
            return 2

        findings, stats = lint_text(text, label)
        all_findings.extend(findings)
        all_stats[label] = stats

    if args.json:
        print(json.dumps({
            "stats": all_stats,
            "findings": [asdict(f) for f in all_findings],
        }, indent=2))
    else:
        for label, st in all_stats.items():
            print(
                f"{label}: {st['words']}w, {st['sentences']}s (median {st['median_sentence_words']}w, stdev {st['sentence_stdev']}), "
                f"{st['flags']} flag(s), {st['reviews']} review(s)"
            )
            for f in (x for x in all_findings if x.file == label):
                print(f"  L{f.line:<4d} [{f.severity:<6s}] {f.rule}: {f.match}")
                print(f"          fix: {f.fix}")

    return 1 if any(f.severity == "flag" for f in all_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
