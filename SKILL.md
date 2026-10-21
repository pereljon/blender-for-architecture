---
name: blender-for-architecture
description: Builds architectural and remodel renders in Blender from a Python scene script, run headless with Cycles. Covers project setup, plan input from PDFs or measurements, perspective and cut plan views, option studies, a posable scale figure, render checks, construction sheets, the site sun by date and time, LiDAR scans against the model, and IFC walls and plan drawings for an architect. Use when creating or changing a Blender render, scene script, plan view, study page, construction sheet, or IFC file for a room, house, or remodel.
---

# Architectural renders in Blender

One Python script builds the whole scene, and Blender renders it headless. Options are command-line flags. The owner decides from labeled study pages, and the chosen option becomes the script default.

## Environment

- Run Blender by its full app path, with these flags:
  `/Applications/Blender.app/Contents/MacOS/Blender --factory-startup -b --python-exit-code 1 -P script.py -- args`
- Keep `--python-exit-code 1`. Without it, a script exception still exits 0 and looks like success.
- Render one view per Blender run. A view changes visibility, scale, and lighting for the rest of the process.
- Do not use the `/usr/local/bin/blender` symlink. Blender cannot find its bundled Python through it and crashes.
- The scripts target Blender 5.2 LTS with Cycles on Metal. Blender's Python also bundles numpy and a few other packages. The helpers use only `bpy`, `bmesh`, and `mathutils`. Do not pip-install into Blender.
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
- If a dimension on a plan or photo is unreadable, mark it unread in the dimensions file. Ask for a clearer copy.
- Never fill an unreadable dimension with a plausible value.
- When a plan and a site measurement disagree, record both with their sources. Ask the owner which one governs.
- Model each product from the manufacturer's dimensioned drawing, never from a look-alike. Record the drawing in the dimensions file.
- Name objects with a prefix per element group (`wic_`, `vanity_`, `stair1_`). Plan views and checks select objects by prefix.
- Give colors as hex through `srgb()`. sRGB numbers typed as linear values come out too light and washed out.
- Never let two same-facing faces overlap on one plane. Butt the pieces against each other, or offset one of them 1 to 2 mm.
- Round design constants to the owner's step (for example 5 mm) before they reach a render or a sheet. Derive odd values only for fit checks.
- Model a floor as one slab, and cut openings with `cut_holes`. A floor pieced from rectangles leaves gaps at thresholds.
- Use one fixed sun time for every render in a project, so options compare fairly.
- Before you read `matrix_world` or any world position, call `bpy.context.view_layer.update()`. Until then, positions are stale.
- In `exempt`, and in any list of objects that a script moves or skips, use exact object names. A prefix there also catches unrelated objects.
- Exempt only objects with stable names. A name built from a list index, such as `wall_27`, can point at another object after the plan changes.
- Build each stair step as one box from its riser to the next riser, butted to its neighbours.
- Set an emissive strip into its recess, so that only its front face shows.
- After a floor or wall level changes, look at every threshold and wall base in a preview.
- Place an eye-level camera at the floor height plus `EYE_HEIGHT / U`. That is a 5'-7" viewer's eye, 5'-2 1/2".

## The loop

Copy this checklist into the response and track it:

