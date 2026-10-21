"""Blender test: Revision 6 checks (T17, T18): wall_gap_check, flipped_check, floor_fit_check, camera_check,
clearance_check, coplanar_check changes, run_checks, EYE_HEIGHT, and a timing case on a large scene."""
import contextlib
import io
import os
import random
import re
import sys
import time
import traceback

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, finish

import bhelpers as bh
import checks as ck
import mannequin as mq

FT = 0.3048


def reset(unit="m"):
    bh.set_units(unit)
    bh.clear_scene()


def upd():
    bpy.context.view_layer.update()


def cap(fn, *a, **kw):
    """Run fn and return (result, stdout lines)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = fn(*a, **kw)
    return res, buf.getvalue().splitlines()


def _eq(x, y, tol):
    if isinstance(y, float):
        return isinstance(x, (int, float)) and abs(x - y) <= tol
    if isinstance(y, tuple):
        return isinstance(x, tuple) and len(x) == len(y) and all(_eq(a, b, tol) for a, b in zip(x, y))
    return x == y


def same(got, want, tol=1e-6):
    return len(got) == len(want) and all(_eq(g, w, tol) for g, w in zip(got, want))


def expect(label, got, want, tol=1e-6):
    check(same(got, want, tol), f"{label}: want {want}, got {got}")


def edit_mesh(ob, fn):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    fn(bm)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def signed_volume_world(ob):
    me = ob.data
    m = ob.matrix_world
    vol = 0.0
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        a, b, c = (m @ me.vertices[i].co for i in t.vertices)
        vol += a.dot(b.cross(c)) / 6
    return vol


def xz_slab(name, prof, y0, y1):
    """Slab from an x-z profile extruded along y, flipped when needed so its signed volume is negative."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in prof]
    b = [bm.verts.new((x, y1, z)) for x, z in prof]
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([a[i], a[j], b[j], b[i]])
    ob = bh.new_obj(name, bh._to_mesh(name, bm))
    upd()
    if signed_volume_world(ob) > 0:
        ob.data.flip_normals()
    return ob


def box_ft(name, x0, x1, y0, y1, z0, z1):
    """Box with extents given in metres, in a scene whose unit is feet."""
    return bh.box(name, *(v / FT for v in (x0, x1, y0, y1, z0, z1)))


# ---------------------------------------------------------------- wall_gap_check
def t_wall_gaps():
    def two(wb=(3.9, 4.0, 0.15, 3, 0, 2.6), nb="wall_b", unit="m"):
        reset(unit)
        mk = box_ft if unit == "ft" else bh.box
        mk("wall_a", 0, 4, 0, 0.1, 0, 2.6)
        mk(nb, *wb)
        upd()

    two()
    expect("gap", ck.wall_gap_check(), [("wall_a", "wall_b", "gap", 0.05)])
    two(unit="ft")
    expect("gap in feet", ck.wall_gap_check(), [("wall_a", "wall_b", "gap", 0.05)])
    two(wb=(3.9, 4.0, 0.15, 3, 3, 5.6))
    expect("other level", ck.wall_gap_check(), [])
    two(nb="shelf_b")
    expect("not a wall prefix", ck.wall_gap_check(), [])
    two()
    expect("skip", ck.wall_gap_check(skip=("wall_b",)), [])
    expect("prefixes", ck.wall_gap_check(prefixes=("shelf_",)), [])

    two()
    bh.cut_holes("wall_a", [(1, 2, -0.2, 0.3, -0.05, 2.1)])
    upd()
    expect("a door cut into a wall changes nothing", ck.wall_gap_check(), [("wall_a", "wall_b", "gap", 0.05)])

    reset()
    bh.box("wall_a", 0, 4, 0, 0.1, 0, 2.6)
    bh.seg("wall_angle", (6, 0), (6.95, 0.55), 0.1, 0, 2.6)
    upd()
    res, lines = cap(ck.wall_gap_check)
    expect("angled wall is not checked", res, [])
    note = [ln for ln in lines if ln.startswith("NOTE wall_gaps:")]
    check(len(note) == 1 and "wall_angle" in note[0], f"NOTE line names the angled wall: {lines}")

    reset()
    for n, r in (("wall_1", (0, 2, 0, 0.1)), ("wall_sq", (2, 2.1, 0, 0.1)), ("wall_3", (2.1, 4, 0, 0.1)),
                 ("wall_stem", (2, 2.1, 0.1, 3))):
        bh.box(n, *r, 0, 2.6)
    upd()
    expect("T junction filled by its own square", ck.wall_gap_check(), [])


def opening_scene(header=None, ceiling=True, floors="one", z0=0.0):
    reset()
    if floors == "one":
        bh.box("floor", -3, 5, -3, 3, -0.1, 0)
    elif floors == "split":
        bh.box("floor", -3, 2.2, -3, 3, -0.1, 0)
        bh.box("floor_r", 2.7, 5, -3, 3, -0.1, 0)
    bh.box("wall_a", 0, 2, 0, 0.1, z0, 2.6)
    bh.box("wall_b", 2.9, 4, 0, 0.1, z0, 2.6)
    if ceiling:
        bh.box("ceiling", -3, 5, -3, 3, 2.6, 2.7)
    if header:
        bh.box(header, 2, 2.9, 0, 0.1, 2.1, 2.6)
    upd()


