"""Blender test: Revision 2 behavior (T1, T2, T4, mannequin floor_z) from the scripts contract."""
import contextlib
import io
import math
import os
import re
import random
import sys

import bpy
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, close, dims, extents, finish

import bhelpers as bh
import checks as ck
import mannequin as mq

FT = 0.3048


def reset(unit="m"):
    bh.set_units(unit)
    bh.clear_scene()


def pair_set(hits):
    return {frozenset(h) for h in hits}


# ---------------------------------------------------------------- T1: plan entry with drop/keep
def t1_case(unit, u, fz):
    label = f"T1 {unit} floor_z={fz}"
    reset(unit)
    bh.setup_cycles(8, gpu=False)
    cut = 1.2 / u
    h = 2.0 / u
    mat = bh.principled("t1_grey", (0.5, 0.5, 0.5))
    bh.box("floor", -5 / u, 5 / u, -5 / u, 5 / u, fz - 0.1 / u, fz, mat)
    bh.cyl("opt_cyl", 0, 0, fz, fz + h, 0.2 / u, mat)           # origin at mid-height
    bh.box("opt_box", 1 / u, 1.5 / u, 1 / u, 1.5 / u, fz + 0.5 / u, fz + h, mat)   # origin at world zero, not at the floor
    bh.box("low_box", -1 / u, -0.5 / u, 1 / u, 1.5 / u, fz, fz + 0.5 / u, mat)
    bh.box("hi_box", -1 / u, -0.5 / u, -1.5 / u, -1 / u, fz + 1.5 / u, fz + 2.5 / u, mat)
    bh.box("keep_hi", 1 / u, 1.5 / u, -1.5 / u, -1 / u, fz + 1.5 / u, fz + 2.5 / u, mat)
    bh.add_camera(dict(plan=True, center=(0, 0), width=8 / u, cut=cut, floor_z=fz, aspect=1.0,
                       drop=("opt_",), keep=("keep_",)), 160)
    floor_m, cut_m = fz * u, cut * u
    for name in ("opt_cyl", "opt_box"):
        lo, hi = extents(bpy.data.objects[name])
        check(hi[2] < floor_m + cut_m, f"{label}: {name} top {hi[2]:.5f} is below the cut {floor_m + cut_m:.5f}")
        check(close(hi[2], floor_m + cut_m - 0.06, 1e-3), f"{label}: {name} top lands 0.06 m under the cut, got {hi[2] - floor_m - cut_m:.5f}")
    lo, _ = extents(bpy.data.objects["opt_cyl"])
    check(close(lo[2], floor_m, 1e-4), f"{label}: dropped cylinder bottom stays at the floor, {lo[2]:.6f} vs {floor_m:.6f}")
    check(not bpy.data.objects["opt_cyl"].hide_render, f"{label}: dropped object stays visible")
    check(bpy.data.objects["hi_box"].hide_render, f"{label}: an object above the cut is hidden")
    check(not bpy.data.objects["keep_hi"].hide_render, f"{label}: a keep prefix stays visible above the cut")
    check(not bpy.data.objects["low_box"].hide_render, f"{label}: an object under the cut stays visible")
    lights = [o for o in bpy.data.objects if o.type == "LIGHT" and not o.hide_render]
    check(len(lights) >= 1, f"{label}: a visible overhead light exists")
    for lt in lights:
        check(lt.location.z > floor_m + cut_m, f"{label}: light {lt.name} z {lt.location.z:.3f} above floor_z + cut {floor_m + cut_m:.3f}")


def t1():
    t1_case("m", 1.0, 0.0)
    t1_case("ft", FT, 0.0)
    t1_case("m", 1.0, 3.0)
    t1_case("ft", FT, 10.0)


