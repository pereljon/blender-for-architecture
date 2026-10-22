---
name: blender-for-architecture
description: Builds architectural and remodel renders in Blender from a Python scene script, run headless with Cycles. Covers project setup, plan input from PDFs or measurements, perspective and cut plan views, option studies, a posable scale figure, render checks, construction sheets, the site sun by date and time, LiDAR scans against the model, and IFC walls and plan drawings for an architect. Use when creating or changing a Blender render, scene script, plan view, study page, construction sheet, or IFC file for a room, house, or remodel.
---

# Architectural renders in Blender

One Python file, the scene script, builds the whole scene, and Blender renders it headless. Options are command-line flags. The owner is the person who makes the design decisions. The user is the person working with Claude. The owner decides from labeled study pages, and the chosen option becomes the scene script's default.

## Environment

`$BLENDER` in this skill is the full path of the Blender executable. Set it in the same command that uses it, with a semicolon, and keep these flags:

```
BLENDER=<path>; "$BLENDER" --factory-startup -b --python-exit-code 1 -P script.py -- args
```

| System | Blender path | GPU backend for `--gpu` |
|---|---|---|
| macOS | `/Applications/Blender.app/Contents/MacOS/Blender` | Metal |
| Linux | `blender` from the distribution or Snap, or `blender` in the folder unpacked from blender.org | OptiX, then CUDA, then HIP |
| Windows | `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` | OptiX, then CUDA, then HIP |

- A shell variable does not carry over to the next command. An assignment with no semicolon before the command expands `$BLENDER` too early and runs an empty command.
- Keep `--python-exit-code 1`. Without it, a script exception still exits 0 and looks like success.
- Render one view per Blender run. A view changes visibility, scale, and lighting for the rest of the process.
- On macOS, do not use the `/usr/local/bin/blender` symlink. Blender cannot find its bundled Python through it and crashes.
- Without a GPU of that backend, `--gpu` prints one `WARN` line and renders on CPU.
- The tests run on macOS with Metal only. The Linux and Windows paths and backends are untested.
- The scripts target Blender 5.2 LTS. Blender's Python also bundles numpy and a few other packages. The helpers use only `bpy`, `bmesh`, and `mathutils`. Do not pip-install into Blender.
- Run plain-Python scripts through uvx, with no installs: `uvx --with pillow python -I script.py`.
- Add `--with pymupdf` for `extract_plan.py`.
- uvx needs uv installed, and network on first use. Without them, run `python3 -I script.py` with a system Pillow.

## Project setup

1. Choose the Blender folder. Use `blender/` in a new project. Use the folder where the project already keeps its scene scripts, such as `renders/`, in an existing project. Paths in this skill write it as `blender/`.
2. Read the installed version from the skill folder, `${CLAUDE_SKILL_DIR}`: the first `## [X.Y.Z]` heading in `CHANGELOG.md`. If that file is missing, use the `tag:` line of `.installed`. If both are missing, use the `LIB` value in `templates/scene_template.py`.
3. Copy `${CLAUDE_SKILL_DIR}/scripts/*.py` and `*.json` into `blender/lib/vX.Y.Z/`. Never edit a version folder after you copy it.
4. Copy `templates/scene_template.py` to `blender/build_<scene>.py`. Its `LIB` already names the installed version.
5. Call `set_units("ft")` if the drawings are in feet. All helper lengths are then in feet.
6. If the main viewer is not 5'-7", set `VIEWER` to their height in project units. The eye-level camera height follows from it.
7. Keep two notes files: the dimensions file and the decisions log. If the project has a `context/` folder, use `context/dimensions.md` and `context/decisions.md`. Otherwise use `blender/dimensions.md` and `blender/decisions.md`. For a quick preview outside a project, skip the notes files.
8. Reconcile plan, elevation, site, and model numbers in the dimensions file. Before you build, add a site-photo checklist to it: fixture counts, ceiling steps, closet bays.
9. Record owner decisions in the decisions log. Set each chosen value as the flag default in the scene script.

## Project lib

