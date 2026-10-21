# blender-for-architecture

A Claude Code skill that builds architectural and remodel renders in Blender. One Python scene script builds the whole model. Blender renders it headless (no window) with Cycles, its path-tracing renderer.

## Why

A room or a house is easy to model by hand once and hard to change later. Here the geometry lives in a script, built from plans and measurements. A change is an edit and a re-render. An option is a command-line flag.

The owner chooses from labeled comparison pages, and the choice becomes the script's default. Before every render, six checks look for geometry defects that recur in these scenes. A scene that fails a check does not render.

## How to use it

Prerequisites:
- Blender 5.2 LTS on macOS, Linux, or Windows. Only macOS is tested. SKILL.md ("Environment") lists the usual Blender path and GPU backend for each system.
- uv, a Python package runner. It provides `uvx`, which runs the plain-Python scripts with Pillow, PyMuPDF, or IfcOpenShell and numpy. `uvx` needs the network on first use.
- For IFC, sun, and scan work only: the Bonsai, Sun Position, and Point Cloud I/O extensions. Claude asks before it installs any of them. Bonsai is about 140 MB.

Shortest path to a first render:
1. Install the skill (see Developer details).
2. Open Claude Code in a project. Ask for a render, plan view, study page, construction sheet, or IFC file of a room or house. The skill loads.
3. Claude sets up the Blender folder (`blender/` by default), a dimensions file, and a decisions log, then builds the scene script from `templates/scene_template.py`.
4. Claude copies `scripts/` into `blender/lib/vX.Y.Z/`, where X.Y.Z is the installed skill version. It runs a low-resolution preview before any final render.

To run one view yourself, copy the template, and copy `scripts/` into `lib/<LIB>/` beside it. `<LIB>` is the template's `LIB` value. Then run:

```
BLENDER=<path>; "$BLENDER" --factory-startup -b --python-exit-code 1 -P scene.py -- \
    --view persp --res 800 --samples 48 --gpu --out out/persp.png
```

The script prints `DONE <path>` when the render is written. SKILL.md ("Environment") states the `$BLENDER` rule and the flags.

## How a model gets built

**Inputs.**
- Vector PDF plans. `scripts/extract_plan.py` turns the linework into walls, door swings, and door leaves. Extraction misses some walls, so the scene script keeps a dated correction layer for them ([Route A](reference/plan-input.md)).
- Hand-entered coordinates, when the plan is a scan or the scene is small ([Route B](reference/plan-input.md)).
- Site measurements in the dimensions file. The skill reconciles them with the plans before any geometry change.
- Site photos, as a checklist of fixture counts, ceiling steps, and closet bays. Texture images go on surfaces through the material helpers. They are either CC0 sets (public domain, free to use) or photos.

**The scene script.** `templates/scene_template.py` is the starting point. It holds the project constants and a `VIEWS` table, which lists each named camera view: its position, lens, and plan settings. Its command-line flags are `--view`, `--res`, `--samples`, `--gpu`, `--out`, `--export-pieces`, and an option flag (`--option a|b` in the template). The project keeps one copy of `scripts/` per skill version it has used, in `blender/lib/vX.Y.Z/`. Each scene script pins one version with `LIB`, and an upgrade is a choice that [reference/migration.md](reference/migration.md) describes.

**Views.** A perspective view is a level camera with lens and shift. A plan view is an orthographic camera cut at a fixed height. Ceilings and lights are removed so the cut is true. Plan overlays mark posts, walls to remove, and door swings. `scripts/annotate_plan.py` adds circled callouts afterwards.

**Checks.** `run_checks` runs before every render, previews included. It exits 1 on any hit.

| Check | Finds |
|---|---|
| coplanar | Same-facing faces on one plane, which cause z-fighting (two surfaces flicker and show black strips) |
| flipped | Meshes that are inside out |
| wall_gaps | Walls that almost meet; door-sized openings with no header or no floor |
| floor_fit | Objects floating above or sunk into the floor |
| camera | Faces seen from behind; sky seen from an interior view |
| clearance | Anything inside the walking box over a stair tread or path |

