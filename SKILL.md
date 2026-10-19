---
name: blender-architectural-renders
description: Builds architectural and remodel renders in Blender from a Python scene script, run headless with Cycles. Covers project setup, plan input from PDFs or measurements, perspective and cut plan views, option studies with comparison pages, a posable scale figure with clash checks, QA for recurring render bugs, and optional construction sheets and tile cutting plans. Use when creating or changing a Blender render, scene script, plan view, study page, or construction sheet for a room, house, or remodel.
---

# Architectural renders in Blender

One Python script builds the whole scene, and Blender renders it headless. Options are command-line flags. The owner decides from labeled study pages, and the chosen option becomes the script default.

## Environment

- Run Blender by its full app path, with these flags:
  `/Applications/Blender.app/Contents/MacOS/Blender --factory-startup -b --python-exit-code 1 -P script.py -- args`
- Keep `--python-exit-code 1`. Without it, a script exception still exits 0 and looks like success.
- Render one view per Blender run. A view changes visibility, scale, and lighting for the rest of the process.
- Do not use the `/usr/local/bin/blender` symlink. Blender cannot find its bundled Python through it and crashes.
- The scripts target Blender 5.2 LTS with Cycles on Metal. Inside Blender, `bpy`, `bmesh`, `mathutils`, and `numpy` exist. Other packages come only with an extension.
- Run plain-Python scripts through uvx, with no installs: `uvx --with pillow python -I script.py`.
- Add `--with pymupdf` for `extract_plan.py`.
- uvx needs uv installed, and network on first use. Without them, run `python3 -I script.py` with a system Pillow.

## Project setup

1. Create `blender/lib/` in the project, and copy this skill's `scripts/*.py` and `scripts/*.json` into it.
2. Copy `templates/scene_template.py` to `blender/build_<scene>.py` and rename its constants.
3. Call `set_units("ft")` in the script if the drawings are in feet. All helper lengths are then in feet.
4. In a feet project, give the figure its own pose in feet. `EXAMPLE_POSE` is in metres.
5. Create `context/dimensions.md`. Reconcile plan, elevation, site, and model numbers in it.
6. Before you build, add a site-photo checklist to the dimensions file: fixture counts, ceiling steps, closet bays.
7. Record owner decisions in `context/decisions.md`. Set each chosen value as the flag default in the script.
8. Exclude from git: `scratch/`, `out/`, frame folders, `*.blend1`, video, `incoming/`, and textures over 50 MB.

The project owns its copy of the scripts. To upgrade, copy a newer script deliberately and re-render one view to compare.

## Rules for every scene

- Build the scene from the script only. Never hand-edit a `.blend` file.
- Check `context/dimensions.md` before any geometry change.
- Model each product from the manufacturer's dimensioned drawing, never from a look-alike. Record the drawing in the dimensions file.
- Name objects with a prefix per element group (`wic_`, `vanity_`, `stair1_`). Plan views and checks select objects by prefix.
- Give colors as hex through `srgb()`. sRGB numbers typed as linear values come out too light and washed out.
- Never let two same-facing faces overlap on one plane. Butt the pieces against each other, or offset one of them 1 to 2 mm.
- Round design constants to the owner's step (for example 5 mm) before they reach a render or a sheet. Derive odd values only for fit checks.
- Model a floor as one slab, and cut openings with `cut_holes`. A floor pieced from rectangles leaves gaps at thresholds.
- Use one fixed sun time for every render in a project, so options compare fairly.

## The loop

Copy this checklist into the response and track it:

```
- [ ] 1. Check dimensions.md and decisions.md; edit constants or geometry in the script
- [ ] 2. Preview at --res 800 --samples 48 --gpu into scratch/, then read the image
- [ ] 3. Run the checks (clash, coplanar) and fix every hit
- [ ] 4. Check the preview against the QA list below
- [ ] 5. Studies: render each option, compose one labeled page per question
- [ ] 6. Final: --res 1600..2400 --samples 128..256, in the background, into out/
- [ ] 7. Copy delivered images to deliverables/<date>_<topic>/, log the decision, commit tracked files
```

- Run long renders as background commands, and let the harness notify you. Do not poll with sleep loops.
- `render(out)` prints `DONE <out>` when the image is written. Wait for that line.
- After an owner correction, send a fast low-resolution re-render before the final.
- Keep working renders in `scratch/` and `out/`, out of git. Copy only delivered images into the dated deliverables folder.
- Commit only the files that the project tracks. Push only on request.
- After a geometry change, re-render every delivered view that shows the changed element.
- When the owner reports a missing element, compare the image's time with the change before you debug.

