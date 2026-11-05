---
name: video-brief
description: Make a short film, app demo or motion piece from a one-line idea, with directions Nate picks. Writes the brief (look and motion references, beats with a turn, exact on-screen text, sound, the renderer for each beat: kino2, nocturne, film-lab, Blender, HyperFrames), shows three directions as stills, and has a fresh critic review the render. Not for YouTube explainers or new kino2 mediums and styles.
---

# Video brief

Every new film starts here: a one-line idea becomes `brief.md` in a youtube-lab demo production, three directions shown as real stills for Nate to pick, each renderer's own input, and one render assembled by `ytl film make` and reviewed by a critic that never saw the code. The renderers stay as they are; the brief, the shot file each renderer writes, and youtube-lab's HyperFrames assembly join them.

## Use when
- A one-line idea for a video, film, app demo, title sequence or motion piece: "make a 15 second film about X", "a demo video for <app>".
- A film that mixes renderers: a kino2 passage, a nocturne score, a generated plate, type over all of it.
- "Make one like this" with a reference video.

## Not for
- YouTube explainers with narration (12–25 min): youtube-lab's `film-producer`.
- Changing an existing kino2 piece or adding a kino2 medium or style: kino2's `kino-film`. A nocturne film of one whole score: run nocturne; the score is its brief.
- film-lab's own productions: its `film-director`. Here film-lab only supplies plates for beats the brief gives it.

## The bar
- "Can we combine these with stuff we have already done or in a new project fresh? For amazing and awesome videos from models in all regards and for all uses." (2026-11-05)
- "Build on what I have, no Raea" (2026-11-05, his pick of option A in the video-stack research)
- "one-line idea -> brief with look references, motion references, numbered beats with a turn, exact on-screen text, sound plan, which renderer owns each beat; ... three directions shown as stills on one HTML page for Nate to pick; the builder never grades its own render (a fresh critic reviews frames)." (2026-11-05, the build brief)
- "make the coolest 2 minite video ive ever seen, lean into breathtaking animation and style and let the music and noise be ingrained in really cool ways. literally take my breath away with thr end product." (2026-09-25, kino2)
- His verdict on an earlier agent-made film: "motion was not thought out, animation was lacking and didn't feel purposeful, fonts and layout and drawn scenes looked like ai slop and not artful." (recorded 2026-10-27, youtube-lab)

## Steps

1. **Open the production.** From `~/Projects/youtube-lab`: `uv run ytl film new <slug> --title "…" --kind demo`. Every video-brief film is assembled there, so the brief, refs, directions and shots live in one folder `$P = productions/<slug>/`. A demo is timed by its shots' `seconds`, with no narration. Below, `$S` is this skill's folder, `~/.omp/agent/skills/video-brief`.

2. **Real material before any direction.** A film about a product is made of the product: its real screens captured at their size with real data, its logo file (never redrawn), the hex colours and typefaces its code declares. List each with its path in the brief. If the subject is Nate's own and something is missing, say so and name the stand-in. Every outside asset gets a source and licence line.

3. **Reference video (only when Nate gives one).** Measure it with HyperFrames' free local commands, which need no account and make no network call (checked on 0.9.16, 2026-11-05): `npx --yes hyperframes@0.9.16 telemetry disable` once, then `measure probe <clip>` (size, fps, duration, sound), `measure cuts <clip>` (cut times and shots), `measure events --map <clip>` (change and hold windows, sound onsets), `measure look <clip>` (brightness, contrast, saturation, warmth) and `measure frames --every 2 --out $P/refs/<name> <clip>` (frame sheets). Number the beats yourself from the sheets and windows; the tool reports holds and changes, not beats. `hyperframes diff <reference> <render>` later scores a remake against it. Never `/reverse-any-video` (a Pro feature that sends painted and people layers to paid HeyGen generation), and never `hyperframes auth`, sign-in, billing, publish or cloud.

4. **References, one job each.** Read `references/references.md`. Five stills from one aesthetic (look, palette, material, composition, detail) and three moving references (the main move, the turn, the exit or camera), found with `$S/scripts/find_refs.py` and saved in `$P/refs/`. A named style or brand is a fence: it holds palette, material and type inside that style; it never fences layout, camera or motion. Each reference names the beat it feeds and exactly what is taken.

