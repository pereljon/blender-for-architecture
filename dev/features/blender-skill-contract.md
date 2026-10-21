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

## Revision 6 (2026-10-20, phantom geometry defects; requested by render project B, approved by the user)

Source: `../inputs/2026-10-20-phantom-defects.md`. Decision: skill `docs/ISSUES.md`, Decisions, 2026-10-20. Investigated against this repo at `6cf8009` and Blender 5.2.0 LTS, and against render project B's build script and README (read-only, the two files the user named).

One gate, `run_checks()`, runs six checks over the whole scene right before every render, previews included: the existing `coplanar_check` and five new checks (flipped faces, wall gaps, floor fit, camera rays, clearance). Every check skips objects hidden from render and reads evaluated geometry (modifiers and booleans applied). Lengths inside the checks are world metres, so a script that builds its own scene in feet gets the same results; only `paths` takes project units. Every hit names the objects involved.

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

Flags on the approved shape: "every check over the whole scene" leaves out `clash_check` and leaves the figure out of coplanar, floor fit, and clearance; "each view's camera" is the scene camera of the run, since a run renders one view; exemptions are exact names, but walls and the figure are selected by prefix, as `clash_check`, `coplanar_check`, and `plan_cut` already select (question A1).

### Code (implementer)

Keep out: the implementer does not edit `tests/`; the test author does not edit `scripts/` or `templates/`.

