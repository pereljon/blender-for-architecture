# API reference

One line per public function, from the scripts' signatures and docstrings. Check a signature here before calling it.

## Contents
- Conventions
- VIEWS entries
- Pose format
- bhelpers.py, mannequin.py, checks.py, wall_gaps.py, sheets.py
- Command-line scripts

## Conventions

- Every length argument is in project units. `set_units("ft")` makes them feet; the default is metres.
- Arguments that default to `None` resolve to a metric value at call time, so they stay correct in feet.
- Colors are linear RGB tuples. Convert hex with `srgb()`.
- Import in a scene script after adding `blender/lib` to `sys.path`: `from bhelpers import *`.

## VIEWS entries

- Perspective: `dict(loc, target, lens=24, aspect=0.625, shift_x=0, shift_y=0, hide=())`.
- A perspective entry may carry `interior` (`True`, `False`, or absent for auto). The scene script reads it and passes it to `run_checks`; `add_camera` ignores it.
- Plan: `dict(plan=True, center=(x, y), width, cut, floor_z=0, aspect=1.0, hide=(), drop=(), keep=())`.
- `width` is the plan's span on its longer side. Every plan entry runs `plan_cut` and `plan_light`; `drop` and `keep` are optional.
- `hide` in a perspective entry hides objects from the camera only; in a plan entry it removes them from the render.

## Pose format

Keys of a `mannequin` pose, in project units. `EXAMPLE_POSE` is in metres.

- `root` (x, y) pelvis position; `face` (fx, fy) facing direction.
- `pz` pelvis height when seated, or `None` when standing.
- `bend` torso lean forward in degrees; `head` head tilt in degrees, positive is down.
- `raise_r` optional right-shoulder lift.
- `ankles` ((x, y), (x, y)); `rw` and `lw` ((wrist xyz), (fingertip xyz)).
- `rpole` and `lpole` elbow bend directions.
- `floor_z` optional floor height under the feet, default 0.

## bhelpers.py