def t_openings():
    nh = [("wall_a", "wall_b", "no-header", 0.9)]
    nf = [("wall_a", "wall_b", "no-floor", 0.9)]
    opening_scene()
    expect("opening without header", ck.wall_gap_check(floors=("floor",)), nh)
    opening_scene(header="head_1")
    expect("header box", ck.wall_gap_check(floors=("floor",)), [])
    opening_scene(header="wall_head")
    expect("header named as a wall", ck.wall_gap_check(floors=("floor",)), [])
    opening_scene(ceiling=False)
    expect("no ceiling, no header", ck.wall_gap_check(floors=("floor",)), nh)
    opening_scene(header="head_1", floors="split")
    expect("floor split across the opening", ck.wall_gap_check(floors=("floor", "floor_r")), nf)
    bh.box("ground", -3, 5, -3, 3, -3.1, -3)
    upd()
    expect("slab one storey down", ck.wall_gap_check(floors=("floor", "floor_r", "ground")), nf)
    expect("no floors given", ck.wall_gap_check(), [])
    opening_scene(header="head_1", z0=-0.1)
    expect("walls run down through the slab", ck.wall_gap_check(floors=("floor",)), [])
    opening_scene()
    expect("full_height pair in the other order", ck.wall_gap_check(floors=("floor",),
                                                                    full_height=(("wall_b", "wall_a"),)), [])


# ---------------------------------------------------------------- flipped_check
def t_flipped():
    reset()
    bh.box("ok", 0, 1, 0, 1, 0, 1)
    bh.box("inside_out", 2, 3, 0, 1, 0, 1).data.flip_normals()
    mixed = bh.box("mixed", 4, 5, 0, 1, 0, 1)
    edit_mesh(mixed, lambda bm: [bm.faces.ensure_lookup_table(), bm.faces[0].normal_flip()])
    open_box = bh.box("open_box", 6, 7, 0, 1, 0, 1)
    edit_mesh(open_box, lambda bm: bmesh.ops.delete(
        bm, geom=[max(bm.faces, key=lambda f: f.calc_center_median().z)], context="FACES_ONLY"))
    bh.box("mirrored", 8, 9, 0, 1, 0, 1).scale = (-1, 1, 1)
    bh.cyl("cyl_ok", 10, 0, 0, 1, 0.3)
    bh.sphere("sphere_ok", 12, 0, 0.5, 0.4)
    bh.lathe("lathe_up", [(0, 0), (0.3, 0.2), (0.3, 0.6), (0, 0.8)])
    bh.lathe("lathe_down", [(0, 0.8), (0.3, 0.6), (0.3, 0.2), (0, 0)])
    hid = bh.box("hidden_io", 14, 15, 0, 1, 0, 1)
    hid.data.flip_normals()
    hid.hide_render = True
    upd()
    want = [("inside_out", "inside-out"), ("mixed", "mixed")]
    expect("flipped_check", ck.flipped_check(), want)
    expect("skip", ck.flipped_check(skip=("mixed",)), want[:1])


# ---------------------------------------------------------------- floor_fit_check
def t_floor_fit():
    reset()
    bh.box("floor", -5, 5, -5, 5, -0.5, 0)
    bh.box("up_floor", 0, 5, 0, 5, 0, 0.11)
    for n, r in (("on_floor", (-4, -3, -4, -3, 0, 1)), ("sunk5mm", (-2, -1, -4, -3, -0.005, 1)),
                 ("float_011", (-4, -3, -2, -1, 0.11, 1)), ("buried_011", (1, 2, 1, 2, 0, 1)),
                 ("deep_sunk", (-4, -3, 2, 3, -0.4, 0.5)), ("shelf", (-2, -1, 3, 4, 1.2, 1.6)),
                 ("on_upper", (3, 4, 3, 4, 0.11, 1)), ("outside", (6, 7, 0, 1, 0.2, 1)),
                 ("float_002", (-4, -3, 0, 1, 0.02, 1)), ("float_003", (-2, -1, 0, 1, 0.03, 1)),
                 ("wall_deep", (2, 2.1, 4, 4.1, 0, 2.6)), ("wall_float", (-4, -3.9, 4, 4.1, 0.05, 2.6))):
        bh.box(n, *r)
    upd()
    want = [("buried_011", -0.11), ("deep_sunk", None), ("float_003", 0.03), ("float_011", 0.11),
            ("wall_float", 0.05)]
    expect("floor_fit_check", ck.floor_fit_check(("floor", "up_floor")), want)
    expect("skip", ck.floor_fit_check(("floor", "up_floor"), skip=("float_011",)), [w for w in want if w[0] != "float_011"])


def t_floor_orientation():
    def scene(kind):
        reset()
        if kind == "slab":
            xz_slab("floor", [(-5, -0.5), (-5, 0), (5, 0), (5, -0.5)], -5, 5)
        else:
            f = bh.box("floor", -5, 5, -5, 5, -0.5, 0)
            if kind == "mirrored":
                f.scale = (-1, 1, 1)
            elif kind == "flipped":
                f.data.flip_normals()
        bh.box("on_floor", 0, 1, 0, 1, 0, 1)
        bh.box("float_011", 2, 3, 2, 3, 0.11, 1)
        upd()

    for kind in ("box", "mirrored", "flipped", "slab"):
        scene(kind)
        if kind == "slab":
            check(signed_volume_world(bpy.data.objects["floor"]) < 0, "the x-z slab fixture has negative volume")
        expect(f"floor orientation {kind}", ck.floor_fit_check(("floor",)), [("float_011", 0.11)])


