# blender-architectural-renders

A Claude Code skill that builds architectural and remodel renders in Blender. One Python scene script builds the whole model, and Blender renders it headless with Cycles.

## Why

A room or a house is easy to model by hand once and hard to change later. Here the geometry lives in a script, built from plans and measurements. A change is an edit and a re-render, and an option is a command-line flag. The owner chooses from labeled comparison pages, and the choice becomes the script's default.

Before every render, six checks look for the geometry defects that recur in these scenes. A scene that fails a check does not render.

## How a model gets built

**Inputs.**
- Vector PDF plans. `scripts/extract_plan.py` turns the linework into walls, door swings, and door leaves. Extraction misses some walls, so the scene script keeps a dated correction layer for them ([Route A](reference/plan-input.md)).
- Hand-entered coordinates, when the plan is a scan or the scene is small ([Route B](reference/plan-input.md)).
- Site measurements in `context/dimensions.md`, which the skill reconciles with the plans before any geometry change.
- Site photos, as a checklist of fixture counts, ceiling steps, and closet bays. Texture images (CC0 sets or photos) go on surfaces through the material helpers.

**The scene script.** `templates/scene_template.py` is the starting point: constants, a `VIEWS` table, `--view`, `--res`, `--samples`, `--gpu`, `--out`, and one flag per option study. The project copies `scripts/` into `blender/lib/` and owns that copy.

**Views.** A perspective view is a level camera with lens and shift. A plan view is an orthographic camera cut at a fixed height, with ceilings and lights removed so the cut is true. Plan overlays mark posts, walls to remove, and door swings. `scripts/annotate_plan.py` adds circled callouts afterwards.

**Checks.** `run_checks` runs before every render, previews included, and exits 1 on any hit.

| Check | Finds |
|---|---|
| coplanar | Same-facing faces on one plane (z-fighting, black strips) |
| flipped | Meshes that are inside out |
| wall_gaps | Walls that almost meet; door-sized openings with no header or no floor |
| floor_fit | Objects floating above or sunk into the floor |
| camera | Faces seen from behind; sky seen from an interior view |
| clearance | Anything inside the walking box over a stair tread or path |

**Studies and the scale figure.** Each owner question gets one page: every option rendered from the same view, then joined and labeled by `scripts/compose.py`. `scripts/mannequin.py` builds a clay figure at the user's real height, posed with two-bone IK. `clash_check` reports where the figure touches a fixture.

**Construction sheets.** `scripts/sheets.py` draws A3 sheets for carpentry, plumbing, electrical, and tile from the same numbers as the model. It also packs tile cuts onto stock tiles. Pieces come from the scene through `--export-pieces`, so a sheet cannot drift from the render ([details](reference/construction-sheets.md)).

**Outputs for an architect.** `scripts/ifc_walls.py` writes the scene's walls as an IFC file, reads it back, and raises an error when an element differs from its record by more than 3 mm. Bonsai generates a plan drawing from that IFC, and `check_drawing` compares the drawing with the IFC.

**Sun and scans.** Sun Position sets the sun from the site's latitude, longitude, date, and time, and one fixed time serves every render in a project. Point Cloud I/O brings a LiDAR scan (LAS, LAZ, E57, PLY) into the scene, to check the model against the site. All three extensions are described in [reference/extensions.md](reference/extensions.md).

## How to use it

Install the skill (see Developer details), then open Claude Code in a project. Ask for a render, a plan view, a study page, a construction sheet, or an IFC file for a room, house, or remodel, and the skill loads. Claude sets up `blender/`, `context/dimensions.md`, and `context/decisions.md`, builds the scene script, and runs a low-resolution preview before any final render.

Prerequisites:
- Blender 5.2 LTS at `/Applications/Blender.app/Contents/MacOS/Blender`. The `/usr/local/bin/blender` symlink crashes Blender, so the scripts use the full path.
- uv, for the plain-Python scripts (`compose.py`, `annotate_plan.py`, `extract_plan.py`, `sheets.py`, and `ifc_walls.py`). They run through `uvx` with Pillow, PyMuPDF, or IfcOpenShell and numpy, and `uvx` needs the network on first use.
- For IFC, sun, and scan work only: the Bonsai, Sun Position, and Point Cloud I/O extensions. Claude asks before it installs any of them. Bonsai is about 140 MB.

## What it does not do

- It does not build a model from photos. There is no photogrammetry.
- A LiDAR scan checks the model. It does not build the model.
- It does not read or write DXF or DWG. Plan input is a vector PDF or typed coordinates, and the architect output is IFC.
- The checks see viewport geometry, not render geometry. They miss instances (collection, geometry-nodes, and particle instances) and modifiers shown only in render.
- The wall gap check needs walls aligned to the axes. Rotated walls are reported as not checked, and a preview must cover them.
- Extraction tuning is per drawing set, because offices draw walls differently.
- Headless Bonsai output beyond walls and a plan drawing is unverified: doors and windows in openings, dimensions, labels, sheets, and rendering an IFC scene with project materials.

## Developer details

Install from the skill-developer project root, after the release is approved:

```
python3 scripts/install_skill.py blender-architectural-renders <tag>
```

Run the tests from the skill root. The suite has 54 steps, and a full run prints `54 passed, 0 failed`.

```
timeout 2400 tests/run_tests.sh
```

- The suite needs Blender at the default path above; set `BLENDER` to override it.
- The extension steps skip when Bonsai, Sun Position, and Point Cloud I/O are not installed. The count of 54 was run with all three installed.
- `SCRIPTS_DIR` overrides the scripts under test (default `scripts/`).
- Output and logs go to `tests/out/`, which is gitignored.

The rest of the skill:
- [SKILL.md](SKILL.md): the instructions Claude follows.
- [reference/](reference/): `api.md` (function signatures), `plan-input.md`, `views.md`, `studies.md`, `construction-sheets.md`, and `extensions.md`.
- [dev/features/blender-skill-contract.md](dev/features/blender-skill-contract.md): the design contract for `scripts/`.

This file, `tests/`, `dev/`, and `docs/` are not part of the installed skill.