- `U` = `1.0`
- `EYE_HEIGHT` = `1.5875`: eye height in metres of a 5'-7" viewer (5'-2 1/2"). Place an eye-level camera at the floor plus `EYE_HEIGHT / U`.
- `set_units(u)`: Set metres per project unit: "m", "ft" or a number.
- `clear_scene()`: Remove every object, mesh, material, light, camera and curve, and forget the tile pieces.
- `new_obj(name, mesh, mat=None)`: Link a mesh object to the scene, with an optional material.
- `box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0, seg=2)`: Axis-aligned box from its extents; optional bevel modifier with smooth shading.
- `slab(name, pts, ztop, thick, mat=None, zbot=None)`: XY polygon extruded down from ztop to ztop - thick, or to zbot (sloped floors, counters).
- `prism(name, pts, z0, z1, mat=None)`: Vertical prism over a polygon: angled walls, bays, odd-shaped slabs.
- `seg(name, a, b, t, z0, z1, mat=None)`: Wall segment of thickness t on the centre line a-b, any angle.
- `cyl(name, x, y, z0, z1, r, mat=None, n=32, rot_rad=None)`: Vertical cylinder from z0 to z1; rot_rad=(rx, ry, rz) Euler angles in radians turn it about its centre.
- `cyl_x(name, x0, x1, y, z, r, mat=None, n=32)`: Cylinder along X (bars, rails).
- `cyl_y(name, y0, y1, x, z, r, mat=None, n=32)`: Cylinder along Y.
- `sphere(name, x, y, z, r, mat=None, scale=(1, 1, 1))`: UV sphere (ellipsoid with scale) centred at x, y, z.
- `tube(name, pts, r, mat=None)`: Round tube along a NURBS path through pts (spouts, levers, pipes). Caps are closed; open ends render as holes.
- `polyline(name, pts, z, width, mat=None)`: Flat line through (x, y) points at height z, as a bevelled curve: door swings and break lines in plan views.
- `lathe(name, profile, mat=None, n=64, plan=None)`: Revolve an (r, z) profile around local Z (basins, bowls, knobs); place it with place().
- `place(ob, x, y, z, rot_deg=0.0)`: Set an object's location and its Z rotation in degrees.
- `placed(build, tx, ty, tz, rot)`: Run build(), which models an element around the origin, then move the new objects to (tx, ty, tz) turned rot degrees.
- `cut_holes(prefixes, holes, solver='EXACT')`: Boolean-difference each hole (x0, x1, y0, y1, z0, z1) out of every object whose name starts with prefixes.
- `look(ob, loc, target)`: Place an object (camera, spot light) at loc pointing at target.
- `person(mat, x, y, h=None)`: Scale figure: a cylinder body and a sphere head, h tall in project units (default 1.75 m).
- `srgb(hexstr)`: Hex sRGB colour ("#c8b49a" or "c8b49a") to a linear RGB tuple for Principled inputs.
- `sock(node, name, kind=None)`: Input socket by name and type; needed for nodes like Mix that have several sockets with the same name.
- `osock(node, name, kind=None)`: Output socket by name and type (see sock).
- `principled(name, color, rough=0.5, metal=0.0, **kw)`: Principled BSDF material. Extra inputs by socket name, e.g. **{"Transmission Weight": 1.0, "IOR": 1.45}.
- `emission(name, color, strength)`: Emission-only material: downlight discs, LED strips, screens, plan-view overlay marks.
- `wood_material(name, axis='Z', dark=(0.22, 0.11, 0.045), light=(0.3, 0.165, 0.07), rough=0.45)`: Procedural wood grain (wave bands and a colour ramp) on object coordinates; grain runs across axis.
- `planks(name, color, plank_w=None, plank_l=None)`: Plank floor: brick-texture boards (plank_w by plank_l) with per-board tone, grain and bumped seams.
- `stone_tile(name, color, tile=None, tile_h=None, plane='xy', joint=None, rough=0.7)`: Stone or porcelain tile in stack bond (tile by tile_h, joint = full joint width): per-tile tone, mottling, bumped joints.
- `fabric(name, color, scale=180.0, strength=0.35)`: Woven or boucle textile: fine noise bump on a matte base.
- `image_tile_material(name, path, mult=(1, 1, 1), rough=0.5, bump=0.1, spec=0.5)`: One photo or scan per tile piece through the piece's UVs (each tile shows the whole image), tinted by mult.
- `projected_tile_material(name, path, size, rough=0.5, bump=0.1)`: Image box-projected on object coordinates, one image per size (scalar or (x, y, z)); no UVs needed.
- `Face(origin, uax, vax, nax)`; methods: p: A tiled surface: p(u, v, d) = origin + u*uax + v*vax + d*nax (nax points into the room), in project units.
- `tile_poly(name, pts, uvs, nvec, mat, thick=None, bevel=None)`: Tile piece: front face pts (3D) with UVs, extruded thick behind it (against nvec); a tiny bevel reads as grout.
- `PIECES` = `[]`
- `face_piece(name, face, poly_uv, origin, mat, flips, tile=None, rot=False, thick=None)`: One (possibly cut) tile piece. poly_uv: polygon in face (u, v); origin: (u, v) of the full tile's corner.
- `u_pieces(u0, u1, start, sign, length=None, joint=None)`: Columns of full tiles laid from start in direction sign (+1/-1), clipped to [u0, u1]: (lo, hi, tile_start).
- `subtract(r, h)`: Rectangle r minus hole h, both (a0, a1, b0, b1): up to four rectangles (niches, windows, cut-outs).
- `tile_wall(tag, face, u0, u1, start, sign, rows, mat, rnd, holes=(), tile=None, joint=None)`: Stacked tiles on a Face between u0 and u1, laid from start (a full tile at the most visible corner).
- `export_pieces(path)`: Write PIECES as JSON {"pieces": [...]}, polygons in project units.
- `load_plan(path)`: Walls JSON written by extract_plan.py: {"walls": [{kind, x0, x1, y0, y1}], "doors": [...], "leaves": [...]}.
- `fix_walls(walls, wall_fixes=(), wall_replace=(), tol=None)`: Apply WALL_REPLACE, then WALL_FIXES, to the extracted walls. Pieces match within tol (default 0.06 m).
- `extra_walls(rows)`: Wall dicts, as load_plan returns them, from EXTRA_WALLS tuples (kind, x0, x1, y0, y1).
- `cut_openings(walls, holes, min_piece=None)`: Trim wall rectangles where they run into an opening (jamb fragments left by the extraction).
- `walls_from_plan(walls, z0, z1, mat=None, prefix='wall_')`: One box per wall dict from load_plan, named prefix + index. Returns the objects.
- `door_swings(doors, mat, z=None, width=None, skip=None)`: Door swing arcs from the extracted plan, drawn flat on the floor for plan views.
- `room_fill_lights(rooms, ceil, w_per_m2=24.0, color=(1.0, 0.93, 0.84))`: One hidden area light per room under the ceiling; energy is w_per_m2 times the room area in square metres.
- `opening_light(name, x0, x1, y0, y1, z, energy=900, color=(0.9, 0.95, 1.0))`: Daylight through a skylight or other glazed opening: the sun does not pass glass solids, so the opening emits.
- `sun(elevation_deg, azimuth_deg, plan_north_deg=0.0, energy=3.0)`: Sun from a solar position (elevation, azimuth clockwise from true north).
- `downlights(mat, rect, ceil, nx=3, ny=2, watts=45, tag='room', trim_r=None)`: Recessed downlights over rect (x0, x1, y0, y1): an emissive trim in the ceiling plane plus a spot light below each.
- `setup_cycles(samples, gpu=True, exposure=0.0, look='AgX - Medium High Contrast', max_bounces=10, glossy_bounces=6, transmission_bounces=10, sky=(0.55, 0.7, 0.95), sky_strength=1.0)`: Cycles with adaptive sampling, denoising, AgX and a sky world. Does not set resolution or output.
- `set_resolution(res, aspect=0.625)`: Width res pixels, height round(res * aspect), at 100 percent.
- `new_camera(name='cam', clip_start=None)`: Add a camera object, make it the scene camera and return it; clip_start defaults to 0.05 m.
- `perspective_camera(loc, target, lens=24, sensor=36, shift_x=0.0, shift_y=0.0)`: Camera at loc aimed at target; shift frames a level camera. Keep it outside every object after moving furniture.
- `plan_camera(center, width, cut, floor_z=0.0, height=None)`: Ortho camera looking straight down, height above floor_z (default 12 m). The near clip sits at the plan cut.
- `add_camera(view, res)`: Camera from a VIEWS entry, with resolution set from res and the entry's aspect.
- `plan_cut(cut, floor_z=0.0, hide=(), drop=(), keep=())`: Plan-view object rules by name prefix, with cut measured above floor_z.
- `plan_light(center, floor_z=0.0, height=None, size=None, w_per_m2=6.0, extent=None)`: One even overhead area light for plan views, height above floor_z, and a dim grey world.
- `project_points(points)`: Points in project units to pixel (x, y) in the current camera, for PIL labels and rulers added after the render.
- `render(out)`: Render the scene camera to the PNG at out (made absolute), then print DONE <out>.
- `dotted_square(name, px, py, half, z, mat, dash=None, pitch=None, w=None)`: Dotted outline of a square (an existing post) centred at px, py; half = half the side.
- `dashed_path(name, pts, z, mat, dash=None, gap=None, w=None)`: Dashed line along a polyline (an outline of the floor above). Close it by repeating the first point.
- `dotted_rect(name, x0, x1, y0, y1, z, mat, dash=None, pitch=None, w=None)`: Dotted outline of a rectangle (a wall to be removed).

