# Renderers: who owns a beat, and how it reaches the production

Each beat has one owner. A renderer draws its beats natively and hands over a frozen shot with a shot file (youtube-lab `src/ytlab/film/shot.schema.json`); youtube-lab's HyperFrames step places the shots, mixes their stems and masters at −16 LUFS / −1.5 dBTP. Never render one beat in two renderers to compare them: two engines drift, and the brief already chose.

Paths below: `$P` is the production folder, `~/Projects/youtube-lab/productions/<slug>`. A shot source's `file` is relative to `$P`, normally `shots/<id>/<file>`. Render every shot at the production's fps and size (`production.json`). A working example with a kino2 clip, a nocturne window, a film-lab cut and two boards: `productions/stack-test/shots.json`.

## Which renderer for which beat

| Beat needs | Owner | Why |
|---|---|---|
| A drawn world in a named medium (ink, gouache, watercolour, screen print, impasto oil, phosphor vector, WebGL light), drawn lettering, sound composed with the picture | kino2 | 13 pieces of code-drawn films; seek-exact frames; sound scheduled in the page at 48 kHz |
| Music shown as engraved notation, a score playing | nocturne | MusicXML in, engraved film and synthesised score out, sample-accurate |
| Real-looking places, people, objects, b-roll, a hero moment | film-lab (generated, paid) | Blender previz locks framing, an image model the look, MiniMax H3 the motion |
| 3D objects or spaces built in code, products, mechanisms, diagrams in depth | Blender plate (youtube-lab scene program) | free, exact geometry, cached renders |
| Type, titles, UI, charts, captions, lower thirds, any exact string over another shot | HyperFrames board or overlay (youtube-lab) | HTML text is exact; generated video is not |

Generated footage never carries exact text, UI or rigid geometry: put those in a board or overlay over the plate.

## kino2 (`~/Projects/kino2`)

- Input: `pieces/<piece>/film.mjs`, an ordinary object with `events()` (named beats in seconds), `controls`, `sound`, and its own `fps` and size, which must match the production's. Before authoring, read kino2's `.omp/skills/kino-film/SKILL.md` and README "Author a film". Each brief beat becomes a named event.
- Directions stills: `bun tools/render.mjs <piece> --frame 0,130,216 --out <dir>` (several frames, one browser); `--strip events` for one labelled frame per event. Add `--gpu` for WebGL pieces.
- Shot: `bun tools/render.mjs <piece> --clip <a>:<b> --out $P/shots/<id>` (ends are frames or event names; with its sound) or `--video`. The `render.json` it writes is the shot file, with the stem `clip-a-b.wav` or `mix.wav`.
- Source: `{"kind": "shot", "file": "shots/<id>/render.json", "in": 0.0, "make": {"cwd": "~/Projects/kino2", "run": ["bun", "tools/render.mjs", "<piece>", "--clip", "<a>:<b>", "--out", "<absolute $P>/shots/<id>"]}}`
- Cost: free; CPU time.

## nocturne (`~/Projects/nocturne`, binary `target/release/nocturne`)

- Input: a score (`.musicxml`, `.xml`, `.mxl`); the score is that beat's brief. Choices: `--theme nocturne|ivory`, `--seed N` (camera shots, sparks), `--start/--end` (a window, audio trimmed to match), `--quality final` (1920×1080, 16 samples).
- Directions stills: `nocturne <score> --still <seconds> -o <file>.png --theme <t> --seed <n> --quality final`.
- Shot: `nocturne <score> --start <a> --end <b> --theme <t> --seed <n> --quality final --size <W>x<H> --fps <fps> -o $P/shots/<id>/<name>.mp4` writes `<name>.shot.json` and the unmixed `<name>.score.wav` beside it. A whole-piece render has a 4 s title pre-roll and a 6 s outro; take a window for a beat. In a `make`, run `./target/release/nocturne` with `cwd` `~/Projects/nocturne`.
- Cost: free; GPU time.

## film-lab (`~/Projects/film-lab`): generation is paid, the cut is free

- Generation runs under film-lab's own `film-director` skill (previz, keyframes, H3 motion, ledger, budget). Every paid call (`film image`, `film video …`) goes through `--slug <slug> --shot <id>` with `--dry-run` first; spending needs Nate's approval of the amount. A paid command never goes in a `make`.
- Directions stills: free previz (`uv run film previz <slug> <shot> --res 1920 --no-video`); generated keyframes cost (about $0.12 a still at 2K).
- Shot: `uv run film cut <slug> --fps <fps> --out $P/shots/<id>/cut.mp4` cuts the existing takes in `edit/edl.json` with ffmpeg (free) and writes `cut.shot.json` and `cut.audio.wav` beside it. film-lab defaults to 24 fps, so always pass the production's fps.
- Source: `{"kind": "shot", "file": "shots/<id>/cut.shot.json", "in": <seconds>, "make": {"cwd": "~/Projects/film-lab", "run": ["uv", "run", "film", "cut", "<slug>", "--fps", "<fps>", "--out", "<absolute $P>/shots/<id>/cut.mp4"]}}`

## Blender plates (youtube-lab)

- Input: a scene program `$P/scenes/<scene>.py` (see youtube-lab `blender/README.md`; `scenes/world.py` holds the film's shared look). Blender runs as PyPI `bpy` through youtube-lab, never `/Applications/Blender.app`, which hangs at launch on this Mac.
- Directions stills: `uv run ytl film render3d <slug> --shot <id> --quality still`.
- Source: `{"kind": "3d", "scene": "<scene>", "take": "<take>", "params": {…}}`; `ytl film make` runs `render3d` for it. In a demo production a 3D shot carries no `beats`.
- Cost: free; EEVEE final at 1080p measured 1.9–4.5 s a frame (youtube-lab `film-producer`).

## HyperFrames boards and overlays (youtube-lab)

- A full-frame board: `{"kind": "board", "component": "<name>", "props": {…}}`, where `<name>` is a file in `src/ytlab/film/web/components/` (title-card, end-credits, key-phrase, chat-box, step-sequence, bar-chart, line-chart, comparison, quote-card, image-grid and others; read the component for its props). Text over another shot: a per-shot `overlays` entry `{"component", "props", "at", "until"}`.
- A UI that must move like the real app is rebuilt in HTML from captures of the real app at the same size, with its real strings, colours, type and icons: a believable product shown simply, "Three to five beats and a payoff, 10 to 16 seconds" (Benji Taylor's stageshow). A component that does not exist yet is added to `web/components/` in youtube-lab.
- Directions stills: `uv run ytl film compose <slug>`, then render a short range (`uv run ytl film render <slug> --from <s> --to <s+1>`) and take a frame with ffmpeg.
- Transitions: `transition` is `cut` (default) or `dissolve`.