To render several views, run one background shell loop of single-view runs, with one marker at the end:

```
for v in plan vanity shower; do
  /Applications/Blender.app/Contents/MacOS/Blender --factory-startup -b --python-exit-code 1 \
    -P blender/build_bath.py -- --view $v --res 2000 --samples 192 --gpu --out out/$v.png || exit 1
done; echo ALL_DONE
```

## Checks

Run these in the script after the build and before rendering. `fail_on` exits non-zero on any hit.

```python
from checks import clash_check, coplanar_check, fail_on
fail_on(clash_check(("man_",), ("vanity_", "basin", "tub_")), "clash")
fail_on(coplanar_check(("vanity_", "tile_", "ceil_")), "coplanar")
```

- Run `clash_check` on every view that contains the figure.
- Run `coplanar_check` before finals. It finds same-facing coplanar faces, which z-fight or render black strips.
- Scope `coplanar_check` with prefixes. Leave out the figure and other curved meshes, whose tangent faces give false hits.
- Faces that meet back to back, such as a butt joint, are fine and are not reported.
- `clash_check` counts surfaces that touch as a hit. Keep furniture 1 mm off the wall behind it, or leave walls out of the second prefix list.

## QA checklist

Check every preview against this list. The owner's colored-box markup of a plan render finds most of these.

- Geometry buried in an existing wall, or doubled elements
- Coplanar faces: z-fighting or black strips at jambs, headers, and ceilings
- A camera inside an object (check again after moving furniture)
- Open tube ends (keep fill caps on)
- Overexposure from sRGB colors or unrealistic light wattage
- Fixture, step, and bay counts that differ from the plans or site photos
- Missing corners, headers, or reveal faces inside openings
- Products modeled from look-alikes, or the wrong SKU
- Door and window swings hitting built-ins (set a stop angle)
- A black mirror: it reflects a removed object or the dark world
- Floor gaps at thresholds
- Soft items overlapping each other
- Figure limbs passing through fixtures
- A second source drawing registered with the first drawing's offset
- On sheets: overlapping labels, drawings too big for the scale, wet and dry sides swapped

## Scripts

Run these; do not read them into context. Look up signatures in [reference/api.md](reference/api.md).

| Script | Runs in | Does |
|---|---|---|
| `bhelpers.py` | Blender | Units, geometry, materials, tiles, plan input, lights, Cycles setup, cameras, plan cut, overlays, `render` |
| `mannequin.py` | Blender | Clay figure at a given height, posed with two-bone IK |
| `checks.py` | Blender | `clash_check`, `coplanar_check`, `fail_on` |
| `compose.py` | uvx pillow | Labeled study pages from PNGs |
| `annotate_plan.py` | uvx pillow | Circled callouts on a plan render |
| `extract_plan.py` | uvx pymupdf | Walls, door swings, and leaves from a plan PDF's vector linework |
| `sheets.py` | uvx pillow | Construction sheets, dimension lines, tile packing, rounding check |

## Extensions

Read [reference/extensions.md](reference/extensions.md) before you install or use an extension.

| Extension | Use it for |
|---|---|
| Bonsai (includes IfcOpenShell) | Walls, doors, and windows as IFC objects; plans and sections from the model; IFC files for architects |
| Sun Position | The sun from the site's latitude, longitude, date, and time |
| Point Cloud I/O | LiDAR scans (LAS, LAZ, E57, PLY) in the scene, to check the model against the site |
| CAD2Cube, Export AutoCAD DXF | DXF from or to an architect's CAD files (install only when needed) |

- Install an extension once per machine. Do not enable it in the user's preferences.
- Enable the extension inside each run that needs it.

## Reference

- Plan input from a PDF or from measurements: [reference/plan-input.md](reference/plan-input.md)
- Perspective views, plan cuts, overlays, labels: [reference/views.md](reference/views.md)
- Option studies, study pages, the figure, textures: [reference/studies.md](reference/studies.md)
- Construction sheets and tile cutting plans: [reference/construction-sheets.md](reference/construction-sheets.md)
- Extensions (Bonsai and IfcOpenShell, Sun Position, Point Cloud I/O, DXF): [reference/extensions.md](reference/extensions.md)
