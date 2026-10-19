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