## mannequin.py

- `ik(a, t, l1, l2, pole)`: Two-bone IK: joint (elbow/knee) and end point for root a reaching t; the joint bends toward pole.
- `EXAMPLE_POSE` = `dict(root=(1.0, 0.75), face=(1, 0), pz=None, bend=18, head=2`
- `mannequin(pose, height=None, mat=None, prefix='man_')`: Neutral clay figure of the given height in pose (see EXAMPLE_POSE); object names start with prefix.

## checks.py

Lengths in the checks are world metres, except `paths` in `run_checks` and `clearance_check`, which take project units.

- `clash_check(a_prefixes=('man_',), b_prefixes=None, ignore=())`: Pairs (a_name, b_name) where an a* object overlaps a b* object, or has a vertex inside it.
- `coplanar_check(prefixes=None, tol=0.0005, min_area=1e-06, skip=())`: Pairs (name1, name2) of mesh objects with faces on one plane (within tol metres) whose in-plane extents overlap; skip holds exact object names to leave out.
- `flipped_check(skip=())`: Pairs (name, "inside-out" or "mixed") of closed mesh objects whose faces turn the wrong way. Sorted by name.
- `wall_gap_check(prefixes=('wall_',), floors=(), gap=0.3, opening=2.5, touch=0.001, tol=0.025, skip=(), full_height=())`: Hits (name_i, name_j, kind, length_m) for walls that almost meet (kind "gap" or "corner") or frame a door-sized opening with no header ("no-header") or no floor ("no-floor"). full_height holds wall-name pairs whose opening runs to the ceiling.
- `floor_fit_check(floors, walls=('wall_',), tol=0.025, hang=0.3, skip=())`: Pairs (name, d) of mesh objects that float above (d > 0) or sink into (d < 0, or None for more than hang) the floor under their centre. floors holds exact object names.
- `camera_check(interior=None, rays=160, skip=())`: Items (kind, name, count, (x0, y0, x1, y1)) for faces the perspective scene camera sees from behind ("backface") and for sky in an interior view ("escape"). The box is in pixels.
- `clearance_check(paths, headroom=2.032, unit=None, tol=0.005, skip=())`: Items (path, name, headroom_m) for objects inside the walking box over each path. paths maps a name to (x0, x1, y0, y1, z) in project units.
- `fail_on(hits, label)`: Print OK <label>, or FAIL <label>: <hits> and exit with status 1 when hits is not empty.
- `run_checks(floors=(), walls=('wall_',), paths=None, figure=('man_',), exempt=None, interior=None, unit=None, rays=160)`: Run the six checks over the whole scene right before a render, print OK, FAIL or SKIP for each, and exit 1 when any failed. exempt is {check: [exact object names]} for coplanar, flipped, wall_gaps, floor_fit, camera, and clearance, and {"openings": [(wall, wall), ...]} (a list of pairs) for openings meant to run to the ceiling.