The project keeps one folder of this skill's scripts per skill version it has used, in `blender/lib/`. Each script that imports them pins one version:

```
LIB = "v1.1.0"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", LIB))
```

- Give every project script that imports the lib these two lines: scene scripts and sheet generators alike.
- A script with no `LIB` uses the old flat `blender/lib/`. Treat it as pinned to `pre-1.0`.
- Run a command-line tool from the version folder that the scene pins: `python -I blender/lib/<LIB>/compose.py`.
- Keep every version folder, including one that no script pins. Remove one only when the user asks.

Before you edit or run a project script, compare its `LIB` with the installed version (Project setup, step 2). Do this once per script in a session.
- If they match, go on.
- If the pin is older, show the user a warning before you run the script. The warning is one line, followed by a short list of the headline CHANGELOG items since the pin.
- After the warning, offer an upgrade by [reference/migration.md](reference/migration.md). If the user declines, run the script unchanged.
- If the `LIB` line carries a `# held:` comment, do not warn.
- On an older pin, a function can differ from this skill's text. If the CHANGELOG lists it as changed or added after the pin, read its `def` in `blender/lib/<LIB>/` first. For a script with no `LIB`, read the flat `blender/lib/`.
- When a script stays on an older pin, use that version's equivalent for a missing feature. For example, use `EYE_HEIGHT / U` in place of `eye_height()`.
- If the pin is newer than the installed version, warn and suggest updating the skill. Never move a pin to an older version.
- If no source in step 2 gives a version, say that the installed version is unknown. Change no pin.

To move a project's own helpers onto the lib, follow [reference/migration.md](reference/migration.md).

## Rules for every scene

- Build the scene from the scene script only. Never hand-edit a `.blend` file.
- Check the dimensions file before any geometry change.
- If a dimension on a plan or photo is unreadable, mark it unread in the dimensions file. Ask for a clearer copy.
- Never fill an unreadable dimension with a plausible value.
- When a plan and a site measurement disagree, record both with their sources. Ask the owner which one governs.
- Model each product from the manufacturer's dimensioned drawing, never from a look-alike. Record the drawing in the dimensions file.
- Name objects with a prefix per element group (`wic_`, `vanity_`, `stair1_`). Plan views and checks select objects by prefix.
- Give colors as hex through `srgb()`. sRGB numbers typed as linear values come out too light and washed out.
- Never let two same-facing faces overlap on one plane. Butt the pieces against each other, or offset one of them 1 to 2 mm.
- Round design constants to the owner's step (for example 5 mm) before they reach a render or a sheet. Derive odd values only for fit checks.
- Model a floor as one slab, and cut openings with `cut_holes`. A floor pieced from rectangles leaves gaps at thresholds.
- Use one fixed sun time for every render in a project, so options compare fairly. Record its angles in the dimensions file.
- Before you read `matrix_world` or any world position, call `bpy.context.view_layer.update()`. Until then, positions are stale.
- Exempt a check hit (a check result that reports a defect) only as the Exemptions part of Checks says.
- Build each stair step as one box from its riser to the next riser, butted to its neighbours.
- Set an emissive strip into its recess, so that only its front face shows.
- After a floor or wall level changes, look at every threshold and wall base in a preview.
- Place an eye-level camera at the floor height plus `eye_height(VIEWER)`. Keep the camera heights of existing views as they are.

## The loop

Copy this checklist into the response and track it:

```
- [ ] 1. Check the dimensions file and the decisions log; edit constants or geometry in the scene script
- [ ] 2. Preview at --res 800 --samples 48 --gpu into scratch/; the checks run first
- [ ] 3. Fix every check hit, then read the preview image
- [ ] 4. Check the preview against the QA list below
- [ ] 5. Studies: render each option, compose one labeled page per question
- [ ] 6. Final: --res 1600..2400 --samples 128..256, in the background, into out/
- [ ] 7. Copy delivered images to the delivery folder, and log the decision
```

The delivery folder is `deliverables/<date>_<topic>/` if the project has a `deliverables/` folder; otherwise `delivered/<date>_<topic>/`.

