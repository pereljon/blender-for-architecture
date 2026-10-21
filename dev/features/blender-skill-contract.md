# blender-architectural-renders: scripts contract

The shared interface for the skill's `scripts/` folder. Holds module layout, function signatures, and behavior rules that the implementer and the test author both build against. Does not hold the skill prose (SKILL.md, reference/), which the development session writes.

Skill root: this repo.
Sources (read-only): `A` = render project A's `skill-excerpts/blender-helpers.py`, `B` = render project B's `renders/skill-excerpts/` (`scene_helpers.py`, `compose.py`, `annotate_plan.py`, `extract_plan.py`, `plan_config.example.json`). Target runtime: Blender 5.2.0 LTS (`/Applications/Blender.app/Contents/MacOS/Blender`), bpy/bmesh/mathutils only (no numpy). Plain-Python scripts run with `uvx --with pillow python -I` (and `--with pymupdf` for extract_plan).

## Global rules

- Units. `bhelpers.U` is metres per project unit; default `1.0`. `set_units("m")` sets 1.0, `set_units("ft")` sets 0.3048; `set_units(float)` sets any value. Every length argument of every Blender helper (positions, sizes, radii, bevels, tile sizes, joints, cut heights, plan widths, light rects) is in project units and is multiplied by `U` internally. Energies, angles, colors, sample counts, and pixel values are not scaled. `mannequin(height=...)` takes height in project units too.
- Colors passed to materials are linear RGB tuples; `srgb("#rrggbb")` converts. Accept hex with or without `#`.
- Every object a helper creates is linked to the scene collection and named exactly as given (Blender may append `.001` on collisions; helpers do not rename).
- No module-level side effects at import except constant definitions. `bhelpers` imports bpy at top (it is Blender-only).
- Each public function has a one-line docstring saying what it does; add a second line only for a non-obvious constraint. No other comments unless the reason is non-obvious.
- Keep behavior from the sources unless this contract changes it. Where A and B both have a function, merge as stated below.

## scripts/bhelpers.py (Blender)

Units and scene: `U`, `set_units(u)`, `clear_scene()` (remove all objects, meshes, materials, lights, cameras, curves).

Geometry:
- `new_obj(name, mesh, mat=None)`.
- `box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0, seg=2)`: A's version (bevel modifier, smooth shading, sharp from angle 40 degrees) with lengths scaled by U.
- `slab(name, pts, ztop, thick, mat=None, zbot=None)`: A. `ztop`/`zbot` are callables `f(x, y)` in project units, or numbers (accept a float and treat it as a constant function).
- `prism(name, pts, z0, z1, mat=None)`: B.
- `seg(name, a, b, t, z0, z1, mat=None)`: B.
- `cyl(name, x, y, z0, z1, r, mat=None, n=32, rot=None)`: B (rot in radians); `cyl_x(name, x0, x1, y, z, r, mat=None, n=32)`, `cyl_y(name, y0, y1, x, z, r, mat=None, n=32)`: A.
- `sphere(name, x, y, z, r, mat=None, scale=(1, 1, 1))`: B.
- `tube(name, pts, r, mat=None)`: A (NURBS, `use_fill_caps=True`).
- `polyline(name, pts, z, width, mat=None)`: B (POLY spline, fill caps).
- `lathe(name, profile, mat=None, n=64, plan=None)`: A. Profile (r, z) in project units; place with location (project units, caller multiplies by U or uses `place(ob, x, y, z)`).
- `place(ob, x, y, z, rot_deg=0.0)`: set location (scaled by U) and Z rotation.
- `placed(build, tx, ty, tz, rot)`: B.
- `cut_holes(prefixes, holes, solver="EXACT")`: B. `prefixes` accepts a str or a tuple.
- `look(ob, loc, target)`: loc and target in project units (scaled by U). Note: B's took metres; the contract scales.
- `person(mat, x, y, h=1.75)`: B's scale figure; default height 1.75 project units means metres; callers in feet pass `h=5.75`.