```
- [ ] 1. Check dimensions.md and decisions.md; edit constants or geometry in the script
- [ ] 2. Preview at --res 800 --samples 48 --gpu into scratch/; the checks run first
- [ ] 3. Fix every check hit (a check result that reports a defect), then read the preview image
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

The scene script calls `run_checks` after it sets the camera and before it renders. It runs six checks over the whole scene, prints `OK`, `FAIL`, or `SKIP` for each, and exits 1 on any hit.

```python
from checks import clash_check, fail_on, run_checks
fail_on(clash_check(("man_",), ("vanity_", "basin", "tub_")), "clash")
run_checks(floors=("floor",), paths=STAIR_PATHS, interior=VIEWS[args.view].get("interior"))
```

| Check | Finds |
|---|---|
| coplanar | Same-facing faces on one plane: z-fighting, black strips, a slab side on a wall face |
| flipped | Closed meshes that are inside out, or have faces turned the wrong way |
| wall_gaps | Walls that almost meet or meet only at a corner; door-sized openings with no header, or with no floor through them |
| floor_fit | Objects that float above or sink into the floor under them |
| camera | Faces seen from behind (a missing face, or a camera inside an object), and sky seen from an interior view |
| clearance | Anything inside the walking box over a stair tread or path, with the headroom. The walking box is the space from the tread top up to 2.032 m (6'-8"). |

Besides `OK`, `FAIL`, and `SKIP`, `run_checks` prints these lines:

| Line | Meaning |
|---|---|
| `NOTE wall_gaps: not axis-aligned, not checked: ...` | Walls rotated off the axes are not checked. Check those walls in the preview. |
| `NOTE camera: exterior view, escapes not checked` | No object is above the camera, so sky is not reported. Set `interior=True` to check it. |
| `WARN exempt <check>: no object named X` | An exemption names no object, so it does nothing. Correct the name. |
| `WARN floors: no rendered mesh named X` or `no object named X` | The floor is hidden from render, is not a mesh, or does not exist. `floor_fit` leaves it out. |
| `SKIP <check>: ...` | The check did not run. Reasons: `no floors given`, `none of the floors exists`, `no paths given`, `no scene camera`, `scene camera is not a camera object`, or an orthographic or panoramic camera. |
| `FAIL <check>: error ...` | The check raised an exception. Treat it as a failure. |

- Run the checks before every render, previews included.
- Keep `--python-exit-code 1` in every run command. Without it, an error outside the checks exits 0 and leaves the old image in place.
- Fix every hit.
- If a hit is intended, exempt the object by its exact name: `exempt={"floor_fit": ["vanity_front"]}`.
- If an opening is meant to run to the ceiling, exempt it by its two wall names: `exempt={"openings": [("wall_hall_w", "wall_hall_e")]}`.
- Give `openings` a list of pairs. One bare pair is read as two names, and the hit stays.
- Give the reason for each exemption in a comment.
- Name every floor, slab, deck, and paving object in `floors`. Without floors, `floor_fit` does not run, and openings are not checked for a floor.
- Name every wall with the `wall_` prefix, or pass your wall prefixes in `walls`.
- Add a walking box to `paths` for each stair tread and landing.
- Write each walking box as `(x0, x1, y0, y1, z)`, with z at the tread top.
- Draw each walking box between the handrails, from its nosing to the next nosing.
- If a view looks out through an opening without glass, set `interior=False` in its entry.
- In a script without a VIEWS table, leave out `interior` unless the view looks out through an opening without glass. The default detects an interior view from an object above the camera.
- An object buried entirely inside a floor reports as sunk more than the hang limit (0.3 m), whatever its depth.
- A camera hit gives a pixel box in the view's image at the run's `--res`. A failing run writes no image.
- To see a camera hit, exempt its object for one preview run at the same `--res`. Then look inside the pixel box.
- A plan (orthographic) view checks openings for a floor only, not for a header.
- The header check runs only where the opening's walls stand at least 2.0 m above the higher wall bottom. Half walls get no header check.
- A wall pair that stands about 1 m or less above the higher wall bottom gets no opening check.
- The checks do not see instances (collection, geometry-nodes, or particle instances). Check those in the preview.
- The checks see viewport geometry, not render geometry. A modifier shown in render but hidden in the viewport, such as a boolean with `show_viewport` off, is not seen.
- Run `clash_check` for the figure. `run_checks` leaves the figure out of the coplanar, floor_fit, and clearance checks.
- `clash_check` counts surfaces that touch as a hit. Keep furniture 1 mm off the wall behind it, or leave walls out of the second prefix list.
- In a project script that builds its own scene, copy `scripts/*.py` into its `lib/`.
- Then call `run_checks` right before the render call, with `unit` set to metres per project unit.

## QA checklist

Check every preview against this list. The owner's colored-box markup of a plan render finds most of these.

- Geometry buried in an existing wall, or doubled elements
- Coplanar faces: z-fighting or black strips at jambs, headers, and ceilings
- A camera inside an object (check again after moving furniture)
- Open tube ends (keep fill caps on)
- Overexposure from sRGB colors or unrealistic light wattage
- Fixture, step, and bay counts that differ from the plans or site photos
- Missing corners, headers, or reveal faces inside openings
- An emissive strip whose top or sides show, or that streaks nearby glass
- A dark sill or track across the full wall depth, which reads as a hole
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
| `checks.py` | Blender | `run_checks` and the six checks (coplanar, flipped, wall gaps, floor fit, camera, clearance), `clash_check`, `fail_on` |
| `wall_gaps.py` | Blender or plain Python | Wall rectangles that almost meet, and door-sized openings between in-line walls, from a list such as `load_plan`'s |
| `compose.py` | uvx pillow | Labeled study pages from PNGs |
| `annotate_plan.py` | uvx pillow | Circled callouts on a plan render |
| `extract_plan.py` | uvx pymupdf | Walls, door swings, and leaves from a plan PDF's vector linework |
| `sheets.py` | uvx pillow | Construction sheets, dimension lines, tile packing, rounding check |
| `ifc_walls.py` | Blender with Bonsai enabled, or uvx with ifcopenshell and numpy | IFC walls from the wall records, read back and checked; a Bonsai plan drawing checked against the IFC |

## Extensions

Read [reference/extensions.md](reference/extensions.md) before you install or use an extension.

| Extension | Use it for |
|---|---|
| Bonsai (includes IfcOpenShell) | Walls as IFC objects, plan drawings from the model, and IFC files for architects |
| Sun Position | The sun from the site's latitude, longitude, date, and time |
| Point Cloud I/O | LiDAR scans (LAS, E57, PLY, PCD, PTS, XYZ) in the scene, to check the model against the site |

- Before you install or sync an extension, ask the user. Name each extension and its download size.
- Install an extension once per machine. Do not enable it in the user's preferences.
- Enable every installed extension of the three inside each run that needs any, the same set in every run.

## Reference

- Plan input from a PDF or from measurements: [reference/plan-input.md](reference/plan-input.md)
- Perspective views, plan cuts, overlays, labels: [reference/views.md](reference/views.md)
- Option studies, study pages, the figure, textures: [reference/studies.md](reference/studies.md)
- Construction sheets and tile cutting plans: [reference/construction-sheets.md](reference/construction-sheets.md)
- Extensions (Bonsai and IfcOpenShell, Sun Position, Point Cloud I/O): [reference/extensions.md](reference/extensions.md)