# ---------------------------------------------------------------- T2: clash_check and coplanar_check
def open_cube(name, s):
    verts = [(x, y, z) for z in (0, s) for y in (0, s) for x in (0, s)]
    idx = lambda x, y, z: x + 2 * y + 4 * z
    faces = [(idx(0, 0, 0), idx(0, 1, 0), idx(1, 1, 0), idx(1, 0, 0)),     # bottom
             (idx(0, 0, 0), idx(1, 0, 0), idx(1, 0, 1), idx(0, 0, 1)),     # -y
             (idx(1, 0, 0), idx(1, 1, 0), idx(1, 1, 1), idx(1, 0, 1)),     # +x
             (idx(1, 1, 0), idx(0, 1, 0), idx(0, 1, 1), idx(1, 1, 1)),     # +y
             (idx(0, 1, 0), idx(0, 0, 0), idx(0, 0, 1), idx(0, 1, 1))]     # -x, no top
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return bh.new_obj(name, me)


def t2():
    # default b_prefixes: every other visible mesh, whatever its name
    reset()
    bh.box("man_a", 0, 1, 0, 1, 0, 1)
    bh.box("zzz_thing", 0.5, 2, 0, 1, 0, 1)
    for label, kw in (("default", {}), ("None", dict(b_prefixes=None)), ("empty", dict(b_prefixes=()))):
        hits = ck.clash_check(("man_",), **kw)
        check(("man_a", "zzz_thing") in [tuple(h) for h in hits], f"T2 {label} b_prefixes reports an unprefixed overlap: {hits}")
    check(ck.clash_check(("man_",), ignore=("zzz_",)) == [], "T2 ignore drops the pair under default b_prefixes")
    bh.box("man_b", 0.2, 0.8, 0.2, 0.8, 0.2, 0.8)
    hits = [frozenset(h) for h in ck.clash_check(("man_",), ignore=("zzz_",))]
    check(frozenset(("man_a", "man_b")) not in hits, "T2 objects of A are not B for each other")
    reset()
    bh.box("man_a", 0, 1, 0, 1, 0, 1)
    bh.box("zzz_far", 5, 6, 0, 1, 0, 1)
    check(ck.clash_check(("man_",)) == [], "T2 default b_prefixes: a clear object is no hit")

    # open meshes skip the containment test
    reset()
    open_cube("open_b", 4.0)
    bh.box("man_a", 1.5, 2.5, 1.5, 2.5, 1.0, 2.0)
    check(ck.clash_check(("man_",), ("open_",)) == [], "T2 small box inside an open mesh, surfaces apart, is no hit")
    bh.clear_scene()
    open_cube("open_b", 4.0)
    bh.box("man_a", 3.7, 4.5, 1.5, 2.5, 1.0, 2.0)
    check(len(ck.clash_check(("man_",), ("open_",))) == 1, "T2 box crossing the wall of an open mesh is a hit")
    bh.clear_scene()
    bh.box("closed_b", 0, 4, 0, 4, 0, 4)
    bh.box("man_a", 1.5, 2.5, 1.5, 2.5, 1.0, 2.0)
    check(len(ck.clash_check(("man_",), ("closed_",))) == 1, "T2 control: the same box inside a closed mesh is a hit")

    # clockwise prism
    cw = lambda x0, x1: [(x0, 0), (x0, 2), (x1, 2), (x1, 0)]
    reset()
    ob = bh.prism("cp_p", cw(2, 4), 0, 1)
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    vol = bm.calc_volume(signed=True)
    bm.free()
    check(vol > 0, f"T2 clockwise prism has outward normals (signed volume {vol})")
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    check(ck.coplanar_check() == [], f"T2 clockwise prism butted against a box is not a coplanar hit: {ck.coplanar_check()}")
    bh.clear_scene()
    bh.prism("cp_p", cw(1, 3), 0, 1)
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    check(pair_set(ck.coplanar_check()) == {frozenset(("cp_a", "cp_p"))},
          f"T2 clockwise prism overlapping a box is a coplanar hit: {ck.coplanar_check()}")
    reset("ft")
    bh.prism("cp_p", cw(2, 4), 0, 1)
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    check(ck.coplanar_check() == [], "T2 clockwise prism butted against a box, in feet, is not a hit")