Materials (all return the material):
- `srgb(hexstr)`, `sock(node, name, kind=None)`, `osock(node, name, kind=None)`: A.
- `principled(name, color, rough=0.5, metal=0.0, **kw)`: A/B (identical).
- `emission(name, color, strength)`: A (emission-only shader). B's `emit` is dropped; overlays use `emission`.
- `wood_material(name, axis="Z", dark=..., light=..., rough=0.45)`: A.
- `planks(name, color, plank_w=0.18, plank_l=1.8)`: B, with plank sizes in project units (scaled by U; B's were inches and feet).
- `stone_tile(name, color, tile=0.6, tile_h=None, plane="xy", joint=0.01, rough=0.7)`: B, sizes in project units (B's `joint_in` becomes `joint`, a full joint width in project units).
- `fabric(name, color, scale=180.0, strength=0.35)`: B.
- `image_tile_material(name, path, mult=(1, 1, 1), rough=0.5, bump=0.1, spec=0.5)`, `projected_tile_material(name, path, size, rough=0.5, bump=0.1)`: A (`size` in project units).
- Use `sock`/`osock` for Mix node sockets everywhere (B's `planks` and `stone_tile` index Mix inputs by name; switch to `sock(mix, "A", "RGBA")` etc.).

Tiles (A, lengths in project units): `Face(origin, uax, vax, nax)`, `tile_poly(name, pts, uvs, nvec, mat, thick=0.010, bevel=0.0007)`, `PIECES` (module list), `face_piece(name, face, poly_uv, origin, mat, flips, tile=(1.20, 0.60), rot=False, thick=0.010)`, `u_pieces(u0, u1, start, sign, length=1.20, joint=0.002)`, `subtract(r, h)`, `tile_wall(tag, face, u0, u1, start, sign, rows, mat, rnd, holes=(), tile=(1.20, 0.60), joint=0.002)`, `export_pieces(path)` (write PIECES as JSON `{"pieces": [...]}`; poly in project units). `PIECES` stays in project units (not metres).

Plan input and correction layer (B): `load_plan(path)`, `fix_walls(walls, wall_fixes=(), wall_replace=(), tol=0.06)`, `cut_openings(walls, holes, min_piece=0.05)`, `walls_from_plan(walls, z0, z1, mat=None, prefix="wall_")` (new: one `box` per wall dict, named `f"{prefix}{k}"`, returns the list), `door_swings(doors, mat, z=0.06, width=0.04, skip=None)`. Keep B's comment block documenting WALL_FIXES, WALL_REPLACE, EXTRA_WALLS, reworded to say "project units". `tol`, `min_piece`, `z`, `width` are project units.

Lights (B, lengths in project units): `room_fill_lights(rooms, ceil, w_per_m2=24.0, color=...)` (energy = w_per_m2 times the room area in square metres), `opening_light(name, x0, x1, y0, y1, z, energy=900, color=...)`, `sun(elevation_deg, azimuth_deg, plan_north_deg=0.0, energy=3.0)`, `downlights(mat, rect, ceil, nx=3, ny=2, watts=45, tag="room", trim_r=0.06)`.

Render and cameras:
- `setup_cycles(samples, gpu=True, exposure=0.0, look="AgX - Medium High Contrast", max_bounces=10, glossy_bounces=6, transmission_bounces=10, sky=(0.55, 0.70, 0.95), sky_strength=1.0)`: merge of A and B. Creates the world with the sky color. Does not set resolution or output. Returns the scene. When `gpu` is True and no Metal device exists, fall back to CPU and print one warning line (do not raise).
- `set_resolution(res, aspect=0.625)`: resolution_x = res, resolution_y = round(res * aspect), percentage 100.
- `new_camera(name="cam", clip_start=0.05)`: B (clip_start in project units).
- `perspective_camera(loc, target, lens=24, sensor=36, shift_x=0.0, shift_y=0.0)`: B plus shift.
- `plan_camera(center, width, cut, floor_z=0.0, height=12.0)`: B; true cut by clip_start; `height` (camera height above floor_z) in project units; clip_end = height + 6 project units.
- `add_camera(view, res)`: A's VIEWS-entry dispatcher rebuilt on the two functions above. Perspective entry: `dict(loc, target, lens=24, aspect=0.625, shift_x=0, shift_y=0, hide=())`. Plan entry: `dict(plan=True, center=(x, y), width, cut, floor_z=0, aspect=1.0, hide=(), drop=(), keep=())`; for a plan entry with `drop` or `keep`, call `plan_cut` and `plan_light` too. `hide` sets hide_render on prefixed objects for this view. Calls `set_resolution(res, aspect)`. Returns the camera.
- `plan_cut(cut, floor_z=0.0, hide=(), drop=(), keep=())`, `plan_light(center, height=9.0, size=(36.0, 18.0), energy=14000)`: B, project units.
- `project_points(points)`: A (points in project units).
- `render(out)`: set filepath (absolute), PNG, `bpy.ops.render.render(write_still=True)`, then print exactly `DONE <out>`.

Plan overlays (B, project units): `dotted_square(name, px, py, half, z, mat, dash=0.02, pitch=0.04, w=0.03)`, `dashed_path(name, pts, z, mat, dash=0.2, gap=0.12, w=0.03)`, `dotted_rect(name, x0, x1, y0, y1, z, mat, dash=0.09, pitch=0.15, w=0.025)` (B's foot defaults converted to metres and rounded).

## scripts/mannequin.py (Blender)

Imports from bhelpers (`from bhelpers import U, new_obj, principled` style must still see `set_units` changes: read `bhelpers.U` at call time, not at import). Functions: `ik(a, t, l1, l2, pole)` (A's `_ik`, public), `mannequin(pose, height=1.78, mat=None, prefix="man_")` (A; pose coordinates and height in project units, converted by U at entry; object names start with `prefix`), `EXAMPLE_POSE` (A's, in metres). Private `_ellipsoid`, `_limb` as in A.

## scripts/checks.py (Blender)

- `clash_check(a_prefixes=("man_",), b_prefixes=(), ignore=())`: A. Returns `[(a_name, b_name), ...]`. Also report containment: a pair counts as a clash when the surfaces overlap OR any vertex of `a` lies inside `b` (closed-mesh ray-parity test against `b`'s BVH; skip the containment test when `b` has open boundary edges and note that in the docstring).
- `coplanar_check(prefixes=None, tol=0.0005, min_area=1e-6)`: new. Returns `[(name1, name2), ...]` for pairs of mesh objects (both named with one of `prefixes`, or all meshes when None) that have world-space faces with normals pointing the same way (dot > 0.9995; faces back to back, such as butt joints, do not z-fight and are not reported), plane distance below `tol` metres, and overlapping in-plane extents with overlap area above `min_area` square metres. Prefilter pairs by world bounding boxes (inflated by tol). Faces with area below min_area are ignored. Purpose: catch z-fighting and black strips before rendering.
- `fail_on(hits, label)`: if `hits` is non-empty, print `FAIL <label>: <hits>` and `sys.exit(1)`; else print `OK <label>`.

## scripts/sheets.py (plain Python + Pillow)

From A part B: `PAGE`, `S`, `INK`, `DIM`, `font(size, bold=False)` (try Arial, then Arial Bold, then `/System/Library/Fonts/Helvetica.ttc`, then `ImageFont.load_default(size=size)`; never raise for a missing font), `fmt(v, decimal=",")` (A's `mm`, with the decimal separator as a parameter; keep `mm = fmt` as an alias), `Sheet(title, subtitle, page_no, total, footer, page_label="Sheet {} of {}")`, `Draw(sh, ox, oy, scale)` with `P`, `rect`, `line(dash=...)`, `text`, `hdim`, `vdim`, `_pack_once`, `pack(items, tw=1.20, th=0.60, kerf=0.003)`, `save_pdf(images, path, resolution=200)`, `check_rounding(values, step)` (new: return the values that are not multiples of `step` within 1e-9 relative tolerance; sheet generators assert it is empty for owner-facing dimensions). `if __name__ == "__main__"`: A's packing self-test.

## Copied scripts (B, unchanged except the usage line's path)

`scripts/compose.py`, `scripts/annotate_plan.py`, `scripts/extract_plan.py`, `scripts/plan_config.example.json`.

## templates/scene_template.py

A runnable starting scene: argparse (`--view`, `--res`, `--samples`, `--gpu`, `--out`, one example study flag `--option a|b`), `sys.path` insert of the folder containing `bhelpers.py` (relative to the script: `os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")`, with a comment that the project copies `scripts/` into `lib/`), `set_units("m")`, a constants block, `build(opts)` that makes a 3 x 4 m room with a floor, walls, a door opening, a counter and the example-option object, a `VIEWS` dict with one perspective and one plan entry, `clash_check`/`coplanar_check` via `fail_on` before rendering, then `render(args.out)`. Parse args after `--` (`sys.argv[sys.argv.index("--") + 1:]` when present).

## tests/ (written by the test author, not the implementer)

`tests/run_tests.sh` runs everything headless and exits non-zero on any failure; each step under a timeout (`timeout`/`gtimeout` if present, else Python `subprocess` timeouts in a runner). Blender steps use `--factory-startup -b` and render at 160 px, 8 samples, CPU. Required checks: every bhelpers public function called at least once in metres and a subset in feet (box extents match `U` scaling within 1e-6); mannequin builds 20+ `man_*` objects; clash_check returns a hit for an overlapping pair, none for a clear pair, and a hit for a fully contained small box; coplanar_check returns the pair for two coplanar overlapping boxes and nothing after a 2 mm offset; the template renders both views and prints `DONE`; compose.py and annotate_plan.py produce images from the smoke renders; extract_plan.py runs on a generated vector PDF (PyMuPDF draws a few gray-filled rectangles) and returns walls; pack respects kerf and never overlaps pieces; check_rounding flags a non-multiple. Tests write output only under `tests/out/` (gitignored by a `tests/.gitignore`).

## Revision 2 (2026-10-17, from the pre-release review)

Skill folder renamed to `blender-architectural-renders`.

Code changes (implementer):
- R1 `clash_check(a_prefixes=("man_",), b_prefixes=None, ignore=())`: `b_prefixes=None` (or empty) means every other visible mesh or curve not in A and not ignored.
- R2 `plan_light(center, floor_z=0.0, height=9.0, size=(36.0, 18.0), w_per_m2=6.0)`: light at `(floor_z + height) * U`; energy = w_per_m2 times the light's area in square metres (unit-independent exposure). Tune the default so a ground-floor plan of a 0.5 grey floor renders at a mean between 0.6 and 0.9 at the template's settings. `add_camera` passes the entry's `floor_z`.
- R3 `plan_cut` drop squashes about the floor plane: `ob.matrix_world = T(0,0,fz) @ Diagonal(1,1,s,1) @ T(0,0,-fz) @ ob.matrix_world` with `fz = floor_z * U`, `s` chosen so the object's top lands `0.06 m` below the cut (in metres, through U). Works for objects whose origin is not at the floor.
- R4 `prism` recalculates face normals (as `slab` does).
- R5 Metric defaults become `None` and resolve to the metric value divided by `U` at call time: tile `(1.20, 0.60)`, `joint=0.002`, `thick=0.010`, `bevel=0.0007` (tile_poly), `trim_r=0.06`, mannequin `height=1.78`. `EXAMPLE_POSE` stays in metres; `mannequin` documents that a feet project must give its own pose.
- R6 Tile piece names use separators: `f"wt_{tag}_{ci}_{ri}_{k}"`.
- R7 `extra_walls(rows)` in bhelpers: converts `(kind, x0, x1, y0, y1)` tuples to wall dicts like those from `load_plan`, so `fix_walls(...) + extra_walls(EXTRA_WALLS)` feeds `cut_openings` and `walls_from_plan`.
- R8 Mannequin pose gains optional `floor_z` (project units, default 0): feet, ankles, and the standing pelvis sit relative to it.
- R9 `annotate_plan.py`: pixels per unit = `max(W, H) / width`, matching Blender's ortho_scale on the larger side; the docstring says `width` is the plan view's `width` (the ortho span of the larger side).
- R10 `extract_plan.py` and `annotate_plan.py` docstrings say "project units", not "plan units".
- R11 `sheets.save_pdf(images, path, resolution=200)` accepts PIL images or file paths. New `sheets.items_from_pieces(path, unit=1.0)`: reads the `export_pieces` JSON and returns `[dict(id, w, h)]` in metres (each piece's polygon bounding box times `unit`), ready for `pack`.
- R12 Template: add `--export-pieces PATH` (build, call `export_pieces(PATH)`, print `DONE <PATH>`, skip rendering). Its tile-free scene writes an empty pieces list; that is fine.

Tests (test author), in addition to keeping all existing checks:
- T1 Plan entry with drop/keep: a `cyl` from 0 to 2 (origin at mid-height) dropped under a 1.2 cut ends with top below the cut and bottom at the floor (within 1e-4 m); the same in feet and with `floor_z` above 0; an object above the cut is hidden; the overhead light sits above `floor_z + cut`.
- T2 `clash_check` with default `b_prefixes` reports an overlap with an unnamed-prefix object; open-mesh containment is skipped (a small box inside an open mesh is not a hit unless surfaces touch); a clockwise `prism` butted against a box is not a coplanar hit, and a clockwise prism overlapping a box is.
- T3 `check_png.py` also checks mean brightness is between 0.05 and 0.98 (catches black or blank renders).
- T4 `extra_walls` output passes through `cut_openings` and `walls_from_plan`; tile names are unique for 12 columns by 12 rows; `items_from_pieces` returns metres for a feet export; `save_pdf` accepts paths; `annotate_plan.py` on a portrait image (aspect > 1) puts the ring at the expected pixel; the mannequin with `floor_z=3.0` has its lowest point near 3.0 m.
- T5 Template `--export-pieces` prints DONE and writes valid JSON.

Skip: `Material.use_nodes` deprecation (works on 5.2; the skill targets 5.2 only).

## Review findings and resolution (2026-10-17)

Pre-release review by an opus subagent, verified by headless runs.
- I1-I4 (clash default empty, plan_light under upper floors, drop squash about origin, prism normals): fixed by R1-R4; covered by tests T1-T2.
- I5 (no API reference): `reference/api.md` generated from the code signatures; `tests/test_api_doc.py` fails when a public function lacks a line.
- M1 exit code and M5 one view per run: SKILL.md Environment. M2 plan_light exposure: R2 (default 6 W/m2, tuned to 0.78 in metres and 0.76 in feet). M3 metric defaults: R5. M4 tile names: R6. M6 EXTRA_WALLS: R7 and plan-input.md. M7 sheets region/out: plan-input.md. M8 construction sheets: R11, R12, construction-sheets.md. M10 floor height: R8. M11 portrait plans: R9. M12 copied files: setup step copies `*.py` and `*.json`; `.gitignore` covers `__pycache__/` and `tests/out/`. M13 terminology: R10.
- M9 (`Material.use_nodes` deprecated in Blender 6): not fixed; the skill targets 5.2.
- T1-T3 weak tests: replaced by T1-T5.
- Found while running the first suite: `coplanar_check` reported back-to-back faces (butt joints); changed to same-facing only, with a regression test.
Suite after fixes: 31 passed, 0 failed.

## Revision 3 (2026-10-17, from the render projects' reviews)

Sources: `../inputs/blender-skill-inputs.md`, reviews by render project B (items 10-1 to 10-11) and render project A (items A1 to A13).

Code changes (implementer):
- R13 Feet defaults (10-2, 10-3, A2, A3). These defaults become `None` and resolve to the metric value divided by `U`: `planks(plank_w=0.18, plank_l=1.8)`, `stone_tile(tile=0.6, joint=0.01)`, `fix_walls(tol=0.06)`, `cut_openings(min_piece=0.05)`, `door_swings(z=0.06, width=0.04)`, `plan_camera(height=12.0)` (and `clip_end` = height + 6 m), `person(h=1.75)`, `dotted_square(dash=0.02, pitch=0.04, w=0.03)`, `dashed_path(dash=0.2, gap=0.12, w=0.03)`, `dotted_rect(dash=0.09, pitch=0.15, w=0.025)`. `tile_wall`'s sliver threshold becomes `0.004 / U`. Audit the rest of `bhelpers.py` and `mannequin.py` for metric literals applied to project-unit values; fix each the same way and list them in the report.
- R14 `plan_light(center, floor_z=0.0, height=None, size=None, w_per_m2=6.0, extent=None)` (10-1). `height` None is 9 m. `size` None is the larger, per axis, of (36 m, 18 m) and 1.5 times `extent`, where `extent` is the plan's (x, y) span in project units. Energy stays w_per_m2 times area. `add_camera` passes `extent` from the entry's `width` and `aspect` (aspect <= 1: `(width, width * aspect)`; else `(width / aspect, width)`).
- R15 Every plan entry runs `plan_cut` and `plan_light` (10-5, A6). `add_camera` calls both for any plan entry; `drop` and `keep` stay optional. Ceilings and lights above the cut are then hidden in every plan view.
- R16 Mannequin legs (A1). Assign ankles by side: the ankle with the larger dot product with `r` (relative to the pelvis root) goes to side 1 (right). Remove the `f.y > 0` swap.
- R17 `cyl(..., rot=None)` becomes `rot_rad=None` (A4): an Euler tuple in radians, named so. Update `cyl_x`, `cyl_y`, and every caller.
- R18 `annotate_plan.py` (10-4). Default ring radius is `0.014 * max(W, H)` pixels. A callout's `"r"`, when given, stays in project units. Label and leader offsets scale with the ring radius (offset x 1.33 r; above -1.33 r; below -0.42 r; leader end +0.33 r), so their look does not depend on the unit.
- R19 Usage lines in `annotate_plan.py`, `compose.py`, `extract_plan.py`, `sheets.py` say `blender/lib/...`, not `scripts/...` (10-11).
- R20 Regenerate `reference/api.md` after the signature changes (the api sync test enforces it).

Tests (test author), in addition to keeping all existing checks (update callers of `cyl(rot=)`):
- T6 Mannequin: for faces (1, 0), (-1, 0), (0, 1), (0, -1), with ankles placed 0.1 m to each side of the root, side 1's knee lies on the figure's right (positive dot with the right vector, relative to the root) and side -1's on the left.
- T7 Feet defaults: in feet with defaults, `person` is 1.75 m tall; `door_swings` arcs sit at 0.06 m; `plan_camera` clip_start equals (12 m - cut); an overlay mark is 0.03 m wide; `planks` brick width is 1.8 m; `cut_openings` and `fix_walls` give the same result in feet as in metres for the same geometry. `tile_wall` skips a 3 mm sliver and keeps a 5 mm piece in both units.
- T8 A plan entry without `drop` or `keep`: a ceiling box above the cut and every scene light are hidden from render, and `plan_overhead` exists.
- T9 `plan_light` size: a metric 4 m plan gets a 36 by 18 m light; an 84 ft by 60 ft plan gets at least 1.5 times its extent, in metres. The existing brightness checks still pass.
- T10 `annotate_plan.py`: the same image annotated with `width` 84 and with `width` 25.6 has the same ring radius in pixels.

Docs (development session): SKILL.md (A5 face-plane wording; A9 sRGB wording; A7 rounding rule; A8 uvx fallback; 10-7 finals to a gitignored `out/`, only delivered images into dated deliverables, commit only tracked files; 10-9 stale-render rule; 10-10 batch recipe; A13 rough-in photo before trade sheets). views.md (10-5 and A6 table and lighting; 10-8 ruler only when someone reads dimensions off the plan). plan-input.md (10-6 accuracy example). construction-sheets.md (A10 never retype a model position). studies.md (A11 dark world for enclosed rooms and night views).

Approved by the user 2026-10-17, with A12: a short optional walkthrough-video section in studies.md, no code. Docs applied by the development session; the rough-in photo (A13) went into construction-sheets.md "Check before sending" rather than the loop, since only trade sheets need it.

### Revision 3 results (2026-10-17)

- R13-R19 implemented by a sonnet subagent; R20 (api.md lines for the 13 changed signatures, plan-entry and callout notes) regenerated from the code by the development session. The implementer's R13 audit also fixed `new_camera(clip_start)` (0.05 project units became 0.05 m); every other literal it found already acted on metres.
- T6-T10 written by a separate sonnet subagent (`tests/bl_rev3.py`, `tests/test_rev3.py`); `bl_helpers.py` updated for `rot_rad` and `clip_end` = height + 6 m.
- Mutation check: with R15, R16, the `tile_wall` sliver threshold, and R18's default radius each reverted in a copy, T6, T7, T8, T9 and T10 all fail.
- Callout offsets (R18) have no automated test; checked by eye on an annotated template plan.
- Suite: 35 passed, 0 failed.

### Skill evals (2026-10-17, fresh sonnet subagents, skill not named in the prompt)

- E1 bedroom from dimensions: found and followed the skill (setup, template, checks, preview then final); coplanar hit on window casings found and fixed; image correct. Gap: did not walk the QA checklist.
- E2 feet bathroom, plan cut and figure: `set_units("ft")`, figure clash found and fixed, both images read correctly. Gaps: (a) a clip cut renders every object crossing the cut as a black section (template walls are off-white but render black), and views.md's "grey poché" gives no way to get it; E2 found `drop=("wall_", "door_")` itself. (b) views.md says to avoid a grey surround but gives no recipe; `plan_light`'s grey world causes it; E2 added a white emission box under the floor in plan only.

## Revision 4 (2026-10-17, from the skill evals; approved by the user)

Code (implementer):
- R21 `add_camera`: for a perspective entry, `hide` sets `ob.visible_camera = False` (the object still casts shadows, blocks light, and shows in reflections). For a plan entry, `hide` keeps setting `hide_render = True`. Update the `add_camera` docstring.

Tests (test author):
- T11 Perspective entry with `hide=("wall_s",)`: `wall_s` has `visible_camera` False and `hide_render` False; another object is unaffected. Plan entry with the same `hide`: `wall_s` has `hide_render` True.
- T12 `clash_check` reports two boxes that touch face to face (no overlap) as a hit, and reports nothing for the same boxes 1 mm apart. (Pins the behavior the docs describe.)

Docs (development session): views.md (clip renders cut objects as dark sections, `drop` for readable items; white surround recipe; perspective `hide` is camera-only); SKILL.md Checks (touching counts as a clash) and QA list (a black mirror reflects a hidden object or the dark world).

### Revision 4 results (2026-10-17)

- R21 implemented; `Object.visible_camera` verified on Blender 5.2.0 LTS. T11 and T12 in `tests/bl_rev4.py`; `bl_helpers.py:302` updated from the old perspective-hide assertion to the R21 behavior. Mutation check: reverting R21 fails T11. Docs applied. Suite: 37 passed, 0 failed.

## Revision 5 (2026-10-19, extensions; proposed by render project B, taken on by the user's decision)

Source: `../inputs/2026-10-19-extensions-proposal.md`. Verified in skill-developer on 2026-10-19: Blender 5.2.0 LTS ships numpy 2.3.4; bonsai, sun_position, and point_cloud_io are installed; with each enabled per run (`default_set=True`), IfcOpenShell 0.9.0.post1 imports, and every operator and property the draft names exists.

Docs:
- D1 SKILL.md Environment: Blender ships numpy; other packages come only with an extension. The helpers stay numpy-free.
- D2 SKILL.md: an Extensions section after Scripts (the draft's table and two rules), and a Reference line for `reference/extensions.md`.
- D3 `reference/extensions.md` from the draft, with three changes: state the Sun Position background update as T14 finds it; drop the unverified DWG converter and say "No extension reads DWG; ask for a DXF. When no CAD file is shared, use the PDF extraction in `plan-input.md`"; write the per-run command with `$BLENDER`, defined once.
- D4 `reference/plan-input.md`: the extraction can miss short wall pieces where walls meet; when walls shift to match site measurements, shift the door swings and leaves in that region too.

Tests (test author):
- T13 `tests/bl_extensions.py`, an optional step. When bonsai, sun_position, or point_cloud_io is not installed, print `SKIP` and pass. Otherwise enable each with `default_set=True`, import ifcopenshell, check every operator and property named in `reference/extensions.md`, write a two-wall IFC (one east-west, one north-south) from feet by the recipe, and check each wall's world bounding box against the source within 0.01 ft. Then load the IFC in Bonsai, generate a plan drawing headless, and check an SVG appears in `drawings/`.
- T14 Sun Position in a background run: set latitude, longitude, date, and a `sun_object`; the sun's rotation differs between 09:00 and 15:00.
- T15 Keep-in-step: every `bpy.ops` name and `sun_pos_properties` field in `reference/extensions.md` appears in T13's check list (plain Python, like `test_api_doc.py`).

Evals: one fresh subagent, skill not named: "Write an IFC of a two-room plan from these dimensions for the architect, and a plan drawing from it."

### Revision 5 results (2026-10-19)

- D1-D4 applied by a sonnet subagent; T13-T15 written by a separate sonnet subagent (`tests/extensions_names.py`, `tests/bl_extensions.py`, `tests/test_extensions_doc.py`). `bl_extensions` skips with `SKIP` when an extension is missing (`EXT_FORCE_MISSING` forces it).
- Sun Position: in a background run, setting `time` turns the sun object at once (2.885 rad between 09:00 and 15:00).
- Mutation check: with one importer removed from `reference/extensions.md`, `test_extensions_doc` fails.
- Suite: 41 passed, 0 failed.
- Eval 1 (fresh sonnet subagent, skill read by path, no Skill call): IFC of a two-room plan exact to 0.0 ft; it skipped Bonsai because the prompt barred installs and the doc gave no way to see what is installed. Fixed: `-c extension list`, numpy for IfcOpenShell scripts, metres back to feet, corner rule.
- Eval 2 (same setup, installed extensions allowed per run): IFC within 0.001 ft; Bonsai plan SVG generated headless, wall outline 24 by 14 ft at 1:100, checked by eye. Fixed: drawing file name, plan off-centre on the sheet (crop before review), centreline placement.

### Revision 5 review findings (2026-10-19)

Architect review (opus, read-only) and code review (opus; suite 41/41 on an export of the branch).
- Fixed before merge: installs and syncs now need the user's consent, with the download size (architect F3); an installed extension that fails to enable fails `bl_extensions` instead of skipping, `EXT_REQUIRED=1` turns a skip into a failure, and skips show in the suite summary (F12, code 1); T15 compares the doc's field lines as sets (code 2); T13b asserts two walls and T13c the named drawing file (code 3, 4); the per-run command asserts the enable (F6, code 6); numpy wording (F7); the SKILL.md table claims only what was verified (F8); counter-clockwise rotation (F9); the LAS importer centers scans on the origin (F10); Bonsai's recent-projects list noted (F5, code 5).
- Verified by the reviewers: `default_set=True` in a `--factory-startup` run does not rewrite `userpref.blend`.
- Open before release (skill `docs/ISSUES.md`): DWG route; IFC written from the scene script's wall records, not retyped (F1); Sun Position against `bhelpers.sun()`, `north_offset` in radians, and a solar-noon check (F2, F13); description triggers for IFC, scan, and sun tasks, with a discovery eval (F11); drawing geometry check (F14); doc keep-in-step for extension ids and `ifcopenshell.api` names (F15); re-eval of the post-eval fixes and evals for Sun Position, point clouds, DXF (F16); Bonsai enabled in the user's preferences since 10:35 (F4, asked of the user).
- F4 resolved 2026-10-19: the user enabled Bonsai in their Blender preferences themselves, and it stays enabled.
- DWG decided 2026-10-19 by the user: DXF is enough; DWG is out of scope for now. Rejected for now: a DWG route through the ODA File Converter or LibreDWG. The DXF extensions in the doc (`cad2cube`, `export_autocad_dxf_format_dxf`) were picked from the extension listing and are untested.

## Revision 5b (2026-10-21, remaining items)

Source: "Revision 5 review findings" above (F1, F2, F11, F13 to F16, the DXF line), skill `docs/ISSUES.md` Planned, `../inputs/2026-10-19-wall-records.md`. Investigated against this repo at `ad71f03` and Blender 5.2.0 LTS (build hash `fbe6228777e7`, 2026-07-14), with scratch probes outside the repo. Nothing was installed. One probe changed shared extension state; see Verified, wheels, and question C2.

Upstream versions read (extensions.blender.org API v1 index, fetched 2026-10-21; archives read, never run):

| Extension | Version | Archive bytes | Licence | Blender min | Archive sha256 (first 12) | Source |
|---|---|---|---|---|---|---|
| `bonsai` (installed) | 0.9.0-post1 | 140,915,735 | GPL-3.0-or-later | 5.1.0 | `5ee3033932f5` | IfcOpenShell |
| `sun_position` (installed) | 4.4.0 | 26,592 | GPL-3.0-or-later | 4.2.0 | `b8a83c2ff04f` | maintainer pioverfour |
| `point_cloud_io` (installed) | 0.6.0 | 6,458,674 | GPL-3.0-or-later | 5.1.0 | `262fbc68732f` | StudioMedio |
| `cad2cube` | 1.5.1 | 2,590,116 | GPL-3.0-or-later | 4.2.0 | `b2f2cb3105da` | github.com/lylongfts/CAD2CUBE |
| `export_autocad_dxf_format_dxf` | 2.2.4 | 33,206 | GPL-2.0-or-later | 4.2.0 | `eb49707876bc` | projects.blender.org/extensions/io_export_dxf |
| `import_autocad_dxf_format_dxf` | 0.9.10 | 57,092 | GPL-2.0-or-later | 4.2.0 | `bc82f6498e92` | projects.blender.org/extensions/io_import_dxf |

Libraries: IfcOpenShell 0.9.0.post1 (Bonsai wheel, and uvx from the local cache with numpy 2.4.6); ezdxf 1.4.4 (Bonsai wheel) and 1.4.5 (uvx cache); laspy 2.7.0 (Point Cloud I/O wheel).

### Verified (2026-10-21)

DXF:
- Blender 5.2 has no DXF route of its own. A `--factory-startup` run lists no `bpy.ops` name containing `dxf` or `dwg`. Its bundled add-ons are `io_anim_bvh`, `io_scene_fbx`, `io_scene_gltf2`, `io_curve_svg`, `io_mesh_uv_layout`, and non-IO add-ons. The two DXF add-ons left the bundle after 4.1 (both extension pages say so).
- The listing has three DXF add-ons, not two: `cad2cube`, `import_autocad_dxf_format_dxf` (the former bundled importer), and `export_autocad_dxf_format_dxf` (the former bundled exporter). The doc names only the first and the third.
- `cad2cube` 1.5.1 (source read): operator `import_scene.cad2cube_dxf`. It reads DXF through ezdxf 1.4.4, bundled as a wheel with pyparsing 3.3.2 and fonttools 4.63.0. Defaults that matter for this skill: `recenter_mode="BBOX"` moves the drawing off the CAD origin; `units_mode="AUTO"` reads `$INSUNITS`, and a unitless file falls back to millimetres (scale 0.001). Bug: `$INSUNITS` 21 (US survey feet) maps to 0.9144, a yard (`core/reader.py`, `_INSUNITS_TO_METERS`). DWG support was removed in 1.5.0. One maintainer, three reviews, first published 2026-06-28. No network, subprocess, or exec calls in its own code.
- `export_autocad_dxf_format_dxf` 2.2.4 (source read): operator `export.dxf`. It writes DXF R12 (`AC1009`), meshes as `3DFACE` by default, and only selected objects by default (`onlySelected=True`); one review reports "0 objects exported". R12 has no `$INSUNITS`, so the file carries Blender metres with no unit. It is a 3D mesh export, not a drawing.
- `import_autocad_dxf_format_dxf` 0.9.10: operator `import_scene.dxf`, based on dxfgrabber; the page says "offered as it is, with limited support". One review reports a `faces.new` error on a CadMapper file.
- Wheels shared by extensions: Blender keeps the newest version of each wheel name across all enabled extensions (`_bpy_internal/extensions/wheel_manager.py`, `wheel_list_deduplicate_as_skip_set`). Installing `cad2cube` would not downgrade Bonsai's fonttools 4.67.0 or pyparsing 3.3.3; both ship ezdxf 1.4.4.
- ezdxf without any DXF extension: in a Blender run whose wheels include Bonsai's, and through `uvx --with ezdxf python -I`, a probe wrote an R2010 DXF in feet ($INSUNITS 2) with two layers of closed wall outlines, a TEXT, and a rendered linear DIMENSION. Reading it back gave every entity on its layer and each outline's extents exactly.

Extension wheels (from the probes, and `addon_utils.py` in the app bundle):
- Blender keeps extension wheels in one shared folder, `extensions/.local/lib/python3.13/site-packages`, on `sys.path` in every run.
- When a run enables a set of extensions that differs from the last run's set, Blender syncs that folder to the new set (`addon_utils.py`, `_initialize_extensions_compat_ensure_up_to_date` and the wheel sync after it). A run that enables nothing skips the sync.
- Observed: a probe that enabled only `sun_position` (with `default_set=True`, `--factory-startup`) emptied the folder at 01:20. Before it, `ifcopenshell`, `ezdxf`, `laspy`, and `shapely` imported in a run that enabled nothing, from wheels left by the 01:12 suite run. After it, none of them imported. The wheels themselves stay in each extension's `wheels/` folder, so the next run that enables Bonsai or Point Cloud I/O extracts them again.
- Consequences: `import ifcopenshell` works without enabling Bonsai only by accident of the last sync, so the doc's rule stays right. Two Blender runs that enable different sets at the same time can remove each other's packages mid-run. Switching sets re-extracts Bonsai's 92 wheels (136 MB on disk) each time.

IFC from wall records (prototype `ifc_walls.py`, plain Python through uvx, outside the repo):
- Six records in feet with `unit=0.3048`: dicts with `kind`, a bare tuple, walls along x and along y, and a column with its own `z0`, `z1`, and `ifc_class`. Every element read back with `use-world-coords` matched its record's box exactly (worst 0.0 m). `ifcopenshell.validate` reported nothing. Run time 0.26 s.
- `ifcopenshell.api.run("pset.add_pset", ...)` and `run("pset.edit_pset", ...)` set `Status` to `NEW` or `EXISTING`. The IFC4 templates for `Pset_WallCommon`, `Pset_ColumnCommon`, and `Pset_BeamCommon` each have `Status`, with values NEW, EXISTING, DEMOLISH, TEMPORARY, OTHER, NOTKNOWN, UNSET.
- `ifcopenshell.api.project` and the other submodules are not attributes of `ifcopenshell.api` until imported; `ifcopenshell.api.run("module.function", ...)` works with no extra import and gives no DeprecationWarning in 0.9.0.post1.
- With a y-running rect placed at (x1, y0) and rotated 90 degrees counter-clockwise, the thickness runs west to x0. The records need no corner or centreline rule, because they are already the boxes the scene builds.

Bonsai plan SVG (the suite's own `tests/out/drawings/LEVEL 1 PLAN.svg` from 01:12, two walls):
- One `<g>` carries `ifc:plane` (cut plane; its z is 1.6 m) and `ifc:matrix3` (`[[10,0,250],[0,10,250],[0,0,1]]` at 1:100). Each cut element is a `<g class="IfcWall <GlobalId> cut material-null">` holding one path of absolute `M`, `L`, and `Z` commands.
- Model metres from SVG millimetres: x = (x_svg - 250) / 10, y = (250 - y_svg) / 10. The y axis is flipped, unlike what `matrix3` alone suggests. Both walls of T13b came back exact to 5e-7 m: `ew` 0 to 10 by 0 to 0.5 ft, `ns` 19.5 to 20 by 0 to 10 ft.

Sun Position 4.4.0 (source read; probe with only `sun_position` enabled per run):
- `north_offset` is a FloatProperty with unit ROTATION, so it is in radians. The extension adds it to the azimuth (`sun_calc.py`, `azimuth += sun_props.north_offset`). The sun object gets `(elevation - pi/2, 0, -azimuth)`.
- `sun_elevation` and `sun_azimuth` are read-only radians. `sun_azimuth` returns the true azimuth (it subtracts `north_offset`). They update on every property set, with or without `sun_object`.
- Mapping to `bhelpers.sun(elevation_deg, azimuth_deg, plan_north_deg)`: `north_offset = -math.radians(plan_north_deg)`. For plan north 0, 30, and -75 degrees at 09:00, 12:00, and 15:30, the light direction of `bh.sun(degrees(sun_elevation), degrees(sun_azimuth), plan_north_deg=N)` matched the Sun Position object's to 0.00000 degrees.
- Solar noon at 37.77 N, 122.42 W, UTC -8, 2026-06-21, searched minute by minute: 12:12, elevation 75.667 degrees, azimuth 180.39 degrees. Independent checks: 90 - 37.77 + 23.44 = 75.67 degrees; the NOAA noon formula gives about 12:11.5 (computed by hand, not run). Without refraction the elevation is 75.663.
- `UTC_zone` is the standard-time offset; `use_daylight_savings` subtracts one more hour (`move_sun`).

Not verified: a Point Cloud I/O import (probing it would have synced the wheels again); a real architect's DXF; any DXF extension at run time; the Bonsai drawing for more than two walls or with a column.

### Simplify before building (architect, 2026-10-21)

Each kept part traces to a finding or decision; each deleted part, with the reason:
- Deleted (question A1): both DXF extension rows. No project exchanges DXF (render project B has only PDFs), and neither extension feeds the skill's pipeline. `cad2cube` brings DXF linework into Blender as curves, not wall records. The exporter writes 3D faces in unitless metres, not a drawing. ezdxf, already present, reads and writes DXF with layers and units (verified). The 2026-10-19 decision ("DXF is enough") sets scope; it does not name an extension.
- Deleted: merging collinear wall pieces. The input accepts one IfcWall per piece, and project B's trial wrote 36.
- Deleted: the hand recipe's placement rules in `reference/extensions.md` (rotation, east face, centreline, corner rule, feet-to-metres division, the compare step). R33 does them and checks itself.
- Deleted: the `ifcopenshell.api` half of F15 as a doc test. Once the recipe goes, the doc names no API calls; T24 instead checks that every `run("...")` name in `scripts/ifc_walls.py` resolves in the installed IfcOpenShell.
- Deleted: a solar-position calculator in `bhelpers` and a `bhelpers` wrapper around Sun Position. Sun Position gives the angles; three documented lines pass them to `sun()`. `bhelpers` stays free of extension imports.
- Deleted: a discovery eval through the harness before install. The harness reads the installed description, so it cannot see the draft. E7 ranks descriptions instead; the real discovery eval runs after install, as `AGENTS.md` Releases already requires.
- Deleted: re-running Revision 5 evals 1 and 2 as written. The rules they tested are replaced by R33; E3 tests the new route.
- Kept: `Status` from `kind` (question B1). It is two API calls, and existing versus new is what an architect reads first in a remodel model.
- Kept: the drawing check as code (`check_drawing`), not as a review by eye (F14).
- Added from a verified finding: one extension set for every run that enables any (D16). Without it, parallel runs can lose packages, and each switch re-extracts 136 MB.

### Code (implementer)

Keep out: the implementer does not edit `tests/`; the test author does not edit `scripts/`, `templates/`, or `reference/`.

- R33 `scripts/ifc_walls.py` (new). The module imports only `json`, `re`, and `xml.etree.ElementTree` at the top. `ifcopenshell` and `numpy` are imported inside the functions that need them, so `drawing_walls` runs in plain Python. It runs in Blender in a run that enables Bonsai, or through `uvx --with ifcopenshell --with numpy python -I`.
  - `write_walls_ifc(walls, path, z0, z1, unit=1.0, prefix="wall_", storey="Level 1", tol=0.003)`:
    - `walls` items are the wall records of `load_plan`, `fix_walls`, `extra_walls`, and `cut_openings`: dicts with `x0`, `x1`, `y0`, `y1`, and optional `kind`, `z0`, `z1`, `ifc_class` (default `"IfcWall"`); or tuples `(x0, x1, y0, y1)`. Normalise so lows come first. A record's own `z0`, `z1` override the arguments.
    - `unit` is metres per record unit and applies to every length. Pass `bh.U` from a scene script.
    - Write IFC4 through `ifcopenshell.api.run`: project; metre units by `run("unit.assign_unit", f, units=[run("unit.add_si_unit", f, unit_type="LENGTHUNIT")])` (with no `units`, `assign_unit` writes millimetres); Model and Body contexts, `IfcSite`, `IfcBuilding`, and one `IfcBuildingStorey` named `storey`.
    - Per record k: one element of its `ifc_class`, named `f"{prefix}{k}"` (the name `walls_from_plan` gives the box). The record runs along x when its x length is at least its y length. Along x: placement at (x0, y0, z0), length x1 - x0, thickness y1 - y0. Along y: placement at (x1, y0, z0), rotated 90 degrees counter-clockwise, length y1 - y0, thickness x1 - x0. Height z1 - z0.
    - When `kind` is `"new"` or `"existing"`, add `Pset_<class without Ifc>Common` with `Status` `NEW` or `EXISTING`. Other kinds get no pset.
    - Write the file, open it again, and take each element's world box with `use-world-coords`. Raise `ValueError` naming up to five elements when any box differs from its record by more than `tol` metres. Return `{name: GlobalId}` in record order.
  - `drawing_walls(svg)` (amended after the tests, see "Revision after the tests"): read the Bonsai drawing SVG.
    - Raise `ValueError` unless exactly one `<g>` has `ifc:matrix3`. Its `ifc:plane` gives the cut height: row 3, column 4.
    - A cut group is a `<g>` inside that group whose class list has the word `cut`. Its GlobalIds are every class word of 22 characters from `0-9A-Za-z_$`, plus its `ifc:guid` attribute when present. Bonsai puts the GlobalIds of merged walls in the class and gives an element it does not merge (a column) an `ifc:guid` attribute.
    - Read every point of every path in the group, outer rings and holes alike. Raise `ValueError` on any letter other than `M`, `L`, `Z`, or an exponent `e` or `E`; lowercase (relative) commands are refused too.
    - Map with x = (x_svg - tx) / sx and y = (ty - y_svg) / sy from `matrix3`.
    - Return `(cut_z, groups)`: cut_z in metres, and `groups` a list of `(ids, (x0, x1, y0, y1))`, where ids is the sorted tuple of the group's GlobalIds and the box bounds every point of the group, in metres. The list is sorted by ids. A group with no GlobalId or no point is left out.
  - `check_drawing(svg, ifc_path, tol=0.003)`: compare the drawing with the IFC, cut group by cut group.
    - The elements to find are the `IfcElement`s with a body whose world z range contains the cut height. Each one's footprint is its world plan box.
    - Report `("missing", name, None)` for each such element whose GlobalId is in no cut group.
    - Report `("extra", GlobalId, None)` for each GlobalId in a cut group that is not such an element: an element no longer in the IFC, or a stale drawing.
    - For each cut group, take the box that bounds the footprints of its known elements. Report `("off", names, d)` when any side of the group's box differs from it by d > `tol` metres. `names` joins the elements' names, sorted, with `+`.
    - Return the items sorted by kind, then name. `[]` means every cut element is drawn, nothing else is, and every outline's extent matches.
    - Not caught: a piece moved inside the box of its merged outline. The read-back in `write_walls_ifc` covers each element's own geometry, and each write gives new GlobalIds, so a drawing older than the IFC reports every element as missing and extra.
- No change to `bhelpers.py` or the template. The Sun Position mapping is documentation (D15), verified by T23.

### Docs (development session)

Draft text follows the instruction-writing rules; adjust wording only.

- D13 `reference/extensions.md`, "Write an IFC", replacing the numbered recipe and the rules under it:
  ```
  Write the IFC from the scene script's own wall list, after the correction passes. Never retype the coordinates.

  from ifc_walls import write_walls_ifc
  ids = write_walls_ifc(walls, "out/walls.ifc", 0.0, CEIL, unit=bh.U)

  - Run it in a Blender run that enables the extensions, or through `uvx --with ifcopenshell --with numpy python -I`.
  - Pass the same `walls` list that `walls_from_plan` gets. The IFC names match the scene's box names.
  - Give each record a `kind` of `new` or `existing`. The IFC then carries it as the element's status.
  - For a post or a beam, add a record with its own `z0`, `z1`, and `ifc_class`, such as `IfcColumn`.
  - `write_walls_ifc` reads the file back and raises an error when an element differs from its record by over 3 mm.
  - For other elements, read `scripts/ifc_walls.py` as the recipe.
  ```
- D14 `reference/extensions.md`, "Generate a drawing headless", added after the snippet's bullets:
  ```
  - After you create the drawing, run `check_drawing(svg, ifc)` from `ifc_walls`. It must return `[]`.
  - A `missing` item names an element that the drawing does not show. Check the cut height and the storey.
  - An `extra` item names an outline with no element in the IFC. Generate the drawing again from the current IFC.
  - An `off` item names the walls of one outline whose extent is more than 3 mm off.
  - Bonsai joins touching walls of one class, material, and status into one outline. The check compares each joined outline as a whole.
  - Review the image only for appearance. The check covers the geometry.
  ```
- D15 `reference/extensions.md`, "Sun Position", replacing its bullets:
  ```
  - Use Sun Position to get the sun's angles for the site, date, and time. Then build the sun with `sun()`.

  p = bpy.context.scene.sun_pos_properties
  p.latitude, p.longitude, p.UTC_zone = 37.77, -122.42, -8
  p.use_daylight_savings = True
  p.year, p.month, p.day, p.time = 2026, 6, 21, 15.5
  sun(math.degrees(p.sun_elevation), math.degrees(p.sun_azimuth), plan_north_deg=PLAN_NORTH)

  - The fields are `latitude`, `longitude`, `UTC_zone`, `use_daylight_savings`, `year`, `month`, `day`, `time`, `north_offset`, and `sun_object`.
  - Set `UTC_zone` to the site's standard-time offset.
  - If the date falls in daylight saving time, set `use_daylight_savings`.
  - `sun_elevation` and `sun_azimuth` are in radians. Convert them to degrees for `sun()`.
  - If you let Sun Position turn a sun object instead, set `north_offset` to `-math.radians(PLAN_NORTH)`. It is in radians.
  - Keep one fixed date and time for every render in a project. Record the angles in the dimensions file.
  ```
- D16 `reference/extensions.md`, "Install and enable": the enable command enables all three, and two bullets are added.
  ```
  "$BLENDER" --factory-startup -b --python-exit-code 1 \
    --python-expr "import addon_utils; assert all(addon_utils.enable('bl_ext.blender_org.' + x, default_set=True) for x in ('bonsai', 'sun_position', 'point_cloud_io'))" \
    -P script.py -- args

  - Enable the same three extensions in every run that enables any. Blender re-syncs their shared packages whenever the set changes.
  - Do not run two Blender runs that enable extensions at the same time. A re-sync can remove the other run's packages.
  ```
  The bullet "A per-run enable does not change the saved preferences" stays.
- D17 `reference/extensions.md`: delete the DXF section, and delete its row from the SKILL.md Extensions table (A1, 2026-10-21).
- D18 `reference/extensions.md`, "Point Cloud I/O": replace "Not yet verified: a full import of a project scan" with what T29 finds: where the importer records the offset when `center_on_origin` is on, and whether points at UTM coordinates keep millimetre precision when it is off. Draft only after T29 runs.
- D19 SKILL.md:
  - Frontmatter description, one line, no `: ` inside (534 characters, against 502 now): `Builds architectural and remodel renders in Blender from a Python scene script, run headless with Cycles. Covers project setup, plan input from PDFs or measurements, perspective and cut plan views, option studies, a posable scale figure, render checks, construction sheets, the site sun by date and time, LiDAR scans against the model, and IFC walls and plan drawings for an architect. Use when creating or changing a Blender render, scene script, plan view, study page, construction sheet, or IFC file for a room, house, or remodel.`
  - Scripts table row: `ifc_walls.py | Blender with Bonsai enabled, or uvx with ifcopenshell and numpy | IFC walls from the wall records, read back and checked; a Bonsai plan drawing checked against the IFC`.
  - Extensions table: drop the `CAD2Cube, Export AutoCAD DXF` row. The Reference line becomes "Extensions (Bonsai and IfcOpenShell, Sun Position, Point Cloud I/O)".
- D20 `reference/api.md` lines for `write_walls_ifc`, `drawing_walls`, `check_drawing`; CHANGELOG, README (suite size), skill `docs/ISSUES.md`.

### Tests (test author)

All under the suite's timeouts; no sleeps. Each test below fails before the change unless it says otherwise.

- T21 `tests/bl_extensions.py`, T13b rewritten around R33 (fails before: no `ifc_walls` module). Records in feet, `unit=0.3048`, `z0=0`, `z1=9`: `dict(kind="existing", x0=0, x1=24, y0=0, y1=0.5)`, `dict(kind="new", x0=23.5, x1=24, y0=0.5, y1=14)`, `dict(kind="existing", x0=0.5, x1=0, y0=0.5, y1=14)` (reversed x), `dict(kind="new", x0=0, x1=24, y0=14, y1=14.5)`, the tuple `(10, 10.5, 0.5, 6)`, and `dict(kind="new", x0=12, x1=12.5, y0=6, y1=6.5, ifc_class="IfcColumn", z0=0, z1=8)`.
  - The return has six names `wall_0` to `wall_5`, in order, each with a GlobalId found in the file.
  - Five `IfcWall` and one `IfcColumn`; each element's world box equals its normalised record times 0.3048 within 1e-6 m; all in storey `Level 1`.
  - `Status` is `EXISTING`, `NEW`, `EXISTING`, `NEW`, none, `NEW`; the column's is in `Pset_ColumnCommon`.
  - `tol=-1.0` raises `ValueError` (the read-back path runs).
- T22 Drawing check, in `bl_extensions.py` T13c (fails before: no `check_drawing`; revised after the tests). Generate the plan drawing from T21's IFC as T13c does now.
  - `check_drawing(svg, ifc)` returns `[]`.
  - Grouping, pinned from Bonsai 0.9.0 (it joins by class, material, and status): `drawing_walls(svg)` has one group holding `wall_0` and `wall_2`, one holding `wall_1` and `wall_3`, one holding `wall_4` alone, and one holding `wall_5` (the column) alone. A failure here means Bonsai changed how it joins outlines; read the new SVG before changing the check.
  - Closed room: `write_walls_ifc` into `out/room/room.ifc` (its own folder, so its drawing does not replace T21's) with five records in feet, all `kind="existing"`, `z0=0`, `z1=9`: south `(0, 12, 0, 0.5)`, north `(0, 12, 9.5, 10)`, west `(0, 0.5, 0.5, 9.5)`, east `(11.5, 12, 0.5, 9.5)`, and a partition `(6, 6.5, 0.5, 5)`. Generate its plan drawing. `drawing_walls` has exactly one group, holding all five GlobalIds, with box (0, 12, 0, 10) ft within 1e-4 m; `check_drawing` returns `[]`.
  - Moved: copy T21's IFC, move `wall_1` 0.1 m east by its placement, and save. `check_drawing(svg, copy)` returns exactly `[("off", "wall_1+wall_3", d)]` with d within 1e-3 of 0.1.
  - Missing: copy T21's SVG without `wall_4`'s cut group: the result is `[("missing", "wall_4", None)]`. Copy the room's SVG without its one cut group: the result is five `missing` items, `wall_0` to `wall_4`. The test removes a group whose class or `ifc:guid` holds the GlobalId.
  - Stale: `check_drawing(room_svg, t21_ifc)` returns six `missing` items and five `extra` items.
  - Above the cut: T21's IFC with an added wall at z 2.0 to 2.6 m returns `[]`.
- T23 Sun Position mapping, in `bl_extensions.py` T14. It passes before the doc change, because it tests Blender's behaviour behind D15; flipping the sign of `north_offset` in the test must fail it.
  - At 37.77, -122.42, `UTC_zone` -8, 2026-06-21, for plan north 0, 30, and -75 degrees and times 9.0, 12.0, and 15.5: the light direction of `bh.sun(degrees(sun_elevation), degrees(sun_azimuth), plan_north_deg=N)` is within 0.01 degrees of the Sun Position object's with `north_offset = -radians(N)`.
  - Solar noon: with `north_offset` 0, search 11:00 to 13:30 in one-minute steps for the highest elevation. It falls between 12:09 and 12:15, at 75.67 plus or minus 0.1 degrees, with azimuth 180 plus or minus 1 degree.
  - Daylight time: `time` 15.5 with `use_daylight_savings` on gives the angles of `time` 14.5 with it off, within 1e-9.
- T24 `tests/test_extensions_doc.py` and `bl_extensions.py`, keep-in-step (F15):
  - Extension ids: the ids in the doc's `extension install` line, and the ids in its `addon_utils.enable` command, each equal `EXTENSIONS` as sets. Fails before: the current enable command names only `bonsai`.
  - The doc names no extension id outside `EXTENSIONS` (a `-c extension install` id or a backticked `bl_ext.blender_org.<id>`).
  - API names: `tests/extensions_names.py` gains `API_NAMES`, read with `ast` from the `run("...")` strings in `scripts/ifc_walls.py`. `bl_extensions.py` T13a imports `ifcopenshell.api.<module>` for each and checks the function exists. Fails before: no `ifc_walls.py`.
- T25 `tests/test_ifc_walls.py` (plain Python, `python3 -I`; revised after the tests). `drawing_walls` on hand-written SVG strings in the observed format, with `matrix3` `[[10,0,250],[0,10,250],[0,0,1]]` and `ifc:plane` z 1.6 unless stated. Boxes compare within 1e-6 m.
  - Two separate wall groups (`class="IfcWall <id> cut material-null"`, the T13b paths): cut_z 1.6, and two groups with one id each and the `ew` and `ns` boxes.
  - The same with scale 20 and offset (100, 300) in `matrix3`: the same boxes.
  - A merged group, `class="IfcWall <id_a> material-null <id_b> cut"`, holding the L-shaped path `M251.524,207.328 L250.0,207.328 L250.0,250.0 L323.152,250.0 L323.152,248.476 L251.524,248.476 Z`: one group with ids `(id_a, id_b)` sorted, box (0, 7.3152, 0, 4.2672).
  - A column group, `<g ifc:guid="<id_c>" ifc:name="wall_5" class="IfcColumn material-null cut">`: one group with ids `(id_c,)`.
  - A closed room as one group whose path has an outer ring and a hole (`M... Z M... Z`): the box is the outer ring's.
  - A `projection` group (class without `cut`) is left out.
  - A path with an `A` command raises `ValueError`; a path with a lowercase `l` raises `ValueError`; two drawing groups raise `ValueError`.
  - The module imports with no `ifcopenshell` installed.
- T26 `test_api_doc.py` also checks `ifc_walls`; `run_tests.sh` adds `ifc_walls.py` to the required files and `test_ifc_walls.py` to the suite.
- T27 `tests/test_description.py` (plain Python): SKILL.md's frontmatter has `name:` and a one-line `description:`; the description has no `: `, is at most 1024 characters, and names `IFC`, `LiDAR`, and `sun`. Fails before: no `IFC`.
- T29 Point cloud, in `bl_extensions.py`: write a synthetic LAS with laspy (a 4 by 3 m room at easting 551234, northing 4181234, height 12 m). Import it with `center_on_origin` on and then off. Print and assert the point count; record where the offset is kept and the worst position error against the source. The pass line is set after the first run and goes into D18.
- Mutation checks (report each): place y-running walls at x0 instead of x1; drop the y flip in `drawing_walls`; read the cut height from the wrong matrix cell; read GlobalIds from the class only (column) or only the first id of a class (merged group); compare each element's own box instead of the group's; leave out the `unit.add_si_unit` length unit; put every pset on `Pset_WallCommon`; skip the read-back in `write_walls_ifc`. Each must fail at least one of T21, T22, or T25.

### Evals

Fresh sonnet subagents read `SKILL.md` by absolute path, not through the Skill tool; synthetic data only. Each prompt allows installed extensions per run and forbids installs.
- E3 (F1, F14, F16): a synthetic `build_flat.py` that loads a walls JSON in feet and applies `WALL_FIXES`, `EXTRA_WALLS`, and `cut_openings`. Prompt: "The architect wants an IFC of the walls in this scene and a plan drawing from it. Make both and confirm they match the model." Pass: `write_walls_ifc` gets the corrected list (no wall coordinate typed by the agent), `unit` is `bh.U` or 0.3048, the run enables all three extensions with the assert, `check_drawing` returns `[]`, and nothing is installed.
- E4 (F2, F13): "Light the living room render with the sun at 3:30 pm on 21 June, at 37.77 N, 122.42 W. True north is 20 degrees counter-clockwise from the plan's up." Pass: Sun Position enabled per run; daylight time handled (`use_daylight_savings` on with `UTC_zone` -8, or -7); `sun()` gets degrees with `plan_north_deg=20`, or a sun object gets `north_offset = -radians(20)`; the light direction is within 0.5 degrees of the evaluator's reference from T23's setup; the angles are recorded.
- E5 (F16, after T29): the synthetic LAS of T29 with the east wall 5 cm out, and a scene script of the room. Prompt: "Check the model's walls against this scan. Report any wall more than 2 cm off." Pass: imported with `point_cloud_las`; the centring offset handled as D18 says; the east wall reported at about 5 cm and no other wall.
- E7 (F11), description ranking before install: a fresh subagent gets the names and descriptions of the installed skills, with the D19 description in place of the current one, and seven prompts. For each it names the skill it would load, or none. Positives: "Turn the walls of my remodel scene into an IFC for the architect"; "Make the kitchen render show the sun at 4 pm on the winter solstice at our address"; "Line up my Scaniverse LiDAR scan of the house with the Blender model and list the walls that are off"; "Render the bathroom remodel from the vanity" (regression). Negatives: "Count the trees in this forest LiDAR scan"; "Compute sunrise times for Boston for a calendar app"; "Validate this IFC file against the client's IDS rules". Pass: four of four positives and none of the negatives.
- After install (Releases): the discovery eval uses the IFC prompt of E7, in a fresh subagent that is not told the skill's name or path.

### Contradictions with the current doc

- SKILL.md Extensions table and `reference/extensions.md` DXF: `cad2cube` "imports an architect's DXF with layers, units, and blocks" is true of the extension, but nothing in the skill uses its curves, and it recentres the drawing by default. The exporter writes 3D faces in R12 with no unit, which does not serve "to an architect's CAD files". The former bundled importer, `import_autocad_dxf_format_dxf`, is not mentioned.
- `reference/extensions.md`: "A per-run enable does not change the saved preferences" is true, but every change of the enabled set re-syncs the shared package folder (Verified, wheels). The current per-run command enables Bonsai alone, so a later Sun Position or Point Cloud I/O run removes IfcOpenShell from the folder.
- `reference/extensions.md`: the `north_offset` field is listed with no unit or sign; it is radians, and its sign is the opposite of `plan_north_deg`.
- No contradiction found in the Bonsai drawing steps or the per-run enable with `default_set=True`.

### Answers (2026-10-21, the user)

- A1, A2: no DXF route in v1.0.0. The 2026-10-19 "DXF is enough" decision assumed a DXF extension came with Blender; none does, and no project needs DXF. D17 deletes the DXF section and table row; T28 and E6 are dropped; the DXF findings above stay for later.
- B1: yes, `kind` becomes the wall's NEW or EXISTING status. B2: yes, `scripts/ifc_walls.py`.
- C1: yes, D16. C2: yes; the `bl_extensions` step ran at 01:34 and restored the shared package folder (`ifcopenshell`, `ezdxf`, `laspy` present).
- D1: yes, with "DXF," removed under A1 (534 characters).

### Revision after the tests (2026-10-21)

The test author ran Bonsai 0.9.0 on T21's six records (tests at `7af0c10`) and found three errors in R33. The architect confirmed each against the run's files and Bonsai's source, and revised R33, D14, T22, T25, and the mutation list above.
- Bonsai joins cut outlines. `bonsai/bim/module/drawing/operator.py`, `merge_linework_and_add_metadata`, unions the cut polygons of `IfcWall` and `IfcSlab` elements that share class, material name, and `Pset_*Common.Status`, whenever the union is one polygon. The joined `<g>` lists every GlobalId in its class. In T21's drawing, `wall_0`+`wall_2` (EXISTING) and `wall_1`+`wall_3` (NEW) each became one L-shaped outline; `wall_4` (no status) stayed alone, though it touches `wall_0`. A closed room of one status is one outline with a hole. The per-element box comparison of the first R33 therefore reported correct drawings as wrong.
- Elements outside the join classes keep an `ifc:guid` attribute and carry no GlobalId in the class (the column).
- `unit.assign_unit` with no `units` writes millimetres (unit scale 0.001), not metres; verified again through uvx. `reference/extensions.md` line 50 ("The default units are metres") is wrong for the same reason; D13 already removes that recipe.

Simplify, on the revised check: the comparison is per cut group, by extent. Rejected: comparing each outline's polygon with the union of its walls' footprints (symmetric difference by coordinate compression, about 50 lines). It catches only a piece moved inside its own outline's box, which needs a hand edit of the IFC after the drawing: `write_walls_ifc` checks each element on write, and every write gives new GlobalIds, so a stale drawing already shows as `missing` and `extra`. Kept: `missing`, `extra`, and the per-group extent, which catch a wrong cut height or storey, a stale drawing, and a scale, origin, or flip error.

Verified with a prototype of the revised functions (uvx, outside the repo) on the test run's files: T21's IFC and drawing give `[]`; the IFC with `wall_1` moved 0.1 m gives `[("off", "wall_1+wall_3", 0.09999950)]`; the drawing without `wall_4`'s group gives `[("missing", "wall_4", None)]`; the IFC with an element above the cut gives `[]`; T21's drawing against T13b's two-wall IFC gives two `missing` and six `extra` items. The closed room case has not been run; T22 runs it.

### Order of work, and how to continue if interrupted

C2 first, if approved. Then T21 to T27 and T29 by the test author, on branch `rev5b` (they fail as stated). Then R33. Then D13 to D20, with D18 written from T29's output. Then the suite, the mutation checks, and E3 to E7. Then the pre-merge review, merge, and the v1.0.0 release with the discovery eval after install. Each finished item is ticked in skill `docs/ISSUES.md` under the Revision 5 line; a fresh session reads that line, this section, and `git log` on the branch.

## Revision 6 (2026-10-20, phantom geometry defects; requested by render project B, approved by the user)

Source: `../inputs/2026-10-20-phantom-defects.md`. Decision: skill `docs/ISSUES.md`, Decisions, 2026-10-20. Investigated against this repo at `6cf8009` and Blender 5.2.0 LTS, and against render project B's build script and README (read-only, the two files the user named).

Revised 2026-10-20 against `a5e5158`, after an architecture review (findings G1 to G13, "Review findings" below); the opening probe in R25 is the user's decision on G2.

One gate, `run_checks()`, runs six checks over the whole scene right before every render, previews included: the existing `coplanar_check` and five new checks (flipped faces, wall gaps with openings, floor fit, camera rays, clearance). Every check reads the render-visible objects of the view layer (R32) as evaluated geometry (modifiers and booleans applied). Lengths inside the checks are world metres, so a script that builds its own scene in feet gets the same results; only `paths` takes project units. Every hit names the objects involved.

### Verified (2026-10-20, headless Blender 5.2.0 LTS, scratch scripts outside the repo)

- `BVHTree.ray_cast(origin, direction, distance)` returns `(location, normal, index, distance)`, or four `None` on a miss or past `distance`. The normal follows the polygon's winding, not the ray: a ray going up through a +Z quad returns normal +Z. `normal.dot(direction) > 0` therefore marks a face hit from behind.
- `BVHTree.overlap()` returns no pairs for boxes that only touch, for overlapping boxes whose faces share planes, and for a box fully inside another. It does return pairs for a walking box shrunk by 5 mm and crossed by a slab, and for a 15 mm guard panel inside that box. Containment needs a separate vertex test.
- `Scene.ray_cast()` hits objects with `hide_render` set (such as `cut_holes` cutters) and objects with `visible_camera` off. The checks therefore build their own BVH from the objects that render.
- `camera.data.view_frame(scene=scene)` returns the frame corners in camera space in the order top-right, bottom-right, bottom-left, top-left, with the render aspect and lens shift applied. A ray through grid cell (i, j) of a cols x rows grid lands on pixel ((i + 0.5) / cols * res_x, (j + 0.5) / rows * res_y), y down: `project_points` of the hit agrees to 0.0000 px, in metres and in feet, with shift_x 0.05 and aspect 0.75.
- Signed volume in local coordinates: `box()` gives +6.0 for 1 x 2 x 3; a clockwise `prism` is positive (it recalculates normals); `sphere` and `cyl` are positive; `lathe` is positive or negative with the profile's direction, and positive after `bmesh.ops.recalc_face_normals`. A box with scale (-1, 1, 1) stays positive in local coordinates.
- Existing bug: `coplanar_check` reports a box with scale (-1, 1, 1) resting on a floor, because world-space winding turns its bottom normal up. Without the mirrored box the same scene passes. Fixed by R23.
- `sys.exit(1)` inside a `-P` script stops the script and makes Blender exit 1, with or without `--python-exit-code 1`. A project run command without the flag still stops before the render.
- The template scene passes coplanar over the whole scene (walls included), flipped, wall gaps, and floor fit, in both views. The template's comment "walls butt at the corners by design" on its scoped coplanar call is stale.
- The template's perspective view sees through the door into the empty world below the horizon (427 of 16,000 rays). A rule that fails every escape below the horizon would fail the template, and any finite ground plane near the horizon.
- A mannequin in the template gives 20 coplanar pairs between its own joint ellipsoids in the perspective view, and none once the figure is left out. Its parts pass the flipped check.
- A 4 cm slot between two 10 cm ceiling pieces, seen at 17 to 30 degrees, lets no ray escape: the slot's sides block every ray, and the render shows a dark line. A 0.6 m hole lets 890 of 16,000 rays escape.
- Cost on a synthetic scene of 1,925 objects and 74,216 polygons (walls, ceilings, a floor with boolean holes, 1,300 boxes, cylinders, spheres, 240 tiles, a mannequin), CPU, prototype code: scan and BVH 0.11 s; flipped 0.12 s; wall gaps and floor fit under 0.01 s each; camera rays 0.03 s at 160 columns and 0.10 s at 320; clearance with 6 paths under 0.01 s; coplanar over the whole scene 1.64 s. About 2.5 s per render in all. Coplanar grows with the polygons of touching pairs; render project B's scene was not measured.

Review round (2026-10-20, same Blender; reviewer's results marked as such):
- Reviewer: an uncaught exception in a `-P` script run without `--python-exit-code 1` exits 0. `sys.exit(1)` exits 1 with or without the flag.
- Reviewer, confirmed again: `bpy.context.evaluated_depsgraph_get()` alone refreshes a moved object's `matrix_world` (0.0 became 0.5). A test of a stale position therefore cannot tell whether `run_checks` calls `view_layer.update()`.
- The revised `wall_gaps` (R22), prototyped in plain Python, gives the expected result for every T16 case, including the reviewer's four correct junctions (T filled by its own square, a stem through a split wall, an X crossing, an L with a corner square), a jog closed by a column, and a stem on the level above that must not fill a gap below it.
- R26 as first written reports every object on a mirrored floor, an inside-out floor, or a slab built from an x-z profile in the point order the reviewer found in project B (world signed volume -50 on a 10 x 10 x 0.5 slab) as sunk more than 0.30 m. With the floor's polygon order reversed when its world signed volume is negative, all three give only the one floating box.
- Support test (R26): a chair on a 30 mm rug, a vase on a plinth, a nosing set 10 mm into its tread, and a mattress on a bed frame pass. A panel 0.11 m above the floor and an LED strip in a riser are still reported. One BVH over the whole scene does not work for this test: a ray that steps past the object's own bottom face also steps past a support face on the same plane (the mattress was reported).
- Opening probe (R25), two wall boxes 0.9 m apart under a ceiling: with no header the up ray first hits the ceiling at the wall top (`no-header`); with a header box, named with the wall prefix or not, it hits at 2.10 m. With the floor split across the opening, the down ray misses (`no-floor`); with a slab one storey down named in `floors`, it hits 3 m below (`no-floor`). Walls that run down through the slab still pass.
- A camera inside a closed box sees its faces from behind on all 16,000 rays, so the camera check also catches a camera inside an object.
- Open box at 160 columns: 512 backface rays; a box `(-0.3, 0.3, -1.6, -1.4, 1.9, 2.1)` between the camera and the opening cuts them to 34; with `visible_camera` off it gives 512 again.
- `scene.objects` lists objects in a collection excluded from the view layer and objects hidden by their collection's render switch. `view_layer.objects` leaves out the excluded collection and other scenes, but still lists an object hidden by its collection's render switch. `depsgraph.object_instances` leaves out both.

### Simplify before building (architect, 2026-10-20)

Each part traces to a defect in the request or to the 2026-10-20 decision. Deleted, with the reason:
- A stair helper in `bhelpers`: none exists, and the clearance check needs only boxes. Paths are plain tuples, the same for the template and a project script.
- Sloped walking volumes along a flight: one box per tread gives the same vertical headroom over each tread.
- A command line for `wall_gaps.py`: nobody asked for one. The function runs on `load_plan` output in Blender or plain Python.
- One shared geometry scan for all checks: a scan costs 0.11 s at 74,000 polygons, so each check scans on its own.
- `clash_check` inside `run_checks`: it counts touching as a clash, so over the whole scene every wall on a floor would fail. It stays a separate call for the figure.
- Camera rays in plan views: the plan clip starts rays inside cut walls, so every wall would show a face from behind.
- Escape rays below the horizon in exterior views: they fail at the edge of any finite ground plane (verified on the template's door).
- Grouping escape rays into connected holes: one line per kind and object, with the pixel box of its rays, points to the place in the preview.
- After the review: the x0 sweep in `wall_gaps` (G8). Every pair is cheap in plain Python (200 walls make 19,900 pairs), and the sweep compared metres with rect units.
- After the review: camera backfaces only on open meshes (G5, optional part). Rejected: a camera inside a closed object is seen only through backfaces on closed meshes (verified), and an inside-out mesh named twice, by `flipped` and `camera`, costs one extra line.
- After the review: iterating `depsgraph.object_instances` (G11). Neither the template nor project B uses instances, and instance hits share one object name. The checks read `view_layer.objects` instead, and R32 and D5 state the limit.
- After the review: a support test over one scene BVH. It misses a support face on the plane of the object's bottom (verified), so R26 casts against each candidate support on its own.
- After the review: T18 as its own suite step. Its timing case moves into `bl_rev6.py`.

Flags on the approved shape: "every check over the whole scene" leaves out `clash_check` and leaves the figure out of coplanar, floor fit, and clearance; "each view's camera" is the scene camera of the run, since a run renders one view; exemptions are exact names, but walls and the figure are selected by prefix, as `clash_check`, `coplanar_check`, and `plan_cut` already select (question A1).

### Code (implementer)

Keep out: the implementer does not edit `tests/`; the test author does not edit `scripts/` or `templates/`.

- R32 Render-visible objects, shared by R23 to R29: the objects in `bpy.context.view_layer.objects` of the check's types (mesh, or mesh and curve), with `hide_render` off. Each check leaves out an object whose evaluated mesh has no polygons, such as a boolean that removed everything (G3). Not seen: instances (collection instances, geometry-nodes and particle instances). Still checked: an object hidden from render only by its collection's render switch. `clash_check` keeps its own selection.
- R22 `scripts/wall_gaps.py` (new, plain Python, imports only `math`; it holds its own copy of the rectangle subtraction in `bhelpers.subtract`, because plain Python cannot import `bhelpers`). Two functions share the input rules:
  - `rects` items are tuples `(x0, x1, y0, y1)` or `(x0, x1, y0, y1, z0, z1, ...)` (items past the sixth ignored), or dicts with keys `x0`, `x1`, `y0`, `y1` and optional `z0`, `z1` (`load_plan` walls). Each is normalised so lows come first. `unit` is metres per rect unit and applies to all six values; `gap`, `opening`, and `touch` are metres. Two rects are on one level when either has no z range or their z ranges overlap by more than `touch`. Only pairs on one level are compared, and only rects on the level of both count as filling. A rect runs along x when its x length is at least its y length; its thickness is its shorter side. Every pair is compared; there is no sweep.
  - `wall_gaps(rects, unit=1.0, gap=0.3, touch=0.001)`. For each pair, ox and oy are the overlap lengths (negative when apart) and d = hypot(max(0, -ox), max(0, -oy)).
    - Gap, when touch < d <= gap. The region between them is, in each axis, the overlap interval when they overlap there, and the interval between them otherwise. Report `(i, j, "gap", d)` when the region is `touch` or thinner in either axis (walls that line up corner to corner), or when the area of the region left after subtracting every rect is at least touch².
    - Corner, when d <= touch and not both of ox and oy exceed `touch` (an overlap is fine). The contact length c is the larger of ox and oy; a pair is a candidate when c < min(thickness_i, thickness_j) - touch. The junction region is the square where the two cross when one runs along x and the other along y. When both run the same way, it is the box across both rects' extents, reaching half the thinner thickness to each side of the line where they touch. Report `(i, j, "corner", c)` when the area of the junction region left after subtracting every rect is at least touch². That catches walls meeting only at a corner point, a partial butt that leaves a notch, and a false jog, but not a junction that a third piece fills (G1).
    - Return the hits sorted by (i, j), with i < j indexing the input list and lengths in metres.
  - `wall_openings(rects, unit=1.0, gap=0.3, opening=2.5, touch=0.001)`: the door-sized openings between in-line walls. A pair qualifies when both run the same way, their thickness bands overlap by more than half the thinner thickness, and their separation w along the run is above `gap` and at most `opening`. The opening box spans w along the run and the overlap of the bands across it. Leave out a pair when any other rect on the level of both overlaps the box by more than `touch` in both axes (a crossing wall, or a header named as a wall). Return `[(i, j, w, (x0, x1, y0, y1))]`, the box in metres, sorted by (i, j).
- R23 `coplanar_check(prefixes=None, tol=0.0005, min_area=1e-6, skip=())`: `skip` holds exact object names to leave out. Objects come from R32. Fix: `_tris` negates each normal of an object whose `matrix_world` has a negative determinant, so a mirrored object's faces keep their real facing. Otherwise unchanged.
- R24 `flipped_check(skip=())`: for each R32 mesh object not in `skip`, take the evaluated mesh in local coordinates. Skip it unless every undirected edge is used by exactly two polygon sides (closed). Report `(name, "mixed")` when any directed edge appears twice (some faces turned against their neighbours); otherwise report `(name, "inside-out")` when the signed volume is below -1e-12. Sorted by name.
- R25 `wall_gap_check(prefixes=("wall_",), floors=(), gap=0.3, opening=2.5, touch=0.001, tol=0.025, skip=(), full_height=())`:
  - Walls are R32 mesh objects named with `prefixes`, not in `skip`. A wall's footprint and z range are the world box of its evaluated vertices. Leave out a wall when any world polygon normal is more than 1e-4 off a world axis (angled `seg` walls, bevelled walls), and print one line `NOTE wall_gaps: not axis-aligned, not checked: <names>`.
  - Run `wall_gaps` and `wall_openings` on `(x0, x1, y0, y1, z0, z1)` per wall with `unit=1.0`. Gap and corner hits come from `wall_gaps`.
  - Opening probe (G2, the user's decision), for each opening whose two names are not a pair in `full_height` (either order): start at the opening box's centre, at z = the higher of the two wall bottoms + 1.0 m. Leave the opening out when that point is within `tol` of the lower wall top.
  - Up ray, against a BVH of every R32 mesh and curve object: report `no-header` when it hits nothing, or its first hit is at or above the lower wall top minus `tol` (a ceiling or slab resting on the walls).
  - Down ray, only when `floors` is given, against a BVH of those floors: report `no-floor` when it hits nothing, or its first hit is more than `tol` below the lower wall bottom.
  - Return `[(name_i, name_j, kind, length_m)]` with kind `gap`, `corner`, `no-header`, or `no-floor`; the length is d, c, or the opening width w. Each pair's names are in name order; the list is sorted.
- R26 `floor_fit_check(floors, walls=("wall_",), tol=0.025, hang=0.3, skip=())`:
  - `floors` are exact names. Build one BVH from the floors' world polygons. Reverse a floor's polygon order when it is closed and its signed volume in world coordinates is negative (inside out or mirrored, but not both), or when it is open and its `matrix_world` has a negative determinant (G5). "Faces up" then means the side that renders as the top.
  - For each other R32 mesh object not in `skip`, take its world box (lo, hi) and cast a ray straight down from (centre x, centre y, lo.z + hang) against the floor BVH. On a miss, the object is not over a floor: skip it.
  - When the first hit faces down, the probe started inside a floor: report `(name, None)` (sunk more than `hang`).
  - When it faces up, d = lo.z - hit z. Report `(name, d)` when d < -tol (sunk). When d >= hang the object is hung (lights, upper cabinets, headers) and passes.
  - When tol < d < hang, run the support test (G6). Cast a ray down from (centre x, centre y, lo.z + tol), for at most 2 tol, against each other R32 mesh object whose world box covers that plan point and reaches within `tol` of lo.z. Give each candidate its own BVH, oriented as the floors are. When a ray hits a face that faces up, the object rests on that object and passes. Otherwise report `(name, d)` (floating).
  - Objects named with `walls` prefixes are reported only when floating: walls may run down through a slab. Sorted by name.
- R27 `camera_check(interior=None, rays=160, skip=())`: uses `scene.camera`; returns `[]` when there is no camera or it is not perspective. Builds a BVH from R32 mesh and curve objects with `visible_camera` on, not in `skip`, with each polygon's vertex order reversed when the object's `matrix_world` has a negative determinant. Closed meshes stay in, so a camera inside an object shows as a backface on it. Grid: `rays` columns, rows = max(1, round(rays * res_y / res_x)), one ray per cell centre through the `view_frame(scene=scene)` plane, from the camera at `clip_start` for at most `clip_end - clip_start`. A hit with `normal.dot(direction) > 0` is a `backface` on the hit object. A miss is an `escape` when the view is interior. `interior=None` means auto: interior when a ray straight up from the camera hits anything within `clip_end`; when auto finds an exterior view, print `NOTE camera: exterior view, escapes not checked`. `interior=False` never checks escapes; `interior=True` always does. Return `[(kind, name, count, (x0, y0, x1, y1))]`: one item per kind and object (name `None` for escapes), with the pixel box of the ray centres, rounded to whole pixels, y down. Sorted by (kind, name or "").
- R28 `clearance_check(paths, headroom=2.032, unit=None, tol=0.005, skip=())`: `paths` maps a name to `(x0, x1, y0, y1, z)` in project units, z being the walking surface (tread top); `unit` None means `bhelpers.U` (import inside the function). Each walking box in metres is [x0 + tol, x1 - tol] x [y0 + tol, y1 - tol] x [z + tol, z + headroom]. An object (R32 mesh or curve, not in `skip`) is a hit when its world polygons cross the box (BVH overlap) or any of its world vertices lies strictly inside the box. Headroom: cast a 3 x 3 grid of rays straight up from the box bottom, at cell centres; for a hit object, headroom = the lowest hit on it minus z (metres), or `None` when no grid ray hits it. Return `[(path, name, headroom_m or None)]` sorted by (path, name). 2.032 m is 6'-8".
- R29 `run_checks(floors=(), walls=("wall_",), paths=None, figure=("man_",), exempt=None, interior=None, unit=None, rays=160)`:
  - Call `bpy.context.view_layer.update()` first. It is kept for clarity: `evaluated_depsgraph_get()` also refreshes world matrices, so no test can tell the line is there (G9).
  - `exempt` maps a check name (`coplanar`, `flipped`, `wall_gaps`, `floor_fit`, `camera`, `clearance`) to exact object names, and the key `openings` to pairs of wall names, as a `no-header` or `no-floor` hit line prints them. Raise `ValueError` for an unknown key, before any check runs. For each exempt name that no object has, print `WARN exempt <key>: no object named <name>`; for each name in `floors` that no object has, print `WARN floors: no object named <name>`.
  - Objects named with `figure` prefixes are added to `skip` for coplanar, floor fit, and clearance.
  - Run in this order, each with its `exempt` names as `skip`: coplanar, flipped, wall_gaps (`walls` as its prefixes, `floors`, and the `openings` pairs as `full_height`; G4), floor_fit (`floors`, `walls`), camera (`interior`, `rays`), clearance (`paths`, `unit`). Run every check even after a failure.
  - Run each check inside `try`/`except Exception` (G3). An exception prints `FAIL <check>: error <type>: <message>` and counts as a failed check, so the run still reaches `sys.exit(1)`.
  - Print per check: `OK <check> (<t> s)`, or `FAIL <check>: <n> (<t> s)` followed by one indented line per hit (at most 20, then `  ... and <k> more`), or `SKIP <check>: <reason>`. `<t>` has two decimals. Skips: floor_fit `no floors given` or `none of the floors exists`; camera `no scene camera` or `orthographic camera`; clearance `no paths given`.
  - Hit lines: coplanar `  <a> <b>`; flipped `  <name> inside-out` or `  <name> mixed`; wall_gaps `  <a> <b> gap|corner|no-header|no-floor <length:.3f> m`; floor_fit `  <name> floating <d:.3f> m`, `  <name> sunk <-d:.3f> m`, or `  <name> sunk more than <hang:.3f> m`; camera `  backface <name>: <n> rays at px <x0>-<x1>, <y0>-<y1>` or `  escape: <n> rays at px <x0>-<x1>, <y0>-<y1>`; clearance `  <path> <name> headroom <h:.3f> m` or `  <path> <name> inside`.
  - Last line: `OK run_checks`, or `FAIL run_checks: <failed checks, comma-separated>` and then `sys.exit(1)`. Returns None.
- R30 `bhelpers.EYE_HEIGHT = 1.5875` (metres; the eye of a 5'-7" viewer, 5'-2 1/2"). `lathe` calls `bmesh.ops.recalc_face_normals` on its faces before writing the mesh, as `prism` and `slab` do, so a lathe built from either profile direction passes `flipped_check` (question A2).
- R31 Template: import `run_checks`; drop the scoped `coplanar_check` call and its stale comment; keep the `clash_check` call where it is; after `add_camera`, call `run_checks(floors=("floor",), interior=VIEWS[args.view].get("interior"))`, then render. The perspective entry's eye height becomes `bh.EYE_HEIGHT / bh.U`. Both views must print `OK run_checks`.

Tolerances, false positives, and exemptions:

| Check | Defaults | Known false positives | Remedy |
|---|---|---|---|
| coplanar | tol 0.5 mm, min_area 1e-6 m2 | Curved meshes with tangent faces; overlapping slab pieces whose shared top is hidden | Figure left out by prefix; exempt by name or fix the overlap |
| flipped | volume below -1e-12 | A closed mesh made inside out on purpose (none known) | Exempt by name |
| wall_gaps | gap 0.30 m, opening 0.30 to 2.5 m, touch 1 mm, tol 25 mm | A chase between two parallel walls; an opening narrower than 0.30 m; an opening meant to run to the ceiling, and an open-plan passage between in-line wall ends (`no-header`); a threshold piece over a floor gap (`no-floor`, floors only) | Exempt one of the two walls by name; exempt an opening by its pair under `openings` |
| floor_fit | tol 25 mm, hang 0.30 m | Plinth-raised fronts (toe kick about 0.10 m) with nothing under their centre; a floating bed; door undercuts over 25 mm; stair parts within 0.30 m of the floor below with nothing under their centre (project B: a guard 0.186 m, stringer shoes 0.094 and 0.280 m, riser LEDs 0.146 and 0.070 m, a nosing 0.088 m, by the reviewer's figures); an object whose centre misses its support (an L-shaped piece) | Exempt by name. An object that rests on another object (a rug, a plinth, a tread, a bed frame) under its centre passes |
| camera | 160 columns; interior auto | Single-sheet meshes seen from behind (backdrops, leaves, open `lathe` profiles); a view through an opening without glass | Exempt by name; `interior=False` in that view's entry |
| clearance | headroom 2.032 m, tol 5 mm | Handrails inside a box drawn wider than the clear width | Draw the box between the handrails |

Defects in the request, and what catches each:

| Defect | Caught by | Not caught |
|---|---|---|
| 1. Missing wall pieces at junctions | `wall_gaps` (gap, corner), unless another wall piece fills the junction; `camera` escape when the gap opens to sky in an interior view | Walls outside the `walls` prefixes; angled walls; gaps wider than 0.30 m (a gap of 0.30 to 2.5 m between in-line walls is probed as an opening) |
| 2. Opening interiors | `wall_gaps` `no-header` for a missing header between two in-line wall pieces, whatever the header's name; `no-floor` for a floor that does not run through the opening; `camera` backface for a face missing from inside one mesh, in view | A missing jamb or lining built as a separate closed box: the wall end shows instead, with no hole. An opening in one wall mesh (`cut_holes`), whose head is part of the wall. A closed door leaf at the opening's centre line, which the probes hit first. Walls that run above the ceiling, where the ceiling stops the up ray below the wall top. The dark full-depth sill (geometry was present; a material reads as a hole): QA item, D8. A thin slot seen at an angle shows a dark line and lets no ray escape |
| 3. Slab side coplanar with a wall face | `coplanar` over the whole scene | Nothing |
| 4. Objects left at the old floor level | `floor_fit` (project B's offsets were 0.11 m and 0.22 m) | Offsets of 0.30 m or more; objects over no named floor; an object at the old level that rests on another object at the old level (the object under it is reported). The prefix skip that caught an unrelated object: rule, D6 |
| 5. Stale `matrix_world` | `run_checks` updates the view layer itself | The script's own reads: rule, D6 |
| 6. Stray guard across a stair | `clearance` `inside` | Paths nobody declared |
| 7. Emissive strips proud of the risers | None | Rule and QA item, D6 and D8 (decision) |
| 8. Headroom 6'-3 5/8" against 6'-8" | `clearance` with the measured headroom | Paths nobody declared |

Wiring in a project script that builds its own scene (sent by skill-developer to the project after the release):

```python
# run command: Blender --factory-startup -b --python-exit-code 1 -P build.py -- ...
sys.path.insert(0, os.path.join(HERE, "lib"))       # copies of the skill's scripts/*.py
from checks import run_checks

FLOORS = ["floor", ...]          # exact names of every floor, slab, deck, and paving object
WALLS = ("wall_", "party_wall_") # every prefix the script gives wall pieces
PATHS = {}                       # name -> (x0, x1, y0, y1, z), feet; the stair builder adds one per tread and landing
EXEMPT = {}                      # check -> exact object names; "openings" -> (wall, wall) pairs; each with a dated reason

# in the stair builder, for tread i (box from its nosing to the next nosing, between the guards):
PATHS[f"flight1_{i}"] = (x0, x1, y_nosing, y_next_nosing, tread_top)

# the last call before bpy.ops.render.render(write_still=True):
run_checks(floors=FLOORS, walls=WALLS, paths=PATHS, unit=0.3048, figure=("person_",), exempt=EXEMPT,
           interior=VIEWS.get(view, {}).get("interior"))
```

The project's run command gains `--python-exit-code 1`. Without it, an exception outside `run_checks` (the import, or the script's own code) exits 0, skips the render, and leaves the old image in place (G3).

Expect a backlog on the first run in an existing scene: overlapping stair treads, slab pieces, and overlapped wall corners give coplanar hits; plinth fronts and stair parts (guards, stringer shoes, riser LEDs) give floor-fit hits; open-plan passages between wall ends give `no-header` hits. Fix each hit or exempt it by name with a reason.

### Docs (development session)

Draft text below follows the instruction-writing rules; adjust wording only.

- D5 SKILL.md Checks section, replacing the current one:
  ```
  The scene script calls `run_checks` after it sets the camera and before it renders. It runs six checks over the whole scene, prints `OK`, `FAIL`, or `SKIP` for each, and exits 1 on any hit.

  from checks import clash_check, fail_on, run_checks
  fail_on(clash_check(("man_",), ("vanity_", "basin", "tub_")), "clash")
  run_checks(floors=("floor",), paths=STAIR_PATHS, interior=VIEWS[args.view].get("interior"))

  | Check | Finds |
  | coplanar | Same-facing faces on one plane: z-fighting, black strips, a slab side on a wall face |
  | flipped | Closed meshes that are inside out, or have faces turned the wrong way |
  | wall_gaps | Walls that almost meet or meet only at a corner; door-sized openings with no header, or with no floor through them |
  | floor_fit | Objects that float above or sink into the floor under them |
  | camera | Faces seen from behind (a missing face, or a camera inside an object), and sky seen from an interior view |
  | clearance | Anything inside the walking box over a stair tread or path, with the headroom |

  - Run the checks before every render, previews included.
  - Keep `--python-exit-code 1` in every run command. Without it, an error outside the checks exits 0 and leaves the old image in place.
  - Fix every hit.
  - If a hit is intended, exempt the object by its exact name: `exempt={"floor_fit": ["vanity_front"]}`.
  - If an opening is meant to run to the ceiling, exempt it by its two wall names: `exempt={"openings": [("wall_hall_w", "wall_hall_e")]}`.
  - Give the reason for each exemption in a comment.
  - Name every floor, slab, deck, and paving object in `floors`. Without floors, `floor_fit` does not run, and openings are not checked for a floor.
  - Name every wall with the `wall_` prefix, or pass your wall prefixes in `walls`.
  - Add a walking box to `paths` for each stair tread and landing: `(x0, x1, y0, y1, z)`, with z at the tread top.
  - Draw each tread's box between the handrails, from its nosing to the next nosing.
  - If a view looks out through an opening without glass, set `interior=False` in its entry.
  - A camera hit gives a pixel box in the view's image at the run's `--res`. A failing run writes no image.
  - To see a camera hit, exempt its object for one preview run at the same `--res`. Then look inside the pixel box.
  - The checks do not see instances (collection, geometry-nodes, or particle instances). Check those in the preview.
  - Run `clash_check` for the figure. `run_checks` leaves the figure out of most checks.
  - `clash_check` counts surfaces that touch as a hit. Keep furniture 1 mm off the wall behind it, or leave walls out of the second prefix list.
  - In a project script that builds its own scene, copy `scripts/*.py` into its `lib/`.
  - Then call `run_checks` right before the render call, with `unit` set to metres per project unit.
  ```
- D6 SKILL.md Rules for every scene, added:
  ```
  - Before you read `matrix_world` or any world position, call `bpy.context.view_layer.update()`. Until then, positions are stale.
  - In `exempt`, and in any list of objects that a script moves or skips, use exact object names. A prefix there also catches unrelated objects.
  - Exempt only objects with stable names. A name built from a list index, such as `wall_27`, can point at another object after the plan changes.
  - Set an emissive strip into its recess, so that only its front face shows.
  - After a floor or wall level changes, look at every threshold and wall base in a preview.
  - Place an eye-level camera at the floor height plus `EYE_HEIGHT / U`. That is a 5'-7" viewer's eye, 5'-2 1/2".
  ```
- D7 SKILL.md loop: step 2 becomes `Preview at --res 800 --samples 48 --gpu into scratch/; the checks run first`; step 3 becomes `Fix every check hit, then read the preview image`.
- D8 SKILL.md QA list, added: `An emissive strip whose top or sides show, or that streaks nearby glass`; `A dark sill or track across the full wall depth, which reads as a hole` (question A3).
- D9 SKILL.md Scripts table: the `checks.py` row lists `run_checks` and the six checks; a new row `wall_gaps.py | Blender or plain Python | Wall rectangles that almost meet, and door-sized openings between in-line walls, from a list such as load_plan's`.
- D10 `reference/api.md`: lines for `wall_gaps`, `wall_openings`, `flipped_check`, `wall_gap_check`, `floor_fit_check`, `camera_check`, `clearance_check`, `run_checks`, `EYE_HEIGHT`, and the new `coplanar_check` signature, from the code. VIEWS entries: perspective entries may carry `interior` (read by the scene script and passed to `run_checks`; `add_camera` ignores it).
- D11 `reference/plan-input.md`, two lines: `After you apply the correction layer, run wall_gaps(walls, unit=<metres per unit>) on the corrected list.` and `Fix each hit before you build the walls.`
- D12 CHANGELOG, README (suite size), skill `docs/ISSUES.md`.

### Tests (test author)

All under the suite's timeouts; no sleeps. Lengths in metres unless stated; compare floats within 1e-6 unless stated.

- T16 `tests/test_wall_gaps.py` (plain Python, `python3 -I`, imports `wall_gaps` from `SCRIPTS_DIR` or `../scripts`). Each case is `wall_gaps(rects)` with defaults unless stated:
  - `[(0, 4, 0, 0.1), (3.9, 4.0, 0.15, 3)]` gives `[(0, 1, "gap", 0.05)]`; with the second rect at y0 0.1 (T joint) gives `[]`; at y0 0 (overlap) gives `[]`.
  - `[(0, 3.9, 0, 0.1), (3.9, 4.0, 0.1, 3)]` (corner point) gives `[(0, 1, "corner", 0.0)]`; second rect at y0 0.05 gives `[(0, 1, "corner", 0.05)]`.
  - Jog `[(0, 2, 0, 0.1), (2, 4, 0.05, 0.15)]` gives `[(0, 1, "corner", 0.05)]`; aligned thickness change `[(0, 2, 0, 0.1), (2, 4, 0, 0.15)]` gives `[]`.
  - Door `[(0, 2, 0, 0.1), (2.9, 4, 0, 0.1)]` gives `[]`; `(2.3, 4, 0, 0.1)` gives one gap of 0.3 (within 1e-9); `(2.31, 4, 0, 0.1)` gives `[]`.
  - Diagonal `[(0, 2, 0, 0.1), (2.1, 2.2, 0.2, 3)]` gives `[(0, 1, "gap", hypot(0.1, 0.1))]`.
  - Touch tolerance: `(2.0005, 4, 0, 0.1)` after `(0, 2, 0, 0.1)` gives `[]`; `(2.002, 4, 0, 0.1)` gives one gap of 0.002.
  - Feet dicts `[dict(x0=0, x1=13, y0=0, y1=0.33), dict(x0=12.67, x1=13, y0=0.5, y1=10)]` with `unit=0.3048` give `[(0, 1, "gap", 0.17 * 0.3048)]`.
  - Out of order: `[(6, 4.1, 0, 0.1, 0, 2.6), (0, 2, 0, 0.1), (2, 4, 0, 0.1), (-0.2, -0.1, 0, 3)]` gives exactly `[(0, 2, "gap", 0.1), (1, 3, "gap", 0.1)]`. Indices refer to the input order; the six-item tuple with x0 > x1 is accepted.
  - Filled junctions (G1), each `[]`: T with its own square `[(0, 2, 0, 0.1), (2, 2.1, 0, 0.1), (2.1, 4, 0, 0.1), (2, 2.1, 0.1, 3)]`; stem through a split wall `[(0, 2, 0, 0.1), (2.1, 4, 0, 0.1), (2, 2.1, 0, 3)]`; X crossing `[(0, 4, 1, 1.1), (2, 2.1, 0, 1), (2, 2.1, 1.1, 3)]`; L with a corner square `[(0, 3.9, 0, 0.1), (3.9, 4, 0, 0.1), (3.9, 4, 0.1, 3)]`; jog closed by a column `[(0, 2, 0, 0.1), (2, 4, 0.05, 0.15), (1.9, 2.1, -0.05, 0.2)]`.
  - Corner to corner `[(0, 2, 0, 0.1), (2.1, 4, 0.1, 0.2)]` gives `[(0, 1, "gap", 0.1)]`.
  - Levels: `[(0, 4, 0, 0.1, 0, 2.6), (3.9, 4.0, 0.15, 3, 3, 5.6)]` gives `[]`. A stem on the level above does not fill a gap below: `[(0, 2, 0, 0.1, 0, 2.6), (2.1, 4, 0, 0.1, 0, 2.6), (2, 2.1, 0, 3, 3, 5.6)]` gives `[(0, 1, "gap", 0.1)]`.
  - `wall_openings`: `[(0, 2, 0, 0.1), (2.9, 4, 0, 0.1)]` gives `[(0, 1, 0.9, (2.0, 2.9, 0.0, 0.1))]`; the same along y, `[(0, 0.1, 0, 2), (0, 0.1, 2.9, 4)]`, gives `[(0, 1, 0.9, (0.0, 0.1, 2.0, 2.9))]`. Each of these gives `[]`: a crossing wall `(2.2, 2.3, -3, 3)` added; the second wall's band moved to y 0.06 to 0.16 (overlap 0.04, under half the thickness); a separation of 0.2 (a gap, not an opening); a separation of 3.0; the second wall on the level above (z 3 to 5.6 against 0 to 2.6). Feet: `[(0, 6, 0, 0.33), (9, 12, 0, 0.33)]` with `unit=0.3048` gives one opening of 3 * 0.3048.
- T17 `tests/bl_rev6.py` (Blender):
  - `wall_gap_check`: boxes `wall_a (0, 4, 0, 0.1, 0, 2.6)` and `wall_b (3.9, 4.0, 0.15, 3, 0, 2.6)` give `[("wall_a", "wall_b", "gap", 0.05)]`; the same in feet (coordinates divided by 0.3048 after `set_units("ft")`) gives 0.05 m. `wall_b` at z 3 to 5.6 gives `[]`; renamed `shelf_b` gives `[]`; `skip=("wall_b",)` gives `[]`. A door cut into `wall_a` by `cut_holes` changes nothing. A `seg` wall at 30 degrees beside `wall_a` is not reported, and stdout has a line starting `NOTE wall_gaps:` that names it. A T junction filled by its own square piece `wall_sq` (the first G1 layout of T16, as boxes 2.6 m high) gives `[]`.
  - `wall_gap_check` openings (G2): `floor (-3, 5, -3, 3, -0.1, 0)`, `wall_a (0, 2, 0, 0.1, 0, 2.6)`, `wall_b (2.9, 4, 0, 0.1, 0, 2.6)`, `ceiling (-3, 5, -3, 3, 2.6, 2.7)`, `floors=("floor",)`: `[("wall_a", "wall_b", "no-header", 0.9)]`. With `head_1 (2, 2.9, 0, 0.1, 2.1, 2.6)` added: `[]`. With the header named `wall_head` instead: `[]`. With no ceiling and no header: the `no-header` item. With the header, and the floor split into `floor (-3, 2.2, ...)` and `floor_r (2.7, 5, ...)`, both in `floors`: `[("wall_a", "wall_b", "no-floor", 0.9)]`; adding `ground (-3, 5, -3, 3, -3.1, -3)` to the scene and to `floors` gives the same; `floors=()` gives `[]`. With the header and walls from z -0.1: `[]`. `full_height=(("wall_b", "wall_a"),)` with no header: `[]`.
  - `flipped_check`: boxes `ok`, `inside_out` (`flip_normals()`), `mixed` (one face reversed with bmesh), `open_box` (top face deleted), `mirrored` (scale (-1, 1, 1)), a `cyl`, a `sphere`, and a `lathe` from each profile direction give exactly `[("inside_out", "inside-out"), ("mixed", "mixed")]`. `skip=("mixed",)` drops that item; an inside-out box with `hide_render` is not reported.
  - `floor_fit_check(("floor", "up_floor"))`: `floor (-5, 5, -5, 5, -0.5, 0)`, `up_floor (0, 5, 0, 5, 0, 0.11)`, and boxes, each over `floor` alone unless stated: `on_floor` (base 0), `sunk5mm` (base -0.005), `float_011` (base 0.11, over `floor`), `buried_011` (base 0, inside `up_floor`'s footprint), `deep_sunk` (base -0.4 at x -4 to -3, y 2 to 3), `shelf` (base 1.2), `on_upper` (base 0.11 on `up_floor`), `outside` (beyond both floors, base 0.2), `float_002` (base 0.02), `float_003` (base 0.03), `wall_deep` (base 0 inside `up_floor`'s footprint, top 2.6), `wall_float` (base 0.05 over `floor`, top 2.6). Result: `[("buried_011", -0.11), ("deep_sunk", None), ("float_003", 0.03), ("float_011", 0.11), ("wall_float", 0.05)]`. `skip=("float_011",)` drops that item.
  - `floor_fit_check` floor orientation (G5): `floor (-5, 5, -5, 5, -0.5, 0)`, `on_floor (0, 1, 0, 1, 0, 1)`, `float_011 (2, 3, 2, 3, 0.11, 1)`. Each of these floors gives exactly `[("float_011", 0.11)]`: the box as built; with scale (-1, 1, 1); after `flip_normals()`; and a slab of the same extent built with bmesh from the x-z profile `(-5, -0.5), (-5, 0), (5, 0), (5, -0.5)` extruded along y (world signed volume below zero).
  - `floor_fit_check` support (G6), over `floor (-5, 5, -5, 5, -0.5, 0)`: `rug (0, 2, 0, 2, 0, 0.03)` with `chair (0.5, 1, 0.5, 1, 0.03, 0.9)`; `plinth (3, 4, 0, 1, 0, 0.1)` with `vase (3.3, 3.6, 0.3, 0.6, 0.1, 0.5)`; `tread_0 (0, 1, -2, -1.75, 0, 0.18)` with `nosing_0 (0, 1, -2.0, -1.96, 0.17, 0.2)`; `bed_frame (-3, -1, 0, 2, 0, 0.25)` with `mattress (-3, -1, 0, 2, 0.25, 0.45)`; `panel_old (2, 2.4, 3, 3.4, 0.11, 0.9)`; `led_riser (0.1, 0.9, -2.01, -1.99, 0.06, 0.08)`. Result: `[("led_riser", 0.06), ("panel_old", 0.11)]`.
  - `camera_check`, open box: `floor (-5, 5, -5, 5, -0.1, 0)`, `open_box (-0.5, 0.5, -0.5, 0.5, 0, 1)` with its top face deleted, perspective entry `loc (0, -3, 3)`, `target (0, 0, 0.5)`, lens 24, res 160. Result: exactly one item `("backface", "open_box", n, box)` with n > 0, and `box` inside the pixel box of `project_points` of the opening's four top corners, widened by 1 px. Stdout has the exterior NOTE. `skip=("open_box",)` gives `[]`. `blocker (-0.3, 0.3, -1.6, -1.4, 1.9, 2.1)`, between the camera and the opening, lowers the count (512 to 34 in the verification); with `visible_camera` off on it, the result equals the result without it. `rays=320` gives at least 3 times the count. The same box made with negative x scale still gives the backface item, and a closed box with scale (-1, 1, 1) in view gives none.
  - `camera_check`, escape: walls `(-2, 2, -2, -1.9)`, `(-2, 2, 1.9, 2)`, `(-2, -1.9, -1.9, 1.9)`, `(1.9, 2, -1.9, 1.9)`, z 0 to 2.5, on a floor `(-2, 2, -2, 2, -0.1, 0)`, `ceil_a (-2, 0, -2, 2, 2.5, 2.6)`, `ceil_b (0.6, 2, -2, 2, 2.5, 2.6)`, camera `loc (-1.5, -1.5, 1.6)`, `target (1, 1, 2.3)`, lens 18, res 160. Result: one item `("escape", None, n, box)` with n > 0. With `ceil_b` from x 0 the result is `[]`; with the hole and `interior=False` it is `[]`; with `ceil_a` hidden from render it is `[]` (exterior, NOTE printed) and with `interior=True` it has an escape item. A plan entry's camera gives `[]`.
  - `clearance_check`: treads `stair_i (0, 1, 0.25 i, 0.25 (i + 1), 0, 0.18 (i + 1))` for i 0 to 3, paths `t_i = (0, 1, 0.25 i, 0.25 (i + 1), 0.18 (i + 1))`, side walls `side_l (-0.1, 0, 0, 1, 0, 3)` and `side_r (1, 1.1, 0, 1, 0, 3)`, and `slab_above (-1, 2, 0.5, 3, zb, zb + 0.3)`. zb 2.80 gives `[]`; zb 2.60 gives `[("t_3", "slab_above", 1.88)]`; zb 2.60 with `headroom=1.8` gives `[]`. With zb 2.80 plus `guard_x (0, 1, 0.5, 0.515, 0.54, 1.454)`: `[("t_2", "guard_x", None)]`. With zb 2.80 plus `guard_in (0.3, 0.4, 0.55, 0.6, 0.7, 1.0)` (inside, touching nothing): `[("t_2", "guard_in", None)]`. `skip=("slab_above",)` with zb 2.60 gives `[]`. Feet: after `set_units("ft")`, treads 3 ft wide, 11/12 ft deep, 7.5/12 ft risers, `slab_above (-1, 4, 1.5, 6, 8.8, 9.5)`: `unit=None` gives `[("t_3", "slab_above", 1.92024)]`; the same scene checked after `set_units("m")` with `unit=0.3048` gives the same.
  - `coplanar_check(skip=("cp_b",))` on two coplanar overlapping boxes gives `[]`. A box with scale (-1, 1, 1) resting on a floor box gives `[]`; with scale (1, 1, 1) and the same placement it also gives `[]`.
  - `run_checks`, captured with `contextlib.redirect_stdout` and catching `SystemExit`. Clean scene (floor, four walls butted at the corners as in the template with no door or other opening, a ceiling resting on them, a counter on the floor, a perspective camera inside the room): the lines `OK coplanar`, `OK flipped`, `OK wall_gaps`, `OK floor_fit`, `OK camera` (each followed by ` (<t> s)`), `SKIP clearance: no paths given`, and last `OK run_checks`; no exit. Add `float_011` (base 0.11): `FAIL floor_fit: 1 (`, the line `  float_011 floating 0.110 m`, the camera line still printed, last line `FAIL run_checks: floor_fit`, exit code 1. `exempt={"floor_fit": ["float_011"]}`: passes. `exempt={"floor_fit": ["no_such"]}`: prints `WARN exempt floor_fit: no object named no_such`. `exempt={"florr_fit": []}`: `ValueError` and no `OK`/`FAIL` line. `floors=()`: `SKIP floor_fit: no floors given`. `floors=("nope",)`: the WARN line and `SKIP floor_fit: none of the floors exists`. Clean scene plus a mannequin: still `OK run_checks`. 25 floating boxes: 20 hit lines, then `  ... and 5 more`. A box moved to float by setting `location` with no view-layer update is still reported; this checks behaviour only and does not guard the `update()` line (G9). A plan camera: `SKIP camera: orthographic camera`.
  - `run_checks` walls (G4): the clean scene with its walls renamed `w_south`, `w_north`, `w_west`, `w_east`, and `w_east` moved 0.05 m east, with `walls=("w_",)`: the wall_gaps lines are `FAIL wall_gaps: 2 (` and two `corner 0.050 m` lines that name `w_east` (checked in the prototype). With the default `walls`, the same scene gives `OK wall_gaps`. Assert only the wall_gaps lines.
  - `run_checks` errors (G3): with `checks.floor_fit_check` replaced by a function that raises `RuntimeError("boom")`, the output has `FAIL floor_fit: error RuntimeError: boom`, the camera and clearance lines after it, last line `FAIL run_checks: floor_fit`, and exit code 1. The clean scene plus an object with an empty mesh, and a box whose boolean difference removes all of it, still ends `OK run_checks`.
  - `run_checks` openings: the opening scene above (no header) with `exempt={"openings": [("wall_a", "wall_b")]}` gives `OK wall_gaps`; `exempt={"openings": [("wall_a", "no_such")]}` prints `WARN exempt openings: no object named no_such`.
  - `bh.EYE_HEIGHT == 1.5875`.
- T18 Timing case, the last case of `tests/bl_rev6.py`: the 1,925-object synthetic scene from the verification (seeded `random.Random(1)`), each of the six checks timed; passes when their total is under 60 s, and prints each time. It guards only against a check whose cost grows with the square of the object count, such as a BVH built per pair.
- T19 `run_tests.sh`: add `wall_gaps.py` to the required files, `tests/seed_template.py` to the syntax step, and `test_wall_gaps.py` and the Blender step to the suite; each template view's log must have the line `^OK run_checks$` before `DONE`. Negative template step: `tests/seed_template.py`, copied beside the template copy, imports `scene_template`, wraps `build` to add `box("float_test", 2.0, 2.4, 3.0, 3.4, 0.11, 0.9)`, and calls `main()` with `--view persp`; the run must exit non-zero, its log must have `^FAIL run_checks: floor_fit$`, and it must have no `^DONE` line.
- T20 `test_api_doc.py` also checks `wall_gaps`.
- Mutation checks (report each): remove the `wall_gaps` corner rule; make `flipped_check` read world coordinates; drop the walls float-only rule; use `Scene.ray_cast` in `camera_check`; drop the vertex test in `clearance_check`; drop the figure skip in `run_checks`; drop the negative-determinant normal fix in `coplanar_check`; stop `run_checks` after the first failure; drop the fill subtraction in `wall_gaps` (G1); drop the opening probe's up ray, or its down ray (G2); remove the `try` around each check (G3); stop passing `walls` to `wall_gap_check` (G4); drop the floor orientation fix in `floor_fit_check` (G5); drop its support test (G6); let the checks read empty meshes (G3). Each must fail at least one of T16 to T19.

### Evals

Fresh subagents read `SKILL.md` by absolute path, not through the Skill tool; synthetic data only.
- E1: "A 12 x 16 ft room with a 4 5/16 in step to a raised landing and a straight stair of 7 risers up to a floor 9 ft above; render an eye-level preview from the room." Pass: `set_units("ft")`, `run_checks` with every floor named and one path per tread, every hit fixed or exempted with a reason, the camera at the floor plus `EYE_HEIGHT / U`.
- E2: a synthetic 150-line legacy build script (its own `box()`, feet, no checks) with a floating panel, a missing wall corner, and a guard across a tread. Prompt: "The renders show odd gaps; add the skill's checks and fix what they find." Pass: the wiring above before the render call with `unit=0.3048`, `--python-exit-code 1` in the run command, all three defects fixed, no prefix exemptions.

### Revision 6 eval results (2026-10-21, fresh sonnet subagents, SKILL.md read by path, synthetic data)

- E1 pass. Feet units, every floor named, one walking box per tread and the landing, the camera at the floor plus `EYE_HEIGHT / U`, no exemptions. The checks caught sky through an unenclosed stairwell, a one-ray backface on a butted stair block (an edge graze, P1 below), and the hidden bottoms of butted blocks on one plane (coplanar). Gaps: (a) the skill gives no rule for a stair built from boxes; butted boxes trip camera and coplanar, and the agent nudged sizes by 1 mm to clear them; (b) SKILL.md step 5 requires `context/dimensions.md` with no exemption for a quick preview, and the agent skipped it. The prompt's "9 ft above" gave a 14 13/16 in riser; that is the prompt's fault, not the skill's.
- E2 pass. The wiring sits before the render call with `unit=0.3048`, the run command keeps `--python-exit-code 1`, all three planted defects are fixed (`cab_low` floating, the 0.15 ft corner gap, the mid rail across tread 3), and nothing is exempted. The checks also found two real defects the fixture did not plant: table legs coplanar with the rug bottom, and ceiling headroom under 2.032 m over the top treads. Gaps: (c) no rule for `interior` in a script without a VIEWS table (the agent passed `interior=True`); (d) the agent first drew tread boxes across the full stair width and got `inside` hits from the rails, then narrowed them as D5 says.

### Pre-merge review findings (2026-10-21, opus, at `b1c7749`)

Verdict: merge after fixes. Suite 50 of 50. Every test added since `aaaa951` fails on the mutation it targets (verified by mutating copies of `scripts/`). No shell, file writes, or eval in the new code; no project names or absolute paths in shipped files. Resolutions wait for the user.

- P1 Important. `camera_check` reports a backface where a ray grazes a silhouette edge (`checks.py:410-414`). E1's stair with the 1 mm nudge removed gives `backface stair_3: 1 rays` at a front vertical edge; jittered rays hit the front face and the wall, so no face is missing. This, not a crack, caused E1 gap (a). Proposed: on a backface hit, cast two rays offset by a quarter cell, and count it only if one also hits a backface on the same object. Test: a box edge under a cell-centre ray.
  Resolution: fixed at `0ce6203`: a backface counts only when a ray a quarter cell off diagonally also hits a back face of the same object. Tests: `t_camera_graze`, `t_camera_backface_area`.
- P2 Important. `floor_fit` reports an object that runs up into a named upper slab as sunk more than 0.300 m (`checks.py:349-352`): a beam at z 2.8 to 3.1 and a downlight at 2.95 to 3.05 under a slab at 3.0 to 3.2. Present since `352a14b`. Proposed: when the first hit faces down above `lo.z + tol`, cast again from just below it. Test: both give `[]`; `deep_sunk` keeps `None`.
  Resolution: fixed at `0ce6203`: after a down-facing first hit above the base, an up ray decides; an object whose top stays below the slab top is measured against the floor below, and one that pierces the slab stays sunk (the plain recast missed a piercing object, found by the test author). Test: `t_floor_fit_hung_into_slab`; a piercing object through a 0.2 m floor still reports None (scratch probe).
- P3 Important, docs. A plan-input scene fails `no-header` on every door, and an exemption would name index-built walls, which D6 forbids. Proposed for `reference/plan-input.md`: add a header box over each door opening; rename the two walls to stable names before you exempt an opening.
  Resolution: added both sentences to `reference/plan-input.md`, after the `walls_from_plan` snippet.
- p1. A fully buried thin object reports "sunk more than 0.300 m". Proposed: document it, or print "inside a floor".
  Resolution: documented in SKILL.md (checks notes); the printed text is unchanged.
- p2. SKILL.md's SKIP list omits `none of the floors exists` and `scene camera is not a camera object`.
  Resolution: SKILL.md's SKIP row lists all six reasons, copied from `run_checks`.
- p3. SKILL.md says `run_checks` leaves the figure out of "most checks"; it is coplanar, floor_fit, and clearance.
  Resolution: SKILL.md names coplanar, floor_fit, and clearance.
- p4. `reference/plan-input.md`: the `wall_gaps` call belongs in the snippet before `walls_from_plan`.
  Resolution: the `wall_gaps` call sits in the snippet before `walls_from_plan`; the separate sentence is gone.
- p5. `docs/ISSUES.md` still says "Next: evals"; the eval gaps are not logged.
  Resolution: `docs/ISSUES.md` Next line updated; eval gap (b) logged under Planned.
- p6, writing rules: "each tread's box" for "walking box" (SKILL.md:124); "is not probed" for "checked" (SKILL.md:130); three descriptions of 28 to 31 words in `reference/api.md` (118, 119, 123).
  Resolution: SKILL.md uses "walking box" and "gets no opening check"; the three `reference/api.md` descriptions are split.
- Eval gaps: (a) needs P1 and the rule "Build each stair step as one box from its riser to the next riser, butted to its neighbours"; (b) log for later; (c) optional rule "In a script without a VIEWS table, leave out `interior` unless the view looks out through an opening without glass"; (d) no change.
  Resolution: (a) stair rule added to SKILL.md, the code fix waits on P1; (b) logged in `docs/ISSUES.md`; (c) interior rule added to SKILL.md; (d) no change.

### Review findings (2026-10-20)

Architecture review of the first Revision 6 text at `a5e5158` (opus, read-only; it read project B's build script and README). Severity as the reviewer gave it.
- G1 Blocker. `wall_gaps` compared walls in pairs only, so it reported correct junctions. Evidence: R22 run as written gave hits for a T filled by its own square, a stem through a split wall, an X crossing, and an L with a corner square; project B fixes junctions with such pieces. Resolved: R22 subtracts every wall rect from the gap region or junction region and keeps a hit only when at least touch² is left; the four layouts and a jog closed by a column are T16 cases expecting `[]` (prototype verified).
- G2 Important. A missing header or jamb built as a separate closed box raises no check, and the coverage table claimed it did. Evidence: project B builds jambs and headers as separate boxes and skips a header when the two wall pieces are out of line by more than 0.08 ft. Resolved by the user's decision (skill `docs/ISSUES.md`, Decisions): R25 probes each door-sized opening between in-line walls with an up ray (`no-header`) and a down ray (`no-floor`), and the `openings` exemption takes wall-name pairs. The coverage table now lists a missing jamb box as not caught. Verified in Blender (Verified, review round).
- G3 Important. Without `--python-exit-code 1`, an exception exits 0 and leaves the old image. Evidence: the reviewer's run of a raising script gave exit 0. Resolved: R29 runs each check in `try`/`except` and prints `FAIL <check>: error ...`; R32 leaves out empty meshes; the wiring and D5 keep the flag; T17 has a raising check and an empty mesh.
- G4 Important. `walls` never reached `wall_gap_check`. Evidence: R29 passed it only to floor fit, while D5 told users to pass their wall prefixes in it. Resolved: R29 passes `walls` to both; T17 runs with `walls=("w_",)`.
- G5 Important. `floor_fit` read mirrored and inside-out floors as facing down. Evidence: a slab in project B's point order has signed volume -12; R26 as written reported every object on such floors as sunk more than 0.30 m (verified on three floors). Resolved: R26 orients each floor by its world signed volume, or by its determinant when open; T17 covers all three. The optional part, backfaces on open meshes only, is rejected (Simplify list).
- G6 Minor. The floor-fit false-positive list missed stair parts and objects resting on objects. Evidence: the reviewer's heights for project B's guards, stringer shoes, riser LEDs, and nosings, all under 0.30 m. Resolved: the table and the backlog note list them, and R26 adds the support test, so an object resting on another under its centre passes (verified; question B1).
- G7 Minor. D6's "exact names, never prefixes" contradicted the skill's prefix parameters. Resolved: D6 scopes the rule to `exempt` and to lists a script moves or skips, and adds a rule on stable names, since the WARN line misses an index name that now points at another object.
- G8 Minor. The x0 sweep was not needed and compared metres with rect units; T18 guarded only a prefilter that coplanar already has. Resolved: the sweep is deleted; T18 is a timing case in `bl_rev6.py`, and the plan says what it guards.
- G9 Minor. Test plan gaps. Resolved: T16 has an exact out-of-order result; the clean `run_checks` scene has no door; the blocker has coordinates; the stale-position test is marked as not guarding `update()`; T19 adds `seed_template.py` to the syntax step; G1, G3, G4, and G5 have tests.
- G10 Minor. The camera pixel box points into an image that a failing run never writes. Resolved: D5 says which image the box refers to and how to see the place.
- G11 Minor, uncertain. The checks missed instances and saw objects that never render. Resolved: R32 reads `view_layer.objects`, which leaves out excluded collections and other scenes (verified); instances and collection-level render switches are documented limits in R32 and D5.
- G12 Minor. Wording: D11 put two instructions in one sentence, D6 put a condition after its action, and D5 dropped the clash instruction for furniture. Resolved in D5, D6, and D11.
- G13 Minor, uncertain. The design names the user. Kept, by decision (skill `docs/ISSUES.md`, Decisions).

### Code review findings (2026-10-20, opus, at `352a14b`)

Suite at review: 48 passed, 2 failed (the expected `test_api_doc` steps). Scratch probes are outside the repo. the user approved the fixes below on 2026-10-20 (M1, M2); the fixes amend R22, R24, R26, R27 wiring and R32.

- C1 Critical. A plan view fails `no-header` on every split-wall opening with a header. `plan_cut` hides objects above the cut from render, so the up ray finds nothing (`checks.py:286-297`, `bhelpers.py:977-1002`; verified in Blender). Fix: run the opening up-ray probe only when the scene camera is perspective; a plan run checks floors only. Test: the opening scene with a header under a plan camera gives `OK wall_gaps`.
- I1 Important. `floor_fit` reports ceilings, beams, and pendants under an upper slab as sunk, because the probe starts above or inside that slab (`checks.py:337-343`; verified). Fix: start the probe at `min(lo.z + hang, hi.z - 1e-4)`. Test: a two-storey case.
- I2 Important. An open floor with a downward normal makes every object above it "sunk more than 0.300 m"; the determinant rule is wrong for an open mesh (`checks.py:83-86`; verified). Fix: orient each face of an open floor, and of an open support candidate, so its world normal z is at least 0. Test: an unmirrored open plane with a downward normal.
- I3 Important. `wall_gaps` is cubic in the wall count: 800 walls take 43.5 s (`wall_gaps.py:80`; verified). Fix: build the fill list only for candidate pairs (0.15 s at 800 walls). Test: a plain-Python timing case in T16, 800 rects under 2 s.
- I4 Important. Three mutations survive: the support ray accepting any facing (`checks.py:353`), removing the open-floor branch (`checks.py:85`), and the literal `abs(z - top) <= tol` (`checks.py:286`). Fix: add an open mirrored floor, a support candidate whose down face is within 2 tol, a wall under 1 m, and the mirrored-and-inside-out floor.
- m1. Named floors that are hidden from render, excluded, or not meshes pass silently (`checks.py:498-507`). Fix: check existence against the R32 set; print `SKIP floor_fit: none of the floors exists` or a WARN.
- m2. A bare string for `floors` or `exempt` is read letter by letter (`checks.py:499-511`). Fix: treat a `str` as one name.
- m3. Half walls under a ceiling report `no-header`. Fix (M2): probe only when the lower wall top is at least 2.0 m.
- m4. A thin gap closed by a column still reports (`wall_gaps.py:86-88`). Contract behaviour; logged in skill `docs/ISSUES.md`.
- m5. A plan rotated off the axes is silently unchecked. Not fixed in Revision 6; document in D5 (a later fix could print `SKIP wall_gaps: no axis-aligned walls`).
- m6. Checks see viewport geometry, not render geometry (a boolean with `show_viewport=False`). Document in D5 beside the instance limit.
- m7. Overlapped wall corners give coplanar hits. Add them to the backlog note's list.
- m8. `scene.camera` set to a non-camera object raises before the gate (`checks.py:520-522`). Fix: test `cam.type != "CAMERA"`.
- m9. The top-level `wall_gaps` import breaks a project that copies only `checks.py`, outside the gate. Fix: import inside `wall_gap_check`, so a missing module prints `FAIL wall_gaps: error ModuleNotFoundError`.
- Implementer deviations, all accepted: floor winding by raw world signed volume (R26's "or both" remark is wrong; fix the text); openings skipped at or above top minus tol; `SKIP camera: panoramic camera` (add to D5); `_off_axis` as the sine off the nearest axis.

### Re-review findings (2026-10-20, opus, at `aaaa951`)

the user approved the fixes below on 2026-10-21 (Q1). The 2.0 m rule now gates only the `no-header` probe, so `no-floor` still runs at half walls more than 1 m above the higher wall bottom; this amends m3.

- N1 Important. The m3 gate compares the wall top's absolute z with 2.0 m, not the wall height (`checks.py:296`, `top < 2.0`). Fix: gate on `top - max(bottoms) < 2.0`. Tests: walls on a storey at z 3.0 and at z -2.7.
- N2 Important. The I1 probe start fails for a zero-thickness object on the floor top: the probe starts inside the floor and reports sunk more than 0.300 m (`checks.py:348`; verified at 0 and 5e-5 m). Fix: start at `min(lo.z + hang, max(hi.z - 1e-4, lo.z + 1e-4))`.
- N3 Minor. The mutation that removes the height gate survives. Test: `wall_a` 0 to 3.0 m and `wall_b` 1.4 to 3.0 m under a ceiling give `[]`. The reviewer's 0 to 2.6 m and 1.6 to 2.6 m case does not catch the mutation, because the `z >= top - tol` skip also covers it.
- N4 Minor. `exempt={"openings": ("wall_a", "wall_b")}`, one pair not wrapped in a list, is read as two names. It fails safe: the hit stays and the run exits 1 (verified). Fix: a test that pins the fail-safe result, and the list form shown in D5.

### Open questions

None open. the user answered A1 to A7 and B1 on 2026-10-20, accepting each recommendation (skill `docs/ISSUES.md`, Decisions): `exempt` takes exact names only (A1); fix `lathe` normals (A2); add the dark-sill QA item (A3); fold in the coplanar mirrored fix (A4); keep the 0.30 m hung limit (A5); approve the revised T16 to T20 (A6); send the wiring to the render project after v1.0.0 (A7); keep the floor-fit support test (B1).

### Order of work, and how to continue if interrupted

R22 and T16 first (plain Python), then R32 and R23 to R29 with T17 and T18, then R30 and R31 with T19, then T20, then docs D5 to D12, then evals. Each finished item is ticked in skill `docs/ISSUES.md` under Revision 6; a fresh session reads that line, this section, and `git log` on `rev6-phantom-checks`.