5. **Write the brief.** Fill `references/brief.md` into `$P/brief.md`. The rules that change the film:
   - **The turn.** One beat where something is revealed, changes medium, zooms out to a larger whole or becomes something else, and it is the biggest beat. Enter, animate, hold is not a film.
   - **Numbers, not adjectives** (HyperFrames' spec rule): seconds for every beat, a named ease, px at 1080p, hex, multipliers. "Snappy" is not a spec.
   - **The mechanism, not the adjective** (blank-page): "the current image peels from a corner to reveal the next one underneath", not "an editorial transition".
   - **Exact on-screen text**: every string verbatim with its beat, time, type and owner. Text and UI are drawn in code (a HyperFrames board or overlay, or kino2 lettering), never by a video model.
   - **App demos**: the real UI rebuilt in HTML from the captures, "Three to five beats and a payoff, 10 to 16 seconds" (stageshow), one thing happening at a time, every cursor move with a cause.
   - **Sound plan** per beat: what is heard, which renderer or licensed file makes it, as which stem. Renderers deliver unmixed 48 kHz stems and never normalise; `ytl film make` masters to −16 LUFS / −1.5 dBTP.
   - **One owner per beat**, chosen from `references/renderers.md`.

6. **Three directions, one page.** Three genuinely different films (motion language, material or structure, not colour), at least one reaching past Nate's references and current style. Each is 2–4 stills rendered by the beat's owning renderer at the film's frame size (commands in `references/renderers.md`): no mockups, no generated images standing in for a code-drawn beat. Put them in `$P/review/directions/`, write `$P/review/directions.json` (one question, id `direction`, an option per direction with `label`, a one- or two-sentence `note` and its `media`, and your `recommended`), run `uv run ytl film review <slug>` and send Nate the phone link it prints, with your recommendation. His pick arrives in `$P/review/notes.json` as a `directions` note, `Picks — direction: <id>`; record it under `## Directions` in the brief. A pick stands. Work that does not depend on the pick (material, refs, renderer setup) keeps going meanwhile.

7. **Translate, and nothing more.** The brief becomes `$P/shots.json` (each shot's `seconds`, `source`, `overlays`, `transition`) and each renderer's own input: kino2 `events()` in `pieces/<piece>/film.mjs`, a nocturne score with `--theme`, `--seed`, `--start/--end`, a film-lab `shots.json`, a youtube-lab scene program, a board component's props. No new schema or wrapper.

8. **Make.** `uv run ytl film make <slug>` runs each missing shot's `make`, checks every shot file, renders 3D shots, mixes the stems to the master and renders. Check a renderer's shot on its own with `uv run ytl film shot-check <file>`; it must print `ok`.

9. **A fresh critic, never the builder.** Take one frame per beat (`ffmpeg -ss <beat middle> -i <render> -frames:v 1 $P/review/critic/beat-<n>.png`), one more at the middle of every on-screen string, and a sheet (`python3 $S/scripts/find_refs.py sheet <render> $P/review/critic/sheet.png 16`). Spawn a new `opus` agent (Nate's roster sends anything visual to opus) that sees only `brief.md`, `refs/`, those frames, the sheet and `audio/measurements.json`, never the code or this conversation: fresh eyes are the requirement. It checks: each beat on screen at its time with its move; every string exact, character by character; the turn landing as the biggest beat; the look inside the fence; craft (cropped or covered text, collisions, empty frames, fallback fonts, flat energy); the sound against the plan. Each finding names a beat, a time and a frame. Triage each in one line (take, backlog or skip, with the reason) in `$P/review/critique-<n>.md`, fix what you take, re-make. Every cut Nate sees has passed a fresh critic and your own look at the frames; stop when the findings are cosmetic.

10. **Nate's notes become delta notes.** The cut goes on the same review page; his timestamped notes come back in `notes.json`. Each becomes one line under `## Changes` in the brief: target, change, magnitude, direction, and what to keep ("beat 3: the leaf lands 0.4 s earlier; keep its ease").

## Money and accounts
film-lab generation (`film image`, `film video …`) is paid per image or per second of footage (image models and MiniMax H3 on fal). Estimate with `--dry-run`, get Nate's yes on the amount, and spend only through film-lab's ledger and budget. A paid command never goes in a shot's `make`; `film cut` over existing takes is free and may. No new accounts or sign-ins (HeyGen, ElevenLabs), and nothing is published; Nate uploads.

## Light version
One short card or a single shot in one renderer: the brief with its references, 1–3 beats with a turn and the exact text; the three directions only when the look is still open (a style Nate already picked stands); make; the critic on its frames. The critic is never skipped.

## Pitfalls
- Text or UI inside generated footage: a model right on 99% of frames still ruins about seven 200-frame clips in eight (research synthesis, "Model-generated footage"). Draw type and UI in code over the plate.
- Screenshots stitched with transitions read as cheap; the real UI rebuilt in code reads as premium (research synthesis, "First uses").
- Every shot must match the production's fps and size; film-lab cuts at 24 fps unless told: `uv run film cut <slug> --fps <production fps>`.
- A whole nocturne render has a 4 s title pre-roll and a 6 s outro; render a `--start/--end` window for a beat.
- Blender runs as PyPI `bpy` through youtube-lab; `/Applications/Blender.app` hangs at launch on this Mac.
- A 3D shot in a demo production carries no `beats` (they anchor to narration, which a demo lacks).
- blank-page's defaults (white background, about 5 s loops, Stewdio files) are a social-clip house style, not Nate's; only its method is used here.

## Examples
- `~/Projects/youtube-lab/productions/stack-test/`: a working demo production, 18 s at 24 fps, with a kino2 clip, a nocturne window, a film-lab cut and two boards; `uv run ytl film make stack-test` renders it. Learn the `shots.json` sources and `make` commands from it; do not copy its subject, copy or renderer choices, which were picked to exercise the stack, not to make a film.

## References
- `references/brief.md`: the `brief.md` template. Read before writing the brief.
- `references/references.md`: reference roles, the fence, where to search, vetting. Read before step 4.
- `references/renderers.md`: which renderer owns which beat, its still and shot commands, its `shots.json` source, its cost. Read when assigning beats and in steps 6–8.
- `scripts/find_refs.py`: blank-page's reference finder (MIT; `UPSTREAM.md`, `LICENSE`). Run with no arguments for its commands.

## Provenance
- Nate's request and pick: video-stack research, `~/Projects/video-stack-wave/local/research/video-stack-2026-11/SYNTHESIS.md` ("Planning in front of every pipeline", "The shared contract", "First build") and `RepoMap.md` (2026-11-05).
- Built in the video-stack-build session of 2026-11-05 with the shot-file contract (`~/Projects/youtube-lab/src/ytlab/film/shot.schema.json`) and the demo production kind (`src/ytlab/film/model.py`). Sources: `UPSTREAM.md`.
- Written before the first film made with it; revise from that film's trace.
