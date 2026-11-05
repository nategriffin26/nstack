# brief.md

The brief is `$P/brief.md` in the demo production. Fill every section; a missing creative choice is a `[? default taken]` marker, a missing routine one (aspect, fps) takes the production's default silently. Every adjective becomes a number: seconds, frames, px at 1080p, hex, a named ease, a multiplier.

```markdown
# <Title>, <N> s

Idea: "<Nate's line, verbatim>" (<date>)
Purpose and viewer: <where it plays and who watches; what they know after it>
Frame: <W>×<H>, <fps> fps, <N> s, <aspect>; <loop | once>
Look: <one named aesthetic, from a1>; fence: <the decoded line, or "none">
Real material: <the product's screens, logo file, colours (hex) and type it uses, with paths>; missing: <what, and the stand-in>

## Beats

1. 0.0–2.5 s · <subject and its state> <the move, like m1 0.0–1.6 s at 1.5× slower> on <a3's surface> · <renderer>
2. 2.5–6.0 s · ...
3. 6.0–9.0 s · THE TURN: <what is revealed, changes medium, zooms out, or becomes something else> (m2) · <renderer>
4. 9.0–12.0 s · <exit or end state; the last frame holds under 1 s unless it is the payoff> · <renderer>

Camera: <move, ease, what it lands on>. Pace: <in numbers: cuts per beat, hold lengths>.

## On-screen text

| Beat | Time | Text, exactly | Type | Owner |
|---|---|---|---|---|
| 2 | 3.0–5.5 s | "Ask anything." | <family> <weight> <px at 1080p>, <hex> | board `key-phrase` |

## Sound

| Beat | What is heard | Source | Stem |
|---|---|---|---|
| 1–4 | <music bed, its character and tempo> | <kino2 score / nocturne score / a licensed file> | score |
| 2 | <effect on the landing frame> | <renderer or asset with licence> | sfx |

No narration unless the idea asks for it. Renderers deliver unmixed 48 kHz stems; `ytl film make` mixes and masters to −16 LUFS / −1.5 dBTP.

## Shots

| Shot | Beats | Seconds | Renderer | Source in shots.json |
|---|---|---|---|---|
| s01 | 1–2 | 6.0 | kino2 `<piece>` | shot, `--clip intro:landing` |

## References

- a1 refs/a1.jpg: look, <what it sets, which beat> (<url>, <channel>)
- a2 … a5, m1 … m3, u1, c1 as `references.md` lists them; every handle appears in a beat.

Assets:
- <path or url>: use as-is for <what>; <licence>

## Directions

<filled after Nate picks: the picked direction's id and what it fixed>
```

Edits after the first cut are delta notes, one line each, appended under `## Changes`: target, change, magnitude, direction, and what to keep (`beat 3: the leaf lands 0.4 s earlier; keep its ease and the rain density`).