- R22 `scripts/wall_gaps.py` (new, plain Python, imports only `math`): `wall_gaps(rects, unit=1.0, gap=0.3, touch=0.001)`. `rects` items are `(x0, x1, y0, y1, ...)` tuples (extra items ignored) or dicts with those keys (`load_plan` walls); each is normalised so x0 <= x1 and y0 <= y1. `unit` is metres per rect unit; `gap` and `touch` are metres. For each pair, with separations dx, dy >= 0 and d = hypot(dx, dy) in metres: when touch < d <= gap, report `(i, j, "gap", d)`. When d <= touch, the pair touches or overlaps: if both overlap lengths exceed `touch`, it is an overlap and fine; otherwise the contact length c is the larger overlap length, and when c < min(thickness_i, thickness_j) - touch (thickness = a rect's shorter side), report `(i, j, "corner", c)`. That catches walls meeting only at a corner point, a partial butt that leaves a notch, and a false jog. Return the hits sorted by (i, j), with i < j indexing the input list and lengths in metres. Sweep pairs in x0 order and stop a sweep once the next x0 is more than `gap` past the current x1.
- R23 `coplanar_check(prefixes=None, tol=0.0005, min_area=1e-6, skip=())`: `skip` holds exact object names to leave out. Fix: `_tris` negates each normal of an object whose `matrix_world` has a negative determinant, so a mirrored object's faces keep their real facing. Otherwise unchanged.
- R24 `flipped_check(skip=())`: for each render-visible mesh object not in `skip`, take the evaluated mesh in local coordinates. Skip it unless every undirected edge is used by exactly two polygon sides (closed). Report `(name, "mixed")` when any directed edge appears twice (some faces turned against their neighbours); otherwise report `(name, "inside-out")` when the signed volume is below -1e-12. Sorted by name.
- R25 `wall_gap_check(prefixes=("wall_",), gap=0.3, touch=0.001, skip=())`: render-visible mesh objects named with `prefixes`, not in `skip`. A wall's footprint is the world x-y box of its evaluated vertices. Leave out a wall when any world polygon normal is more than 1e-4 off a world axis (angled `seg` walls, bevelled walls), and print one line `NOTE wall_gaps: not axis-aligned, not checked: <names>`. Run `wall_gaps` on the footprints with `unit=1.0`; drop pairs whose z ranges overlap by `touch` or less (walls on different levels). Return `[(name_i, name_j, kind, length_m)]`, each pair's names in name order, sorted.
- R26 `floor_fit_check(floors, walls=("wall_",), tol=0.025, hang=0.3, skip=())`: `floors` are exact names. Build one BVH from the render-visible floor objects' world polygons. For each other render-visible mesh object not in `skip`: take its world box (lo, hi) and cast a ray straight down from (centre x, centre y, lo.z + hang) against the floor BVH. On a miss, the object is not over a floor: skip it. When the first hit faces up, d = lo.z - hit z: report `(name, d)` when d < -tol (sunk) or tol < d < hang (floating); d >= hang means hung (lights, upper cabinets, headers) and passes. When the first hit faces down, the probe started inside a floor: report `(name, None)` (sunk more than `hang`). Objects named with `walls` prefixes are reported only when floating: walls may run down through a slab. Sorted by name.
- R27 `camera_check(interior=None, rays=160, skip=())`: uses `scene.camera`; returns `[]` when there is no camera or it is not perspective. Builds a BVH from render-visible mesh and curve objects with `visible_camera` on, not in `skip`, with each polygon's vertex order reversed when the object's `matrix_world` has a negative determinant. Grid: `rays` columns, rows = max(1, round(rays * res_y / res_x)), one ray per cell centre through the `view_frame(scene=scene)` plane, from the camera at `clip_start` for at most `clip_end - clip_start`. A hit with `normal.dot(direction) > 0` is a `backface` on the hit object. A miss is an `escape` when the view is interior. `interior=None` means auto: interior when a ray straight up from the camera hits anything within `clip_end`; when auto finds an exterior view, print `NOTE camera: exterior view, escapes not checked`. `interior=False` never checks escapes; `interior=True` always does. Return `[(kind, name, count, (x0, y0, x1, y1))]`: one item per kind and object (name `None` for escapes), with the pixel box of the ray centres, rounded to whole pixels, y down. Sorted by (kind, name or "").
- R28 `clearance_check(paths, headroom=2.032, unit=None, tol=0.005, skip=())`: `paths` maps a name to `(x0, x1, y0, y1, z)` in project units, z being the walking surface (tread top); `unit` None means `bhelpers.U` (import inside the function). Each walking box in metres is [x0 + tol, x1 - tol] x [y0 + tol, y1 - tol] x [z + tol, z + headroom]. An object (render-visible mesh or curve, not in `skip`) is a hit when its world polygons cross the box (BVH overlap) or any of its world vertices lies strictly inside the box. Headroom: cast a 3 x 3 grid of rays straight up from the box bottom, at cell centres; for a hit object, headroom = the lowest hit on it minus z (metres), or `None` when no grid ray hits it. Return `[(path, name, headroom_m or None)]` sorted by (path, name). 2.032 m is 6'-8".
- R29 `run_checks(floors=(), walls=("wall_",), paths=None, figure=("man_",), exempt=None, interior=None, unit=None, rays=160)`:
  - Call `bpy.context.view_layer.update()` first.
  - `exempt` maps a check name (`coplanar`, `flipped`, `wall_gaps`, `floor_fit`, `camera`, `clearance`) to exact object names. Raise `ValueError` for an unknown check name, before any check runs. For each exempt name that no object has, print `WARN exempt <check>: no object named <name>`; for each name in `floors` that no object has, print `WARN floors: no object named <name>`.
  - Objects named with `figure` prefixes are added to `skip` for coplanar, floor fit, and clearance.
  - Run in this order, each with its `exempt` names as `skip`: coplanar, flipped, wall_gaps, floor_fit (`floors`, `walls`), camera (`interior`, `rays`), clearance (`paths`, `unit`). Run every check even after a failure.
  - Print per check: `OK <check> (<t> s)`, or `FAIL <check>: <n> (<t> s)` followed by one indented line per hit (at most 20, then `  ... and <k> more`), or `SKIP <check>: <reason>`. `<t>` has two decimals. Skips: floor_fit `no floors given` or `none of the floors exists`; camera `no scene camera` or `orthographic camera`; clearance `no paths given`.
  - Hit lines: coplanar `  <a> <b>`; flipped `  <name> inside-out` or `  <name> mixed`; wall_gaps `  <a> <b> gap|corner <length:.3f> m`; floor_fit `  <name> floating <d:.3f> m`, `  <name> sunk <-d:.3f> m`, or `  <name> sunk more than <hang:.3f> m`; camera `  backface <name>: <n> rays at px <x0>-<x1>, <y0>-<y1>` or `  escape: <n> rays at px <x0>-<x1>, <y0>-<y1>`; clearance `  <path> <name> headroom <h:.3f> m` or `  <path> <name> inside`.
  - Last line: `OK run_checks`, or `FAIL run_checks: <failed checks, comma-separated>` and then `sys.exit(1)`. Returns None.
- R30 `bhelpers.EYE_HEIGHT = 1.5875` (metres; the eye of a 5'-7" viewer, 5'-2 1/2"). `lathe` calls `bmesh.ops.recalc_face_normals` on its faces before writing the mesh, as `prism` and `slab` do, so a lathe built from either profile direction passes `flipped_check` (question A2).
- R31 Template: import `run_checks`; drop the scoped `coplanar_check` call and its stale comment; keep the `clash_check` call where it is; after `add_camera`, call `run_checks(floors=("floor",), interior=VIEWS[args.view].get("interior"))`, then render. The perspective entry's eye height becomes `bh.EYE_HEIGHT / bh.U`. Both views must print `OK run_checks`.

Tolerances, false positives, and exemptions:

| Check | Defaults | Known false positives | Remedy |
|---|---|---|---|
| coplanar | tol 0.5 mm, min_area 1e-6 m2 | Curved meshes with tangent faces; overlapping slab pieces whose shared top is hidden | Figure left out by prefix; exempt by name or fix the overlap |
| flipped | volume below -1e-12 | A closed mesh made inside out on purpose (none known) | Exempt by name |
| wall_gaps | gap 0.30 m, touch 1 mm | A chase between two parallel walls; an opening narrower than 0.30 m | Exempt one of the two walls by name |
| floor_fit | tol 25 mm, hang 0.30 m | Plinth-raised fronts (toe kick about 0.10 m), a floating bed, door undercuts over 25 mm | Exempt by name |
| camera | 160 columns; interior auto | Single-sheet meshes seen from behind (backdrops, leaves, open `lathe` profiles); a view through an opening without glass | Exempt by name; `interior=False` in that view's entry |
| clearance | headroom 2.032 m, tol 5 mm | Handrails inside a box drawn wider than the clear width | Draw the box between the handrails |

Defects in the request, and what catches each:

| Defect | Caught by | Not caught |
|---|---|---|
| 1. Missing wall pieces at junctions | `wall_gaps` (gap, corner); `camera` escape when the gap opens to sky in an interior view | Walls outside the `walls` prefixes; angled walls; gaps wider than 0.30 m |
| 2. Opening interiors | `camera` backface for a missing jamb or head face in view | The dark full-depth sill (geometry was present; a material reads as a hole): QA item, D8. A thin slot seen at an angle shows a dark line and lets no ray escape |
| 3. Slab side coplanar with a wall face | `coplanar` over the whole scene | Nothing |
| 4. Objects left at the old floor level | `floor_fit` (project B's offsets were 0.11 m and 0.22 m) | Offsets of 0.30 m or more; objects over no named floor. The prefix skip that caught an unrelated object: rule, D6 |
| 5. Stale `matrix_world` | `run_checks` updates the view layer itself | The script's own reads: rule, D6 |
| 6. Stray guard across a stair | `clearance` `inside` | Paths nobody declared |
| 7. Emissive strips proud of the risers | None | Rule and QA item, D6 and D8 (decision) |
| 8. Headroom 6'-3 5/8" against 6'-8" | `clearance` with the measured headroom | Paths nobody declared |

Wiring in a project script that builds its own scene (sent by skill-developer to the project after the release):

```python
sys.path.insert(0, os.path.join(HERE, "lib"))       # copies of the skill's scripts/*.py
from checks import run_checks

FLOORS = ["floor", ...]          # exact names of every floor, slab, deck, and paving object
PATHS = {}                       # name -> (x0, x1, y0, y1, z), feet; the stair builder adds one per tread and landing
EXEMPT = {}                      # check -> exact object names, each with a dated reason

# in the stair builder, for tread i (box from its nosing to the next nosing, between the guards):
PATHS[f"flight1_{i}"] = (x0, x1, y_nosing, y_next_nosing, tread_top)

# the last call before bpy.ops.render.render(write_still=True):
run_checks(floors=FLOORS, paths=PATHS, unit=0.3048, figure=("person_",), exempt=EXEMPT,
           interior=VIEWS.get(view, {}).get("interior"))
```

Expect a backlog on the first run in an existing scene (overlapping stair treads and slab pieces give coplanar hits; plinth fronts give floor-fit hits). Fix each hit or exempt it by name with a reason.

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
  | wall_gaps | Walls that almost meet, or meet only at a corner |
  | floor_fit | Objects that float above or sink into the floor under them |
  | camera | Faces seen from behind (a missing face), and sky seen from an interior view |
  | clearance | Anything inside the walking box over a stair tread or path, with the headroom |

  - Run the checks before every render, previews included.
  - Fix every hit.
  - If a hit is intended, exempt the object by its exact name: `exempt={"floor_fit": ["vanity_front"]}`.
  - Give the reason for each exemption in a comment.
  - Name every floor, slab, deck, and paving object in `floors`. Without floors, `floor_fit` does not run.
  - Name every wall with the `wall_` prefix, or pass your wall prefixes in `walls`.
  - Add a walking box to `paths` for each stair tread and landing: `(x0, x1, y0, y1, z)`, with z at the tread top.
  - Draw each tread's box between the handrails, from its nosing to the next nosing.
  - If a view looks out through an opening without glass, set `interior=False` in its entry.
  - Run `clash_check` for the figure. `run_checks` leaves the figure out of most checks.
  - In a project script that builds its own scene, copy `scripts/*.py` into its `lib/`.
  - Then call `run_checks` right before the render call, with `unit` set to metres per project unit.
  ```
- D6 SKILL.md Rules for every scene, added:
  ```
  - Call `bpy.context.view_layer.update()` before you read `matrix_world` or any world position. Until then, positions are stale.
  - Use exact object names in a skip list, never prefixes. A prefix also catches unrelated objects.
  - Set an emissive strip into its recess, so that only its front face shows.
  - After a floor or wall level changes, look at every threshold and wall base in a preview.
  - Place an eye-level camera at the floor height plus `EYE_HEIGHT / U`. That is a 5'-7" viewer's eye, 5'-2 1/2".
  ```
- D7 SKILL.md loop: step 2 becomes `Preview at --res 800 --samples 48 --gpu into scratch/; the checks run first`; step 3 becomes `Fix every check hit, then read the preview image`.
- D8 SKILL.md QA list, added: `An emissive strip whose top or sides show, or that streaks nearby glass`; `A dark sill or track across the full wall depth, which reads as a hole` (question A3).
- D9 SKILL.md Scripts table: the `checks.py` row lists `run_checks` and the six checks; a new row `wall_gaps.py | Blender or plain Python | Wall rectangles that almost meet, from a list such as load_plan's`.
- D10 `reference/api.md`: lines for `wall_gaps`, `flipped_check`, `wall_gap_check`, `floor_fit_check`, `camera_check`, `clearance_check`, `run_checks`, `EYE_HEIGHT`, and the new `coplanar_check` signature, from the code. VIEWS entries: perspective entries may carry `interior` (read by the scene script and passed to `run_checks`; `add_camera` ignores it).
- D11 `reference/plan-input.md`, one line: after the correction layer, run `wall_gaps(walls, unit=<metres per unit>)` on the corrected list and fix each hit before you build.
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
  - Three rects given out of x order, with gaps between rects 2 and 0: indices refer to the input order, and hits are sorted by (i, j). Six-item tuples and a rect with x0 > x1 are accepted.
- T17 `tests/bl_rev6.py` (Blender):
  - `wall_gap_check`: boxes `wall_a (0, 4, 0, 0.1, 0, 2.6)` and `wall_b (3.9, 4.0, 0.15, 3, 0, 2.6)` give `[("wall_a", "wall_b", "gap", 0.05)]`; the same in feet (coordinates divided by 0.3048 after `set_units("ft")`) gives 0.05 m. `wall_b` at z 3 to 5.6 gives `[]`; renamed `shelf_b` gives `[]`; `skip=("wall_b",)` gives `[]`. A door cut into `wall_a` by `cut_holes` changes nothing. A `seg` wall at 30 degrees beside `wall_a` is not reported, and stdout has a line starting `NOTE wall_gaps:` that names it.
  - `flipped_check`: boxes `ok`, `inside_out` (`flip_normals()`), `mixed` (one face reversed with bmesh), `open_box` (top face deleted), `mirrored` (scale (-1, 1, 1)), a `cyl`, a `sphere`, and a `lathe` from each profile direction give exactly `[("inside_out", "inside-out"), ("mixed", "mixed")]`. `skip=("mixed",)` drops that item; an inside-out box with `hide_render` is not reported.
  - `floor_fit_check(("floor", "up_floor"))`: `floor (-5, 5, -5, 5, -0.5, 0)`, `up_floor (0, 5, 0, 5, 0, 0.11)`, and boxes, each over `floor` alone unless stated: `on_floor` (base 0), `sunk5mm` (base -0.005), `float_011` (base 0.11, over `floor`), `buried_011` (base 0, inside `up_floor`'s footprint), `deep_sunk` (base -0.4 at x -4 to -3, y 2 to 3), `shelf` (base 1.2), `on_upper` (base 0.11 on `up_floor`), `outside` (beyond both floors, base 0.2), `float_002` (base 0.02), `float_003` (base 0.03), `wall_deep` (base 0 inside `up_floor`'s footprint, top 2.6), `wall_float` (base 0.05 over `floor`, top 2.6). Result: `[("buried_011", -0.11), ("deep_sunk", None), ("float_003", 0.03), ("float_011", 0.11), ("wall_float", 0.05)]`. `skip=("float_011",)` drops that item.
  - `camera_check`, open box: `floor (-5, 5, -5, 5, -0.1, 0)`, `open_box (-0.5, 0.5, -0.5, 0.5, 0, 1)` with its top face deleted, perspective entry `loc (0, -3, 3)`, `target (0, 0, 0.5)`, lens 24, res 160. Result: exactly one item `("backface", "open_box", n, box)` with n > 0, and `box` inside the pixel box of `project_points` of the opening's four top corners, widened by 1 px. Stdout has the exterior NOTE. `skip=("open_box",)` gives `[]`. A box in front of it with `visible_camera` off changes nothing. `rays=320` gives at least 3 times the count. The same box made with negative x scale still gives the backface item, and a closed box with scale (-1, 1, 1) in view gives none.
  - `camera_check`, escape: walls `(-2, 2, -2, -1.9)`, `(-2, 2, 1.9, 2)`, `(-2, -1.9, -1.9, 1.9)`, `(1.9, 2, -1.9, 1.9)`, z 0 to 2.5, on a floor `(-2, 2, -2, 2, -0.1, 0)`, `ceil_a (-2, 0, -2, 2, 2.5, 2.6)`, `ceil_b (0.6, 2, -2, 2, 2.5, 2.6)`, camera `loc (-1.5, -1.5, 1.6)`, `target (1, 1, 2.3)`, lens 18, res 160. Result: one item `("escape", None, n, box)` with n > 0. With `ceil_b` from x 0 the result is `[]`; with the hole and `interior=False` it is `[]`; with `ceil_a` hidden from render it is `[]` (exterior, NOTE printed) and with `interior=True` it has an escape item. A plan entry's camera gives `[]`.
  - `clearance_check`: treads `stair_i (0, 1, 0.25 i, 0.25 (i + 1), 0, 0.18 (i + 1))` for i 0 to 3, paths `t_i = (0, 1, 0.25 i, 0.25 (i + 1), 0.18 (i + 1))`, side walls `side_l (-0.1, 0, 0, 1, 0, 3)` and `side_r (1, 1.1, 0, 1, 0, 3)`, and `slab_above (-1, 2, 0.5, 3, zb, zb + 0.3)`. zb 2.80 gives `[]`; zb 2.60 gives `[("t_3", "slab_above", 1.88)]`; zb 2.60 with `headroom=1.8` gives `[]`. With zb 2.80 plus `guard_x (0, 1, 0.5, 0.515, 0.54, 1.454)`: `[("t_2", "guard_x", None)]`. With zb 2.80 plus `guard_in (0.3, 0.4, 0.55, 0.6, 0.7, 1.0)` (inside, touching nothing): `[("t_2", "guard_in", None)]`. `skip=("slab_above",)` with zb 2.60 gives `[]`. Feet: after `set_units("ft")`, treads 3 ft wide, 11/12 ft deep, 7.5/12 ft risers, `slab_above (-1, 4, 1.5, 6, 8.8, 9.5)`: `unit=None` gives `[("t_3", "slab_above", 1.92024)]`; the same scene checked after `set_units("m")` with `unit=0.3048` gives the same.
  - `coplanar_check(skip=("cp_b",))` on two coplanar overlapping boxes gives `[]`. A box with scale (-1, 1, 1) resting on a floor box gives `[]`; with scale (1, 1, 1) and the same placement it also gives `[]`.
  - `run_checks`, captured with `contextlib.redirect_stdout` and catching `SystemExit`. Clean scene (floor, four walls butted at the corners as in the template, a ceiling resting on them, a counter on the floor, a perspective camera inside the room): the lines `OK coplanar`, `OK flipped`, `OK wall_gaps`, `OK floor_fit`, `OK camera` (each followed by ` (<t> s)`), `SKIP clearance: no paths given`, and last `OK run_checks`; no exit. Add `float_011` (base 0.11): `FAIL floor_fit: 1 (`, the line `  float_011 floating 0.110 m`, the camera line still printed, last line `FAIL run_checks: floor_fit`, exit code 1. `exempt={"floor_fit": ["float_011"]}`: passes. `exempt={"floor_fit": ["no_such"]}`: prints `WARN exempt floor_fit: no object named no_such`. `exempt={"florr_fit": []}`: `ValueError` and no `OK`/`FAIL` line. `floors=()`: `SKIP floor_fit: no floors given`. `floors=("nope",)`: the WARN line and `SKIP floor_fit: none of the floors exists`. Clean scene plus a mannequin: still `OK run_checks`. 25 floating boxes: 20 hit lines, then `  ... and 5 more`. A box moved to float by setting `location` with no view-layer update is still reported. A plan camera: `SKIP camera: orthographic camera`.
  - `bh.EYE_HEIGHT == 1.5875`.
- T18 `tests/bl_rev6_perf.py`, its own step: the 1,925-object synthetic scene from the verification (seeded `random.Random(1)`), each of the six checks timed; passes when their total is under 60 s, and prints each time. Guards against a pair loop without the bounding-box prefilter.
- T19 `run_tests.sh`: add `wall_gaps.py` to the required files and `test_wall_gaps.py` and the two Blender steps to the suite; each template view's log must have the line `^OK run_checks$` before `DONE`. Negative template step: `tests/seed_template.py`, copied beside the template copy, imports `scene_template`, wraps `build` to add `box("float_test", 2.0, 2.4, 3.0, 3.4, 0.11, 0.9)`, and calls `main()` with `--view persp`; the run must exit non-zero, its log must have `^FAIL run_checks: floor_fit$`, and it must have no `^DONE` line.
- T20 `test_api_doc.py` also checks `wall_gaps`.
- Mutation checks (report each): remove the `wall_gaps` corner rule; make `flipped_check` read world coordinates; drop the walls float-only rule; use `Scene.ray_cast` in `camera_check`; drop the vertex test in `clearance_check`; drop the figure skip in `run_checks`; drop the negative-determinant normal fix in `coplanar_check`; stop `run_checks` after the first failure. Each must fail at least one of T16 to T19.

### Evals

Fresh subagents read `SKILL.md` by absolute path, not through the Skill tool; synthetic data only.
- E1: "A 12 x 16 ft room with a 4 5/16 in step to a raised landing and a straight stair of 7 risers up to a floor 9 ft above; render an eye-level preview from the room." Pass: `set_units("ft")`, `run_checks` with every floor named and one path per tread, every hit fixed or exempted with a reason, the camera at the floor plus `EYE_HEIGHT / U`.
- E2: a synthetic 150-line legacy build script (its own `box()`, feet, no checks) with a floating panel, a missing wall corner, and a guard across a tread. Prompt: "The renders show odd gaps; add the skill's checks and fix what they find." Pass: the wiring above before the render call with `unit=0.3048`, all three defects fixed, no prefix exemptions.

### Order of work, and how to continue if interrupted

R22 and T16 first (plain Python), then R23 to R29 with T17, then R30 and R31 with T19, then T18 and T20, then docs D5 to D12, then evals. Each finished item is ticked in skill `docs/ISSUES.md` under Revision 6; a fresh session reads that line, this section, and `git log` on `rev6-phantom-checks`.