- Run long renders as background commands, and let the harness notify you. Do not poll with sleep loops.
- `render(out)` prints `DONE <out>` when the image is written. Wait for that line.
- After an owner correction, send a fast low-resolution re-render before the final.
- Keep working renders in `scratch/` and `out/`. Copy only delivered images into the delivery folder.
- After a geometry change, re-render every delivered view that shows the changed element.
- When the owner reports a missing element, compare the image's time with the change before you debug.

To render several views, run one background shell loop of single-view runs, with one marker at the end:

```
BLENDER=<path>; for v in plan vanity shower; do
  "$BLENDER" --factory-startup -b --python-exit-code 1 \
    -P blender/build_bath.py -- --view $v --res 2000 --samples 192 --gpu --out out/$v.png || exit 1
done; echo ALL_DONE
```

## Checks

### Run

The scene script calls `run_checks` after it sets the camera and before it renders. It runs six checks over the whole scene, prints `OK`, `FAIL`, or `SKIP` for each, and exits 1 on any hit. Run the checks before every render, previews included.

| Check | Finds |
|---|---|
| coplanar | Same-facing faces on one plane: z-fighting, black strips, a slab side on a wall face |
| flipped | Closed meshes that are inside out, or have faces turned the wrong way |
| wall_gaps | Walls that almost meet or meet only at a corner; door-sized openings with no header, or with no floor through them |
| floor_fit | Objects that float above or sink into the floor under them |
| camera | Faces seen from behind (a missing face, or a camera inside an object), and sky seen from an interior view |
| clearance | Anything inside the walking box over a stair tread or path, with the headroom. The walking box is the space from the tread top up to 2.032 m (6'-8"). |

### Read the output

Besides `OK`, `FAIL`, and `SKIP`, `run_checks` prints these lines:

| Line | Meaning |
|---|---|
| `NOTE wall_gaps: not axis-aligned, not checked: ...` | Walls rotated off the axes are not checked. Check those walls in the preview. |
| `NOTE camera: exterior view, escapes not checked` | No object is above the camera, so sky is not reported. A scene with no ceiling reads as exterior. Setup says how to set `interior`. |
| `WARN exempt <check>: no object named X` | An exemption names no object, so it does nothing. Correct the name. |
| `WARN floors: no rendered mesh named X` or `no object named X` | The floor is hidden from render, is not a mesh, or does not exist. `floor_fit` leaves it out. |
| `SKIP <check>: ...` | The check did not run. Reasons: `no floors given`, `none of the floors exists`, `no paths given`, `no scene camera`, `scene camera is not a camera object`, or an orthographic or panoramic camera. |
| `FAIL <check>: error ...` | The check raised an exception. Treat it as a failure. |
| `NOTE coplanar: pairs inside collection X not checked (k of n objects)` | `overlaps` names collection X. Pairs of its members are not compared. Each member is still checked against every other object. |
| `WARN overlaps: no collection named X` | No collection has that name, so it skips nothing. Correct the name. |
| `WARN overlaps: collection X holds no rendered mesh` | The collection is empty, or its objects are hidden from render. It skips nothing. |
| `WARN overlaps: Y in collection X is a floor or wall` | A floor or wall is in the overlap collection. Take it out. |
| `NOTE full hit list: <path>` | The file at that path holds every hit line, not only the first 20 per check. |

- Fix every hit.
- If a check prints `... and k more`, pass `hits_file` and run again to see every hit.
- A tile or panel layer inside the wall volume gives coplanar hits and near-miss wall gaps where it meets walls and jambs. Read each such overlap in the file that `hits_file` writes before you fix or exempt it. List the layer prefix in `finishes`.
- A camera hit gives a pixel box in the view's image at the run's `--res`. A failing run writes no image.
- To see a camera hit, exempt its object for one preview run at the same `--res`. Then look inside the pixel box.

### Exemptions

- If a hit is intended, exempt the object by its exact name: `exempt={"floor_fit": ["vanity_front"]}`.
- In `exempt`, and in any list of objects that a script moves or skips, use exact object names. A prefix there also catches unrelated objects.
- Exempt only objects with stable names. A name built from a list index, such as `wall_27`, can point at another object after the plan changes.
- If an opening is meant to run to the ceiling, exempt it by its two wall names: `exempt={"openings": [("wall_hall_w", "wall_hall_e")]}`.
- Give `openings` a list of pairs. One bare pair is read as two names, and the hit stays.
- Give the reason for each exemption in a comment.
- If many objects overlap on one plane by design, such as leaf cards, put them in one collection.
- Pass that collection's exact name in `overlaps`: `run_checks(..., overlaps=("tree_leaves",))`. Give the reason in a comment.
- Put only those overlapping objects in the collection. Never put a floor or wall in it.
- Pairs inside the collection skip the coplanar check only. Each member is still checked against other objects and by the other checks.

### Setup

```python
from checks import clash_check, fail_on, run_checks
fail_on(clash_check(("man_",), ("vanity_", "basin", "tub_")), "clash")
run_checks(floors=("floor",), paths=STAIR_PATHS, interior=VIEWS[args.view].get("interior"))
```

- Name every floor, slab, deck, and paving object in `floors`. Without floors, `floor_fit` does not run, and openings are not checked for a floor.
- Name every wall with the `wall_` prefix, or pass your wall prefixes in `walls`.
- If wall finishes such as tile pieces are separate objects, pass their prefixes in `finishes`: `finishes=("wt_",)`. Use a prefix that names only finishes.
- To write every hit to a file, pass `hits_file=f"scratch/checks_{args.view}.txt"`. Each run overwrites the file. The file gives a detail line under each coplanar hit: the shared plane, the overlap box, and its area.
- Add a walking box to `paths` for each stair tread and landing.
- Write each walking box as `(x0, x1, y0, y1, z)`, with z at the tread top.
- Draw each walking box between the handrails, from its nosing to the next nosing.
- To check for sky in a scene with no ceiling, pass `interior=True` in the `run_checks` call, or set it in the view's entry.
- If a view looks out through an opening without glass, set `interior=False` in its entry.
- In a script without a VIEWS table, leave out `interior` unless the view looks out through an opening without glass. The default detects an interior view from an object above the camera.

### Limits

- A plan (orthographic) view checks openings for a floor only, not for a header.
- The header check runs only where the opening's walls stand at least 2.0 m above the higher wall bottom. Half walls get no header check.
- A wall pair that stands about 1 m or less above the higher wall bottom gets no opening check.
- `floor_fit` passes an object below the hang limit if contact supports it. Contact means within 25 mm, or running into the other object.
- Support that starts at a floor passes at any height: a chain of objects that rest on each other down to the floor.
- A panel mounted flat against its support, such as a door or a drawer front, passes on the same terms as its support. A door on a floor-standing carcass passes at any height.
- A panel counts when its touching face is at least twice the area of each other face of its bounding box. A panel turned off the world axes does not count.
- Support that starts at a wall or finish needs a base at least 0.1 m above the floor. So does any other side contact, such as a box against a cabinet side.
- An object below 0.1 m that touches only a wall, a finish, or another object with a narrow side is reported. A bed a few cm up against a wall or a nightstand is a defect.
- Objects at or above the hang limit give no support. An item recessed more than 25 mm into a wall is reported.
- An object buried entirely inside a floor reports as sunk more than the hang limit (0.3 m), whatever its depth.
- The checks do not see instances (collection, geometry-nodes, or particle instances). Check those in the preview.
- The checks see viewport geometry, not render geometry. A modifier shown in render but hidden in the viewport, such as a boolean with `show_viewport` off, is not seen.
- `run_checks` leaves the figure out of the coplanar, floor_fit, and clearance checks. Run `clash_check` for the figure, as [reference/studies.md](reference/studies.md) says.

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
- Upgrade a pin, or move a project's own helpers onto the lib: [reference/migration.md](reference/migration.md)
- Function signatures and command-line syntax: [reference/api.md](reference/api.md)