def t_support():
    reset()
    bh.box("floor", -5, 5, -5, 5, -0.5, 0)
    for n, r in (("rug", (0, 2, 0, 2, 0, 0.03)), ("chair", (0.5, 1, 0.5, 1, 0.03, 0.9)),
                 ("plinth", (3, 4, 0, 1, 0, 0.1)), ("vase", (3.3, 3.6, 0.3, 0.6, 0.1, 0.5)),
                 ("tread_0", (0, 1, -2, -1.75, 0, 0.18)), ("nosing_0", (0, 1, -2.0, -1.96, 0.17, 0.2)),
                 ("bed_frame", (-3, -1, 0, 2, 0, 0.25)), ("mattress", (-3, -1, 0, 2, 0.25, 0.45)),
                 ("panel_old", (2, 2.4, 3, 3.4, 0.11, 0.9)), ("led_riser", (0.1, 0.9, -2.01, -1.99, 0.06, 0.08))):
        bh.box(n, *r)
    upd()
    expect("support test", ck.floor_fit_check(("floor",)), [("led_riser", 0.06), ("panel_old", 0.11)])


# ---------------------------------------------------------------- camera_check
def corners_px(pts):
    px = bh.project_points(pts)
    xs, ys = [p[0] for p in px], [p[1] for p in px]
    return min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1


def open_box_scene(neg=False, blocker=False):
    reset()
    bh.box("floor", -5, 5, -5, 5, -0.1, 0)
    ob = bh.box("open_box", -0.5, 0.5, -0.5, 0.5, 0, 1)
    edit_mesh(ob, lambda bm: bmesh.ops.delete(
        bm, geom=[max(bm.faces, key=lambda f: f.calc_center_median().z)], context="FACES_ONLY"))
    if neg:
        ob.scale = (-1, 1, 1)
    if blocker:
        bh.box("blocker", -0.3, 0.3, -1.6, -1.4, 1.9, 2.1)
    bh.set_resolution(160)
    bh.perspective_camera((0, -3, 3), (0, 0, 0.5), lens=24)
    upd()


def t_camera_backface():
    open_box_scene()
    res, lines = cap(ck.camera_check)
    check(len(res) == 1 and res[0][0] == "backface" and res[0][1] == "open_box" and res[0][2] > 0,
          f"open box gives one backface item: {res}")
    n0 = res[0][2] if res else 0
    if res:
        x0, y0, x1, y1 = corners_px([(-.5, -.5, 1), (.5, -.5, 1), (.5, .5, 1), (-.5, .5, 1)])
        b = res[0][3]
        check(b[0] >= x0 and b[1] >= y0 and b[2] <= x1 and b[3] <= y1, f"pixel box {b} lies in the opening {(x0, y0, x1, y1)}")
    check("NOTE camera: exterior view, escapes not checked" in lines, f"exterior NOTE printed: {lines}")
    expect("skip", ck.camera_check(skip=("open_box",)), [])
    r320 = ck.camera_check(rays=320)
    check(len(r320) == 1 and r320[0][2] >= 3 * n0, f"320 columns give at least 3x the count: {r320} vs {n0}")

    open_box_scene(blocker=True)
    rb = ck.camera_check()
    check(len(rb) == 1 and rb[0][2] < n0, f"a blocker lowers the count: {rb} vs {n0}")
    bpy.data.objects["blocker"].visible_camera = False
    expect("blocker with visible_camera off", ck.camera_check(), res)

    open_box_scene(neg=True)
    rn = ck.camera_check()
    check(len(rn) == 1 and rn[0][:2] == ("backface", "open_box"), f"mirrored open box still gives the backface: {rn}")

    reset()
    bh.box("floor", -5, 5, -5, 5, -0.1, 0)
    bh.box("closed_neg", -0.5, 0.5, -0.5, 0.5, 0, 1).scale = (-1, 1, 1)
    bh.set_resolution(160)
    bh.perspective_camera((0, -3, 3), (0, 0, 0.5), lens=24)
    upd()
    expect("closed mirrored box", ck.camera_check(), [])


def room_scene(ceil_b_x0=0.6):
    reset()
    bh.box("floor", -2, 2, -2, 2, -0.1, 0)
    for n, r in (("wall_s", (-2, 2, -2, -1.9)), ("wall_n", (-2, 2, 1.9, 2)),
                 ("wall_w", (-2, -1.9, -1.9, 1.9)), ("wall_e", (1.9, 2, -1.9, 1.9))):
        bh.box(n, *r, 0, 2.5)
    bh.box("ceil_a", -2, 0, -2, 2, 2.5, 2.6)
    bh.box("ceil_b", ceil_b_x0, 2, -2, 2, 2.5, 2.6)
    bh.set_resolution(160)
    bh.perspective_camera((-1.5, -1.5, 1.6), (1, 1, 2.3), lens=18)
    upd()


def t_camera_escape():
    room_scene()
    res = ck.camera_check()
    check(len(res) == 1 and res[0][0] == "escape" and res[0][1] is None and res[0][2] > 0, f"hole gives one escape: {res}")
    expect("hole with interior=False", ck.camera_check(interior=False), [])
    bpy.data.objects["ceil_a"].hide_render = True
    res, lines = cap(ck.camera_check)
    expect("ceil_a hidden: exterior", res, [])
    check("NOTE camera: exterior view, escapes not checked" in lines, f"exterior NOTE printed: {lines}")
    res = ck.camera_check(interior=True)
    check(any(h[0] == "escape" for h in res), f"interior=True reports escapes: {res}")
    room_scene(ceil_b_x0=0.0)
    expect("closed ceiling", ck.camera_check(), [])
    room_scene()
    bh.plan_camera((0, 0), 5, 1.2)
    upd()
    expect("plan camera", ck.camera_check(), [])


