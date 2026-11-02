# Upstream

Vendored from https://github.com/lgwrightlab/schematic-figure (MIT, LGW Lab) at commit 09d8b6e98d04b91de6e8b6632b3356b9fc237417, `.claude/skills/schematic-figure` and `.claude/skills/patent-drawing` (sibling folder). Blog: https://lgwrightlab.github.io/schematic-figure/. License in `LICENSE`.

Local changes: none to upstream files except the omp setup note in `SKILL.md`.

Under omp the skill folder is symlinked, so do not copy `foundation/` into a project: run the tools from the skill folder with `--root <project dir>` (see `reference/process.md`, Layout and Tools). Needs Node 22 or later and a Chromium browser; Blender only for the `blender` route.