## wall_gaps.py

Plain Python (no Blender). Rects are `(x0, x1, y0, y1)`, `(x0, x1, y0, y1, z0, z1)`, or `load_plan` wall dicts. `unit` is metres per rect unit; `gap`, `opening`, and `touch` are metres.

- `wall_gaps(rects, unit=1.0, gap=0.3, touch=0.001)`: Hits (i, j, kind, length_m) between rects i < j that almost meet: kind "gap" (apart by up to gap) or "corner" (touching, with the junction left unfilled). A third rect that fills the space clears the hit.
- `wall_openings(rects, unit=1.0, gap=0.3, opening=2.5, touch=0.001)`: Door-sized openings (i, j, width_m, (x0, x1, y0, y1)) between in-line rects i < j; the box is in metres.

## sheets.py

- `FONTS` = `('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Li`
- `PAGE` = `(3300, 2340)`
- `S` = `PAGE[0] / 420`
- `font(size, bold=False)`: Cached font: Arial (Arial Bold when bold), then Helvetica, then the Pillow default; never raises.
- `fmt(v, decimal=',')`: Number to a string with one decimal and no trailing zero decimal; decimal is the separator.
- `check_rounding(values, step)`: Values that are not multiples of step (relative tolerance 1e-9). Sheet generators assert this is empty.
- `Sheet(title, subtitle, page_no, total, footer, page_label='Sheet {} of {}')`; methods: text, paragraph, save: A3 sheet with title, subtitle, page number and footer. Labels are parameters so any language works.
- `Draw(sh, ox, oy, scale)`; methods: P, rect, line, text, hdim, vdim: A scaled drawing on a Sheet: origin at sheet pixel (ox, oy), coordinates in mm, y up. scale 20 = 1:20.
- `save_pdf(images, path, resolution=200)`: Join page images, PIL images or PNG file paths, into one multi-page PDF.
- `items_from_pieces(path, unit=1.0)`: Pieces from an export_pieces JSON as pack() items dict(id, w, h) in metres; unit is metres per project unit.
- `pack(items, tw=1.2, th=0.6, kerf=0.003)`: Pack pieces dict(id, w, h) (finished size, metres) onto tw x th stock with a kerf saw cut between pieces.

`mm` is an alias of `fmt`. `INK` and `DIM` are the line and dimension colors.

## Command-line scripts

- `uvx --with pillow python -I lib/compose.py OUT.jpg [--title=TEXT] [--width=PX] ITEM ...`: items are `Label=path.png`, `Label=-` (blank cell), `|` (end of row), `#Heading`.
- `uvx --with pillow python -I lib/annotate_plan.py IN.png OUT.png CALLOUTS.json`: CALLOUTS.json is `{"center": [x, y], "width": w, "callouts": [{"x", "y", "label", "above", "r"}]}`. The default ring radius is in pixels; `r` is in project units.
- `uvx --with pymupdf python -I lib/extract_plan.py CONFIG.json`: see `plan_config.example.json` and [plan-input.md](plan-input.md).
- `uvx --with pillow python -I lib/sheets.py`: runs the packing self-test.