# ---------------------------------------------------------------- clearance_check
def stair_scene(zb, extra=()):
    reset()
    for i in range(4):
        bh.box(f"stair_{i}", 0, 1, 0.25 * i, 0.25 * (i + 1), 0, 0.18 * (i + 1))
    bh.box("side_l", -0.1, 0, 0, 1, 0, 3)
    bh.box("side_r", 1, 1.1, 0, 1, 0, 3)
    bh.box("slab_above", -1, 2, 0.5, 3, zb, zb + 0.3)
    for n, r in extra:
        bh.box(n, *r)
    upd()
    return {f"t_{i}": (0, 1, 0.25 * i, 0.25 * (i + 1), 0.18 * (i + 1)) for i in range(4)}


def t_clearance():
    paths = stair_scene(2.80)
    expect("clear headroom", ck.clearance_check(paths), [])
    paths = stair_scene(2.60)
    expect("slab too low", ck.clearance_check(paths), [("t_3", "slab_above", 1.88)])
    expect("headroom 1.8", ck.clearance_check(paths, headroom=1.8), [])
    expect("skip", ck.clearance_check(paths, skip=("slab_above",)), [])
    paths = stair_scene(2.80, [("guard_x", (0, 1, 0.5, 0.515, 0.54, 1.454))])
    expect("guard across the tread", ck.clearance_check(paths), [("t_2", "guard_x", None)])
    paths = stair_scene(2.80, [("guard_in", (0.3, 0.4, 0.55, 0.6, 0.7, 1.0))])
    expect("guard inside the box", ck.clearance_check(paths), [("t_2", "guard_in", None)])

    reset("ft")
    d, r = 11 / 12, 7.5 / 12
    for i in range(4):
        bh.box(f"stair_{i}", 0, 3, d * i, d * (i + 1), 0, r * (i + 1))
    bh.box("slab_above", -1, 4, 1.5, 6, 8.8, 9.5)
    upd()
    paths = {f"t_{i}": (0, 3, d * i, d * (i + 1), r * (i + 1)) for i in range(4)}
    expect("feet, unit from bhelpers", ck.clearance_check(paths), [("t_3", "slab_above", 1.92024)])
    bh.set_units("m")
    expect("feet scene, unit passed", ck.clearance_check(paths, unit=FT), [("t_3", "slab_above", 1.92024)])


# ---------------------------------------------------------------- coplanar_check
def t_coplanar():
    reset()
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    bh.box("cp_b", 1, 3, 0.5, 2.5, 0, 1)
    upd()
    expect("skip", ck.coplanar_check(skip=("cp_b",)), [])
    check(len(ck.coplanar_check()) == 1, "without skip the pair is reported")


def t_coplanar_mirrored():
    for sx in (-1, 1):
        reset()
        bh.box("floor", -5, 5, -5, 5, -0.5, 0)
        bh.box("mir", 0, 1, 0, 1, 0, 1).scale = (sx, 1, 1)
        upd()
        expect(f"box with scale ({sx}, 1, 1) on a floor", ck.coplanar_check(), [])


# ---------------------------------------------------------------- run_checks
def clean_room(mannequin=False, thick_floor=0.1):
    reset()
    bh.box("floor", -0.1, 3.1, -0.1, 4.1, -thick_floor, 0)
    bh.box("wall_south", -0.1, 3.1, -0.1, 0, 0, 2.6)
    bh.box("wall_north", -0.1, 3.1, 4, 4.1, 0, 2.6)
    bh.box("wall_west", -0.1, 0, 0, 4, 0, 2.6)
    bh.box("wall_east", 3, 3.1, 0, 4, 0, 2.6)
    bh.box("ceiling", -0.1, 3.1, -0.1, 4.1, 2.6, 2.7)
    bh.box("counter", 1.6, 2.9, 0.1, 0.7, -0.005, 0.9)
    if mannequin:
        mq.mannequin(mq.EXAMPLE_POSE)
    bh.set_resolution(160)
    bh.perspective_camera((2.7, 3.7, 1.5), (1.0, 0.6, 1.0), lens=20)
    upd()


def run(**kw):
    """run_checks output lines and the exit code (None when it returns)."""
    buf = io.StringIO()
    code = None
    with contextlib.redirect_stdout(buf):
        try:
            ck.run_checks(**kw)
        except SystemExit as e:
            code = e.code
    return buf.getvalue().splitlines(), code


def block(lines, check_name):
    """The header line of a check and the indented lines under it."""
    out, on = [], False
    for ln in lines:
        if re.match(rf"^(OK|FAIL|SKIP) {check_name}\b", ln):
            out, on = [ln], True
        elif on and ln.startswith("  "):
            out.append(ln)
        elif on:
            break
    return out


def t_run_clean():
    clean_room()
    lines, code = run(floors=("floor",))
    check(code is None, f"clean scene does not exit: {code}\n{lines}")
    for c in ("coplanar", "flipped", "wall_gaps", "floor_fit", "camera"):
        check(any(re.match(rf"^OK {c} \(\d+\.\d\d s\)$", ln) for ln in lines), f"OK {c} (t s) in {lines}")
    check("SKIP clearance: no paths given" in lines, f"clearance skip line: {lines}")
    check(lines and lines[-1] == "OK run_checks", f"last line OK run_checks: {lines[-3:]}")

    clean_room(mannequin=True)
    lines, code = run(floors=("floor",))
    check(code is None and lines[-1] == "OK run_checks", f"mannequin scene passes (code {code}): {lines}")

    clean_room()
    lines, code = run()
    check("SKIP floor_fit: no floors given" in lines, f"floors=() skip line: {lines}")
    lines, code = run(floors=("nope",))
    check("WARN floors: no object named nope" in lines, f"floors WARN: {lines}")
    check("SKIP floor_fit: none of the floors exists" in lines, f"none-exist skip: {lines}")
    check(code is None and lines[-1] == "OK run_checks", f"still passes (code {code})")

    bh.plan_camera((1.5, 2), 6, 1.2)
    upd()
    lines, code = run(floors=("floor",))
    check("SKIP camera: orthographic camera" in lines, f"plan camera skip: {lines}")
    check(code is None and lines[-1] == "OK run_checks", f"plan camera run passes (code {code})")