**Studies and the scale figure.** Each owner question gets one page. Every option is rendered from the same view. `scripts/compose.py` joins the renders and labels them. `scripts/mannequin.py` builds a posable clay figure at a real person's height. `clash_check` reports where the figure touches a fixture.

**Construction sheets.** `scripts/sheets.py` draws sheets for carpentry, plumbing, electrical, and tile from the same numbers as the model. It also packs tile cuts onto stock tiles.
- Paper sizes: `letter`, `tabloid`, `arch-c`, `arch-d`, `a4`, and `a3`. The default is `tabloid` (11 x 17 in). `set_paper` picks another.
- Pieces come from the scene through `--export-pieces`, so a sheet cannot drift from the render ([details](reference/construction-sheets.md)).

**Outputs for an architect.** IFC (Industry Foundation Classes) is an open file format for building models.
- `scripts/ifc_walls.py` writes the scene's walls as an IFC file and reads it back. It raises an error when an element differs from its record by more than 3 mm.
- Bonsai, a Blender add-on for IFC, generates a plan drawing from that IFC. `check_drawing` compares the drawing with the IFC.

**Sun and scans.** Sun Position sets the sun from the site's latitude, longitude, date, and time. One fixed time serves every render in a project. Point Cloud I/O brings a LiDAR scan into the scene, to check the model against the site. LiDAR is laser distance scanning. Point Cloud I/O reads LAS, E57, PLY, PCD, PTS, and XYZ point cloud files. [reference/extensions.md](reference/extensions.md) describes all three extensions.

## What it does not do

- It does not build a model from photos. There is no photogrammetry.
- A LiDAR scan checks the model. It does not build the model.
- It does not read or write DXF or DWG. Plan input is a vector PDF or typed coordinates. The architect output is IFC.
- Tested on macOS with Metal only. The Linux and Windows paths and GPU backends are documented but untested.
- The checks see viewport geometry, not render geometry. They miss instances (collection, geometry-nodes, and particle instances) and modifiers shown only in render.
- The wall gap check needs walls aligned to the axes. Rotated walls are reported as not checked, and a preview must cover them.
- Extraction tuning is per drawing set, because offices draw walls differently.
- Headless Bonsai output beyond walls and a plan drawing is unverified. This covers doors and windows in openings, dimensions, labels, sheets, and rendering an IFC scene with project materials.

## Developer details

Install from the skill-developer project root, after the release is approved:

```
python3 scripts/install_skill.py blender-for-architecture <tag>
```

Only `SKILL.md`, `CHANGELOG.md`, `reference/`, `scripts/`, and `templates/` ship in the install. `.gitattributes` export-ignores `README.md`, `docs/`, `dev/`, `tests/`, `.gitignore`, and `.gitattributes`. A session reads the installed version from the shipped `CHANGELOG.md`.

Run the tests from the skill root. `timeout` is optional: `tests/run_tests.sh` falls back to `tests/with_timeout.py` when neither `timeout` nor `gtimeout` is on the path.

```
timeout 2400 tests/run_tests.sh
```

The suite prints `PASS` or `FAIL` for each step. It ends with a summary line (`N passed, M failed`) and exits non-zero on any failure.

- The suite needs Blender at the macOS path in SKILL.md. Set `BLENDER` to override it.
- The suite needs `uvx`. It stops with a prerequisites message when `uvx` or Blender is missing.
- The extension steps skip when Bonsai, Sun Position, and Point Cloud I/O are not installed. The summary line then notes the skip.
- `SCRIPTS_DIR` overrides the scripts under test (default `scripts/`).
- Output and logs go to `tests/out/`, which is gitignored.

The rest of the skill:
- [SKILL.md](SKILL.md): the instructions Claude follows.
- [reference/](reference/): `api.md` (function signatures), `plan-input.md`, `views.md`, `studies.md`, `construction-sheets.md`, `extensions.md`, and `migration.md`.
- [dev/features/blender-skill-contract.md](dev/features/blender-skill-contract.md): the design contract for `scripts/`.
