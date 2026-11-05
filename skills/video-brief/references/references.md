# Finding references

Adapted from blank-page's `references/finding-references.md` (StewdioAI/blank-page, MIT, Cekura, Inc.; `UPSTREAM.md`). Its finder is vendored unchanged as `~/.omp/agent/skills/video-brief/scripts/find_refs.py`, written `find_refs.py` below: run it with no arguments for the commands. It needs only Python, curl and ffmpeg. Save everything under `$P/refs/` (the production folder), named by handle: `a1.jpg`, `m2.mp4`.

## Roles

Every reference has one role, one take (what it supplies) and the beat it feeds. A file good for two roles is listed twice, each scoped. A reference with no beat is cut.

| Handle | Role | Supplies | Never supplies |
|---|---|---|---|
| a1–a5 | look | a1 overall look, a2 palette, a3 material or surface, a4 composition, a5 a detail or motif | shape of the subject, motion |
| m1–m3 | motion | m1 the main move, m2 the turn, m3 the exit or camera: mechanic, timing, easing | subject, palette, texture |
| u1 | ui | layout, component vocabulary, density, type hierarchy | brand, logo, real copy |
| c1 | copy | the specific thing to rebuild one-to-one (an artwork, a product, an app's screen) | how it moves |
| assets | used, not read | the real logo file, footage, a model, a font, a score | — |

Five stills from **one** aesthetic, never a blend; if a second aesthetic keeps winning, switch to it wholesale. Its name goes in the brief's first line. Motion references give the beats their order and timing: read each one's contact sheet (`find_refs.py sheet <clip> <out.png> 16`), take a time range, swap the subject, and state the scale (`m1 0.0–1.6 s is beat 2 at 1.5× slower, cards for the leaves`).

## The fence

When the idea names a style, a brand, a medium or attaches a reference, that word fences palette, material, type and components. It does not fence layout, scale, camera or the move, and it never applies to motion references.

1. Decode the word in one line: what Nate pictures when he says it (`claymation` = stop-motion clay, fingerprints, boil, on twos). That line is the fence.
2. Search the name itself (`find_refs.py search "<style>"` or `search "<brand domain>"`), then the decoded visual words (`channels "<word>"`).
3. For a brand or his own app, the product supplies facts: hex values, typeface, one real component, read from its code or site. A docs page or settings screen is a fact, never a composition reference.
4. A tile outside the fence does not pass, however striking.

No fence: pick the look for remarkable, not for matching the idea's words, and avoid the safe default (flat vector on white, a dark "linear" style, brushed metal) unless a sheet makes it striking.

## Search order

Stills and motion: are.na channels, then Pinterest (a web search restricted to pinterest.com, resolved with `find_refs.py pin <url>`), then primary sites. 3D objects: Sketchfab first (`find_refs.py sketchfab "<object>" $P/refs/3d`), prefer CC0 or CC-BY and record the author.

- are.na is searched by channel, never by block keyword (`channels "<query>"`, `channel <slug> $P/refs/arena 48 moving|still` for numbered contact sheets, `connections <block_id>` to branch to curators with the same eye). Stop after three channels per role.
- Motion seeds: `mo-graph-1uxjlkjqqhc` and its nested channels (`type-animation-references`, `design-moving-l9-xt3sxtne`, `motion-inspo-tfrw-gidqfw`, `ad-device-tech`, `product-video-mf4kzs1zbo0`); widen with `channels "kinetic type"`, `"motion design"`, `"transitions"`. The test for a motion reference: is the move worth copying on any subject?
- Look menu: `umbrella vis-4hvdpzvvua4`, `umbrella flat-ovcn8k0nwa0`, `umbrella form-glcjdzmigiq` list named aesthetics; `user-channels evan-collins-1522646491` lists about 240 more.

## Vetting

Download each candidate (`find_refs.py get <url> $P/refs/<handle>.<ext>`; it fixes the extension), then look at it: stills by reading the file, moving ones by their sheet. Keep it only if its role's quality is visible at 600 px or more (motion: the mechanic happens on screen as more than a cut or fade, and it is not a tutorial). Nothing passes: write `[? motion ref]` or `[? visual ref]` in the brief beside a description in words and list the queries tried. Never pass an unvetted hit.