def t_run_float():
    clean_room()
    bh.box("float_011", 0.3, 0.6, 1.5, 1.8, 0.11, 0.5)
    upd()
    lines, code = run(floors=("floor",))
    check(code == 1, f"exit code 1, got {code}")
    check(any(ln.startswith("FAIL floor_fit: 1 (") for ln in lines), f"FAIL floor_fit: 1 (: {lines}")
    check("  float_011 floating 0.110 m" in lines, f"hit line: {lines}")
    i = next((k for k, ln in enumerate(lines) if ln.startswith("FAIL floor_fit")), 0)
    check(any(re.match(r"^OK camera \(", ln) for ln in lines[i:]), f"camera still runs after the failure: {lines}")
    check(lines and lines[-1] == "FAIL run_checks: floor_fit", f"last line: {lines[-2:]}")

    lines, code = run(floors=("floor",), exempt={"floor_fit": ["float_011"]})
    check(code is None and lines[-1] == "OK run_checks", f"exempt passes (code {code}): {lines}")
    lines, code = run(floors=("floor",), exempt={"floor_fit": ["float_011", "no_such"]})
    check("WARN exempt floor_fit: no object named no_such" in lines, f"exempt WARN: {lines}")

    buf = io.StringIO()
    raised = None
    with contextlib.redirect_stdout(buf):
        try:
            ck.run_checks(floors=("floor",), exempt={"florr_fit": []})
        except ValueError as e:
            raised = e
        except SystemExit:
            pass
    check(raised is not None, "unknown exempt key raises ValueError")
    out = buf.getvalue().splitlines()
    check(not any(re.match(r"^(OK|FAIL|SKIP) ", ln) for ln in out), f"no check ran before the ValueError: {out}")

    # stale position: a box moved without a view-layer update is still reported
    clean_room()
    mv = bh.box("moved", 0.3, 0.6, 1.5, 1.8, 0, 0.5)
    upd()
    mv.location.z = 0.11
    lines, code = run(floors=("floor",))
    check("  moved floating 0.110 m" in lines, f"moved box is reported: {lines}")

    clean_room()
    for k in range(25):
        bh.box(f"float_{k:02d}", 0.2 + 0.4 * (k % 5), 0.3 + 0.4 * (k % 5), 1.0 + 0.4 * (k // 5),
               1.1 + 0.4 * (k // 5), 0.11, 0.3)
    upd()
    lines, code = run(floors=("floor",))
    blk = block(lines, "floor_fit")
    check(len(blk) == 22 and blk[0].startswith("FAIL floor_fit: 25 (") and blk[-1] == "  ... and 5 more",
          f"25 hits print 20 lines and the remainder: {blk}")


def t_run_formats():
    clean_room(thick_floor=0.5)
    bh.box("float_011", 0.3, 0.6, 1.5, 1.8, 0.11, 0.5)
    bh.box("sunk_a", 2.0, 2.2, 2.0, 2.2, -0.05, 0.3)
    bh.box("sunk_deep", 2.4, 2.6, 2.0, 2.2, -0.4, 0.3)
    bh.box("cp_a", 0.3, 1.0, 1.0, 2.0, 0, 1)
    bh.box("cp_b", 0.6, 1.3, 1.5, 2.5, 0, 1)
    bh.box("inside_out", 0.85, 1.15, 0.45, 0.75, -0.005, 0.6).data.flip_normals()
    bh.box("beam", 0.3, 0.4, 0.3, 0.4, 0.5, 0.9)
    bh.box("guard_in", 2.15, 2.25, 1.15, 1.25, 0.7, 1.0)
    upd()
    paths = {"t0": (0.2, 0.6, 0.2, 0.6, 0.0), "t1": (2.0, 2.6, 1.0, 1.6, 0.0)}
    lines, code = run(floors=("floor",), paths=paths)
    check(code == 1, f"exit 1, got {code}")
    for want in ("  float_011 floating 0.110 m", "  sunk_a sunk 0.050 m", "  sunk_deep sunk more than 0.300 m",
                 "  cp_a cp_b", "  inside_out inside-out", "  t0 beam headroom 0.500 m", "  t1 guard_in inside"):
        check(want in lines, f"line {want!r} in output")
    check(any(re.match(r"^  backface inside_out: \d+ rays at px \d+-\d+, \d+-\d+$", ln) for ln in lines),
          f"backface hit line format: {block(lines, 'camera')}")
    check(any(re.match(r"^FAIL clearance: 2 \(\d+\.\d\d s\)$", ln) for ln in lines), f"FAIL clearance header: {lines}")
    check(lines[-1] == "FAIL run_checks: coplanar, flipped, floor_fit, camera, clearance",
          f"last line lists the failed checks in run order: {lines[-1]}")


def t_run_walls():
    clean_room()
    for old, new in (("wall_south", "w_south"), ("wall_north", "w_north"), ("wall_west", "w_west"),
                     ("wall_east", "w_east")):
        bpy.data.objects[old].name = new
    bpy.data.objects["w_east"].location.x += 0.05
    upd()
    lines, code = run(floors=("floor",), walls=("w_",))
    blk = block(lines, "wall_gaps")
    check(blk and blk[0].startswith("FAIL wall_gaps: 2 ("), f"wall_gaps fails with 2 hits: {blk}")
    corners = sorted(blk[1:])
    check(corners == ["  w_east w_north corner 0.050 m", "  w_east w_south corner 0.050 m"], f"corner lines: {blk}")
    lines, code = run(floors=("floor",))
    blk = block(lines, "wall_gaps")
    check(blk and blk[0].startswith("OK wall_gaps"), f"default walls do not match w_*: {blk}")


def t_run_errors():
    clean_room()
    real = ck.floor_fit_check

    def boom(*a, **kw):
        raise RuntimeError("boom")

    ck.floor_fit_check = boom
    try:
        lines, code = run(floors=("floor",))
    finally:
        ck.floor_fit_check = real
    check("FAIL floor_fit: error RuntimeError: boom" in lines, f"error line: {lines}")
    i = next((k for k, ln in enumerate(lines) if ln.startswith("FAIL floor_fit")), 0)
    check(any(ln.startswith("OK camera") for ln in lines[i:]) and "SKIP clearance: no paths given" in lines[i:],
          f"camera and clearance lines follow the error: {lines}")
    check(code == 1 and lines and lines[-1] == "FAIL run_checks: floor_fit", f"exit 1 and last line (code {code}): {lines[-2:]}")

    clean_room()
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("empty_mesh", bpy.data.meshes.new("empty_mesh")))
    gone = bh.box("gone", 1.0, 1.3, 2.0, 2.3, 0.2, 0.5)
    cutter = bh.box("cut_big", 0.9, 1.4, 1.9, 2.4, 0.1, 0.6)
    cutter.hide_render = True
    m = gone.modifiers.new("d", "BOOLEAN")
    m.operation, m.object, m.solver = "DIFFERENCE", cutter, "EXACT"
    upd()
    lines, code = run(floors=("floor",))
    check(code is None and lines[-1] == "OK run_checks", f"empty meshes are left out (code {code}): {lines}")


def t_run_openings():
    opening_scene()
    lines, code = run(floors=("floor",))
    check("  wall_a wall_b no-header 0.900 m" in lines, f"no-header hit line: {lines}")
    check(any(ln.startswith("FAIL wall_gaps: 1 (") for ln in lines), f"FAIL wall_gaps: 1: {lines}")
    lines, code = run(floors=("floor",), exempt={"openings": [("wall_a", "wall_b")]})
    check(any(ln.startswith("OK wall_gaps") for ln in lines), f"openings exemption: {block(lines, 'wall_gaps')}")
    lines, code = run(floors=("floor",), exempt={"openings": [("wall_a", "no_such")]})
    check("WARN exempt openings: no object named no_such" in lines, f"openings WARN: {lines}")
    opening_scene(header="head_1", floors="split")
    lines, code = run(floors=("floor", "floor_r"))
    check("  wall_a wall_b no-floor 0.900 m" in lines, f"no-floor hit line: {lines}")


def t_misc():
    check(getattr(bh, "EYE_HEIGHT", None) == 1.5875, f"EYE_HEIGHT is 1.5875: {getattr(bh, 'EYE_HEIGHT', None)}")


# ---------------------------------------------------------------- code review fixes (T17 additions)
def open_plane(name, down=False, mirror=False, z=0.0, half=5.0):
    """One-quad open mesh at height z, wound so that its local normal faces down or up, optionally mirrored in x."""
    bm = bmesh.new()
    pts = [(-half, -half, z), (half, -half, z), (half, half, z), (-half, half, z)]
    bm.faces.new([bm.verts.new(v) for v in (pts[::-1] if down else pts)])
    ob = bh.new_obj(name, bh._to_mesh(name, bm))
    if mirror:
        ob.scale = (-1, 1, 1)
    return ob


def plane_floor_scene(down, mirror):
    reset()
    open_plane("floor", down, mirror)
    bh.box("on_floor", 0, 1, 0, 1, 0, 1)
    bh.box("float_011", 2, 3, 2, 3, 0.11, 1)
    upd()


def t_plan_view_openings():
    nh = "  wall_a wall_b no-header 0.900 m"
    nf = "  wall_a wall_b no-floor 0.900 m"
    plan = dict(plan=True, center=(1, 0), width=8, cut=1.2)
    opening_scene(header="head_1")
    bh.add_camera(plan, 160)
    upd()
    lines, code = run(floors=("floor",))
    blk = block(lines, "wall_gaps")
    check(blk and blk[0].startswith("OK wall_gaps"), f"plan view of an opening with a header and ceiling: {blk}")
    opening_scene()
    bh.add_camera(plan, 160)
    upd()
    lines, code = run(floors=("floor",))
    check(nh not in lines, f"a plan view checks floors only, no no-header line: {block(lines, 'wall_gaps')}")
    opening_scene(header="head_1", floors="split")
    bh.add_camera(plan, 160)
    upd()
    lines, code = run(floors=("floor", "floor_r"))
    check(nf in lines, f"a plan view still reports no-floor: {block(lines, 'wall_gaps')}")
    opening_scene()
    bh.perspective_camera((1, -4, 1.5), (2, 0, 1.2), lens=20)
    upd()
    lines, code = run(floors=("floor",))
    check(nh in lines, f"a perspective view still reports a missing header: {block(lines, 'wall_gaps')}")


def t_floor_fit_upper_slab():
    reset()
    bh.box("floor", -3, 3, -3, 3, -0.2, 0)
    bh.box("upper", -3, 3, -3, 3, 2.62, 2.85)
    bh.box("ceiling", -3, 3, -3, 3, 2.6, 2.62)
    bh.box("beam", -1, 1, 0, 0.2, 2.4, 2.6)
    bh.box("pendant", 0.5, 0.7, 1, 1.2, 2.35, 2.6)
    bh.box("float_011", 1.5, 2.0, -2, -1.5, 0.11, 0.6)
    upd()
    expect("objects under an upper slab named in floors", ck.floor_fit_check(("floor", "upper")),
           [("float_011", 0.11)])


def t_floor_open_planes():
    for down, mirror, label in ((True, False, "open plane, normal down"),
                                (True, True, "open plane, normal down, mirrored"),
                                (False, True, "open plane, normal up, mirrored"),
                                (False, False, "open plane, normal up")):
        plane_floor_scene(down, mirror)
        expect(label, ck.floor_fit_check(("floor",)), [("float_011", 0.11)])
    reset()
    f = bh.box("floor", -5, 5, -5, 5, -0.5, 0)
    f.data.flip_normals()
    f.scale = (-1, 1, 1)
    bh.box("on_floor", 0, 1, 0, 1, 0, 1)
    bh.box("float_011", 2, 3, 2, 3, 0.11, 1)
    upd()
    expect("closed floor, mirrored and inside-out", ck.floor_fit_check(("floor",)), [("float_011", 0.11)])


def t_support_variants():
    reset()
    bh.box("floor", -5, 5, -5, 5, -0.5, 0)
    open_plane("rug", down=True, z=0.03, half=2.0)
    bh.box("chair", 0.5, 1, 0.5, 1, 0.03, 0.9)
    upd()
    expect("object resting on an open plane with a downward normal",
           ck.floor_fit_check(("floor",), skip=("rug",)), [])
    reset()
    bh.box("floor", -5, 5, -5, 5, -0.5, 0)
    open_plane("rug", down=False, mirror=True, z=0.03, half=2.0)
    bh.box("chair", 0.5, 1, 0.5, 1, 0.03, 0.9)
    upd()
    expect("object resting on a mirrored open plane", ck.floor_fit_check(("floor",), skip=("rug",)), [])
    reset()
    bh.box("floor", -5, 5, -5, 5, -0.5, 0)
    bh.box("plate", 0, 1, 0, 1, 0.11, 0.115)
    bh.box("cand", 0, 1, 0, 1, 0.115, 0.6)
    upd()
    expect("a down face within 2 tol of the bottom is not a support",
           ck.floor_fit_check(("floor",), skip=("cand",)), [("plate", 0.11)])


def t_wall_heights():
    def pair(ha, hb, ceiling=True):
        reset()
        bh.box("floor", -3, 5, -3, 3, -0.1, 0)
        bh.box("wall_a", 0, 2, 0, 0.1, 0, ha)
        bh.box("wall_b", 2.9, 4, 0, 0.1, 0, hb)
        if ceiling:
            bh.box("ceiling", -3, 5, -3, 3, 2.6, 2.7)
        upd()
        return ck.wall_gap_check(floors=("floor",))

    expect("walls 0.9 m tall under a ceiling", pair(0.9, 0.9), [])
    expect("walls 1.1 m tall under a ceiling", pair(1.1, 1.1), [])
    expect("lower wall 1.9 m, higher 2.4 m", pair(1.9, 2.4), [])
    expect("lower wall 2.1 m, no ceiling", pair(2.1, 2.4, ceiling=False), [("wall_a", "wall_b", "no-header", 0.9)])
    expect("both walls 2.1 m under a ceiling", pair(2.1, 2.1), [("wall_a", "wall_b", "no-header", 0.9)])


def t_run_names_as_strings():
    clean_room()
    bh.box("float_011", 0.3, 0.6, 1.5, 1.8, 0.11, 0.5)
    upd()
    lines, code = run(floors="floor")
    check(code == 1 and "  float_011 floating 0.110 m" in lines, f"floors as a bare string is one name (code {code}): {lines}")
    check(not any(ln.startswith("WARN floors") for ln in lines), f"no WARN for single letters: {lines}")
    lines, code = run(floors=("floor",), exempt={"floor_fit": "float_011"})
    check(code is None and lines[-1] == "OK run_checks", f"exempt as a bare string is one name (code {code}): {lines}")
    check(not any(ln.startswith("WARN") for ln in lines), f"no WARN for single letters: {lines}")
    lines, code = run(floors=("floor",), exempt={"floor_fit": "float_011", "wall_gaps": "wall_south"})
    check(not any(ln.startswith("WARN") for ln in lines), f"two exempt strings: {lines}")


def t_run_unrendered_floors():
    clean_room()
    bpy.data.objects["floor"].hide_render = True
    bh.box("float_011", 0.3, 0.6, 1.5, 1.8, 0.11, 0.5)
    upd()
    lines, code = run(floors=("floor",))
    check("SKIP floor_fit: none of the floors exists" in lines, f"a floor hidden from render does not exist: {lines}")
    check(not any(ln.startswith("OK floor_fit") for ln in lines), f"no OK floor_fit: {lines}")
    clean_room()
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("slab_empty", None))
    bh.box("float_011", 0.3, 0.6, 1.5, 1.8, 0.11, 0.5)
    upd()
    lines, code = run(floors=("slab_empty",))
    check("SKIP floor_fit: none of the floors exists" in lines, f"a floor that is not a mesh does not exist: {lines}")
    check(not any(ln.startswith("OK floor_fit") for ln in lines), f"no OK floor_fit: {lines}")


def t_run_camera_not_a_camera():
    clean_room()
    bpy.context.scene.camera = bpy.data.objects.new("cam_empty", None)
    bpy.context.scene.collection.objects.link(bpy.context.scene.camera)
    upd()
    try:
        lines, code = run(floors=("floor",))
    except Exception as e:
        check(False, f"a non-camera scene.camera raised {type(e).__name__}: {e}")
        return
    check(not any(ln.startswith("OK camera") for ln in lines), f"camera check does not pass: {lines}")
    check(any(re.match(r"^(SKIP|FAIL) camera", ln) for ln in lines), f"a SKIP or FAIL camera line: {lines}")
    check(any(ln.startswith("OK coplanar") for ln in lines), f"the other checks still run: {lines}")
    if any(ln.startswith("FAIL") for ln in lines):
        check(code == 1, f"a FAIL line means exit 1, got {code}")


def t_checks_alone():
    import importlib.util
    import shutil
    import tempfile
    clean_room()
    held = sys.modules.get("wall_gaps", False)
    sys.modules["wall_gaps"] = None
    try:
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(os.path.join(tcommon.SCRIPTS, "checks.py"), d)
            spec = importlib.util.spec_from_file_location("checks_alone", os.path.join(d, "checks.py"))
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except ImportError as e:
                check(False, f"checks.py alone imports without wall_gaps.py: {type(e).__name__}: {e}")
                return
            buf = io.StringIO()
            code = None
            with contextlib.redirect_stdout(buf):
                try:
                    mod.run_checks(floors=("floor",))
                except SystemExit as e:
                    code = e.code
            lines = buf.getvalue().splitlines()
    finally:
        if held is False:
            sys.modules.pop("wall_gaps", None)
        else:
            sys.modules["wall_gaps"] = held
    check(any(ln.startswith("FAIL wall_gaps: error ModuleNotFoundError") for ln in lines),
          f"missing wall_gaps module is a FAIL line: {lines}")
    check(any(ln.startswith("OK coplanar") for ln in lines), f"the other checks still run: {lines}")
    check(code == 1 and lines[-1] == "FAIL run_checks: wall_gaps", f"exit 1 (code {code}): {lines[-2:]}")


# ---------------------------------------------------------------- T18 timing
def t_timing():
    rnd = random.Random(1)
    reset()
    bh.box("floor", -40, 40, -40, 40, -0.2, 0)
    bh.cut_holes("floor", [(rnd.uniform(-30, 30), 0, rnd.uniform(-30, 30), 0, -0.3, 0.1) for _ in range(0)] or
                 [(-20, -18, -20, -18, -0.3, 0.1), (10, 13, 5, 8, -0.3, 0.1), (25, 28, -25, -22, -0.3, 0.1)])
    for k in range(60):
        x, y, ln = rnd.uniform(-35, 30), rnd.uniform(-35, 30), rnd.uniform(2, 8)
        if k % 2:
            bh.box(f"wall_{k}", x, x + ln, y, y + 0.1, 0, 2.6)
        else:
            bh.box(f"wall_{k}", x, x + 0.1, y, y + ln, 0, 2.6)
    for k in range(20):
        x, y = rnd.uniform(-35, 30), rnd.uniform(-35, 30)
        bh.box(f"ceil_{k}", x, x + 6, y, y + 6, 2.6, 2.7)
    for k in range(1300):
        x, y, z = rnd.uniform(-38, 38), rnd.uniform(-38, 38), rnd.uniform(0.0, 2.0)
        bh.box(f"obj_{k}", x, x + rnd.uniform(0.1, 0.6), y, y + rnd.uniform(0.1, 0.6), z, z + rnd.uniform(0.1, 0.8))
    for k in range(200):
        z = rnd.uniform(0, 1.5)
        bh.cyl(f"cyl_{k}", rnd.uniform(-38, 38), rnd.uniform(-38, 38), z, z + rnd.uniform(0.2, 1.0), 0.15)
    for k in range(120):
        bh.sphere(f"sph_{k}", rnd.uniform(-38, 38), rnd.uniform(-38, 38), rnd.uniform(0.3, 2.0), 0.2)
    for k in range(240):
        bh.box(f"tile_{k}", -38 + 0.31 * (k % 40), -37.7 + 0.31 * (k % 40), -39.99, -39.98,
               0.31 * (k // 40), 0.3 + 0.31 * (k // 40))
    mq.mannequin(mq.EXAMPLE_POSE)
    bh.set_resolution(160)
    bh.perspective_camera((0, 0, 1.5), (5, 5, 1.5), lens=20)
    upd()
    n_obj = sum(1 for o in bpy.data.objects if o.type == "MESH")
    paths = {f"p{i}": (i, i + 1, 0, 1, 0.0) for i in range(6)}
    calls = (("coplanar", lambda: ck.coplanar_check()),
             ("flipped", lambda: ck.flipped_check()),
             ("wall_gaps", lambda: ck.wall_gap_check(floors=("floor",))),
             ("floor_fit", lambda: ck.floor_fit_check(("floor",))),
             ("camera", lambda: ck.camera_check(interior=True)),
             ("clearance", lambda: ck.clearance_check(paths)))
    total = 0.0
    for name, fn in calls:
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        total += dt
        print(f"TIMING {name} {dt:.2f} s ({n_obj} mesh objects)")
    print(f"TIMING total {total:.2f} s")
    check(total < 60, f"six checks on {n_obj} objects take under 60 s, took {total:.1f} s")


CASES = (t_wall_gaps, t_openings, t_flipped, t_floor_fit, t_floor_orientation, t_support, t_camera_backface,
         t_camera_escape, t_clearance, t_coplanar, t_coplanar_mirrored, t_run_clean, t_run_float, t_run_formats, t_run_walls,
         t_run_errors, t_run_openings, t_misc, t_plan_view_openings, t_floor_fit_upper_slab,
         t_floor_open_planes, t_support_variants, t_wall_heights, t_run_names_as_strings, t_run_unrendered_floors,
         t_run_camera_not_a_camera, t_checks_alone, t_timing)


def main():
    for fn in CASES:
        try:
            fn()
        except Exception as e:
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finish("bl_rev6")


main()