# ---------------------------------------------------------------- T4: extra_walls, tile names, mannequin floor_z
def t4_walls(unit, u):
    label = f"T4 {unit}"
    reset(unit)
    walls = [dict(kind="new", x0=0, x1=6, y0=0, y1=0.2)]
    rows = [("new", 8, 12, 0, 0.2), ("existing", 3, 3.2, 1, 3)]
    extra = bh.extra_walls(rows)
    check(len(extra) == 2 and all(isinstance(w, dict) for w in extra), f"{label}: extra_walls returns one dict per row")
    for w, r in zip(extra, rows):
        check(w["kind"] == r[0] and all(close(w[k], v) for k, v in zip(("x0", "x1", "y0", "y1"), r[1:])),
              f"{label}: extra_walls dict matches its row {w}")
    allw = bh.fix_walls(walls) + bh.extra_walls(rows)
    cut = bh.cut_openings(allw, [(2, 3, -1, 1), (9, 10, -1, 1)])
    check(len(cut) == 5, f"{label}: cut_openings splits the base wall and the extra wall, got {len(cut)}")
    check(any(w["kind"] == "existing" and close(w["y1"], 3) for w in cut), f"{label}: the existing extra wall passes through")
    made = bh.walls_from_plan(cut, 0, 2.5, prefix="xw_")
    check(len(made) == len(cut) and sorted(o.name for o in made) == sorted(f"xw_{k}" for k in range(len(cut))),
          f"{label}: walls_from_plan names {[o.name for o in made]}")
    d = dims(made[0])
    w0 = cut[0]
    check(close(d[0], (w0["x1"] - w0["x0"]) * u, 1e-6) and close(d[2], 2.5 * u, 1e-6), f"{label}: wall dims {d}")


def t4_tiles():
    reset()
    face = bh.Face((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))
    mat = bh.principled("t4_grey", (0.5, 0.5, 0.5))
    n0 = len(bh.PIECES)
    rows = [(k * 0.602, k * 0.602 + 0.6) for k in range(12)]
    bh.tile_wall("big", face, 0.0, 12 * 1.202, 0.0, 1, rows, mat, random.Random(3))
    pieces = bh.PIECES[n0:]
    names = [p["name"] for p in pieces]
    check(len(names) >= 144, f"T4 12 x 12 tile wall makes 144+ pieces, got {len(names)}")
    check(len(set(names)) == len(names), f"T4 tile piece names are unique ({len(names) - len(set(names))} duplicates)")
    check(all(re.fullmatch(r"wt_big_\d+_\d+_\d+", n) for n in names), f"T4 tile names use separators: {names[:3]}")
    objs = [o.name for o in bpy.data.objects if o.name.startswith("wt_big_")]
    check(sorted(objs) == sorted(names), "T4 every piece object carries exactly its piece name")


def lowest(prefix="man_"):
    return min(extents(o)[0][2] for o in bpy.data.objects if o.name.startswith(prefix) and o.type == "MESH")


def t4_mannequin():
    reset()
    mq.mannequin(mq.EXAMPLE_POSE, height=1.78)
    base = lowest()
    for unit, u, fz in (("m", 1.0, 3.0), ("ft", FT, 10.0)):
        reset(unit)
        k = 1 / u
        p = dict(mq.EXAMPLE_POSE)
        p["floor_z"] = fz
        p["root"] = tuple(c * k for c in p["root"])
        p["ankles"] = tuple(tuple(c * k for c in a) for a in p["ankles"])
        for key in ("rw", "lw"):
            p[key] = tuple((a[0] * k, a[1] * k, a[2] * k + fz) for a in p[key])
        mq.mannequin(p, height=1.78 * k)
        lo = lowest()
        want = fz * u
        check(abs(lo - want) < 0.1, f"T4 mannequin floor_z={fz} {unit}: lowest point {lo:.3f} m near {want:.3f} m")
        check(abs((lo - want) - base) < 0.03, f"T4 mannequin floor_z={fz} {unit}: foot offset {lo - want:.3f} matches floor_z=0 ({base:.3f})")


def main():
    t1()
    t2()
    t4_walls("m", 1.0)
    t4_walls("ft", FT)
    t4_tiles()
    t4_mannequin()
    finish("bl_rev2")


main()
