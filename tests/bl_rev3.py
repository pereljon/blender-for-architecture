"""Blender test: Revision 3 behavior (T6 to T9) from the scripts contract."""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, close, dims, extents, finish

import bhelpers as bh
import mannequin as mq

FT = 0.3048


def reset(unit="m"):
    bh.set_units(unit)
    bh.clear_scene()


# ---------------------------------------------------------------- T6: mannequin legs by side
def knee_point(side):
    bpy.context.view_layer.update()  # matrix_world is stale until the depsgraph updates
    ends = {}
    for part in ("thigh", "shin"):
        ob = bpy.data.objects[f"man_{part}{side}"]
        zs = [v.co.z for v in ob.data.vertices]
        ends[part] = [ob.matrix_world @ Vector((0, 0, z)) for z in (min(zs), max(zs))]
    pairs = [(a, b) for a in ends["thigh"] for b in ends["shin"]]
    a, b = min(pairs, key=lambda p: (p[0] - p[1]).length)
    return (a + b) / 2


def t6():
    for face in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for swap in (False, True):
            reset()
            f = Vector((face[0], face[1], 0))
            r = Vector((f.y, -f.x, 0))                       # figure's right
            right = (r.x * 0.1, r.y * 0.1)
            left = (-r.x * 0.1, -r.y * 0.1)
            ankles = (left, right) if not swap else (right, left)
            z = Vector((0, 0, 1))
            wr = lambda s: tuple(tuple(c) for c in (f * 0.35 + r * (0.19 * s) + z * 1.1, f * 0.42 + r * (0.19 * s) + z * 1.08))
            pose = dict(root=(0.0, 0.0), face=face, pz=None, bend=18, head=28, ankles=ankles,
                        rw=wr(1), rpole=(0, 0, -1), lw=wr(-1), lpole=(0, 0, -1))
            mq.mannequin(pose, height=1.78)
            for side in (1, -1):
                k = knee_point(side)
                lat = k.dot(r) * side
                check(lat > 0.05, f"T6 face={face} ankles {'swapped' if swap else 'listed left,right'}: "
                                  f"side {side} knee is {'right' if side == 1 else 'left'} of the root, lateral offset {lat:.3f} m")


# ---------------------------------------------------------------- T7: feet defaults
def t7_unit(unit, u):
    label = f"T7 {unit}"
    reset(unit)
    mat = bh.principled("t7_grey", (0.5, 0.5, 0.5))

    # person 1.75 m
    bh.person(mat, 0, 0)
    top = max(extents(bpy.data.objects[n])[1][2] for n in ("person_body", "person_head"))
    check(1.70 < top < 1.76, f"{label}: person is about 1.75 m tall, top at {top:.3f} m")

    # door_swings at 0.06 m
    bh.door_swings([dict(arc=[(0, 0), (1 / u, 0), (1 / u, 1 / u)])], mat)
    cu = bpy.data.objects["swing_0"].data
    zs = [p.co.z for p in cu.splines[0].points]
    check(all(close(v, 0.06, 1e-6) for v in zs), f"{label}: door swing arc at 0.06 m, got {zs}")
    check(close(cu.bevel_depth, 0.02, 1e-6), f"{label}: door swing arc is 0.04 m wide (bevel {cu.bevel_depth:.5f} m)")

    # plan_camera clip
    cut = 4.0 / u
    cam = bh.plan_camera((0, 0), 8 / u, cut)
    check(close(cam.data.clip_start, 12 - cut * u, 1e-4), f"{label}: plan_camera clip_start {cam.data.clip_start:.4f} m, want {12 - cut * u:.4f}")
    check(close(cam.data.clip_end, 18, 1e-4), f"{label}: plan_camera clip_end {cam.data.clip_end:.4f} m, want 18")
    check(close(cam.location.z, 12, 1e-4), f"{label}: plan_camera height {cam.location.z:.4f} m, want 12")

    # overlay marks 0.03 m wide
    before = set(bpy.data.objects)
    bh.dotted_square("dsq", 0, 0, 0.5 / u, 0.0, mat)
    first = bpy.data.objects["dsq_0"]
    d = dims(first)
    check(close(d[1], 0.03, 1e-5), f"{label}: dotted_square mark is 0.03 m wide, dims {d}")
    bh.dashed_path("dpa", [(0, 5 / u), (2 / u, 5 / u)], 0.0, mat)
    d = dims(bpy.data.objects["dpa"])
    check(close(d[1], 0.03, 1e-5), f"{label}: dashed_path mark is 0.03 m wide, dims {d}")

    # planks brick width 1.8 m, row height 0.18 m
    m = bh.planks("t7_planks", (0.5, 0.4, 0.3))
    br = next(n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeTexBrick")
    check(close(br.inputs["Brick Width"].default_value, 1.8, 1e-5), f"{label}: planks brick width {br.inputs['Brick Width'].default_value:.4f} m, want 1.8")
    check(close(br.inputs["Row Height"].default_value, 0.18, 1e-5), f"{label}: planks row height {br.inputs['Row Height'].default_value:.4f} m, want 0.18")

    # tile_wall sliver threshold
    face = bh.Face((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))
    rows = [(0.0, 0.6 / u)]
    for width_mm, expect in ((3, 0), (5, 1)):
        n0 = len(bh.PIECES)
        bh.tile_wall(f"sl{width_mm}", face, 0.0, width_mm / 1000 / u, 0.0, 1, rows, mat, random.Random(1))
        n = len(bh.PIECES) - n0
        check(n == expect, f"{label}: tile_wall with a {width_mm} mm wide column makes {expect} pieces, got {n}")


def wall_key(ws, u):
    return sorted((round(w["x0"] * u, 4), round(w["x1"] * u, 4), round(w["y0"] * u, 4), round(w["y1"] * u, 4)) for w in ws)


def t7_walls():
    results = {}
    for unit, u in (("m", 1.0), ("ft", FT)):
        reset(unit)
        k = 1 / u
        out = {}
        for tag, hx1 in (("drop", 3.97), ("keep", 3.93)):     # remnant 0.03 m and 0.07 m wide
            walls = [dict(kind="new", x0=0, x1=4 * k, y0=0, y1=0.2 * k)]
            cut = bh.cut_openings(walls, [(1 * k, hx1 * k, -1 * k, 1 * k)])
            out["cut_" + tag] = wall_key(cut, u)
        walls = [dict(kind="new", x0=0.04 * k, x1=4 * k, y0=0, y1=0.2 * k),
                 dict(kind="new", x0=10 * k, x1=14 * k, y0=0, y1=0.2 * k)]
        fixed = bh.fix_walls(walls, wall_fixes=[((0, 4 * k, 0, 0.2 * k), (0.1 * k, 0.3 * k))])
        out["fix_near"] = wall_key(fixed, u)
        far = [dict(kind="new", x0=0.08 * k, x1=4 * k, y0=0, y1=0.2 * k)]
        out["fix_far"] = wall_key(bh.fix_walls(far, wall_fixes=[((0, 4 * k, 0, 0.2 * k), (0.1 * k, 0.3 * k))]), u)
        results[unit] = out
    check(len(results["m"]["cut_drop"]) == 1, f"T7 metric: a 0.03 m jamb remnant is dropped by cut_openings: {results['m']['cut_drop']}")
    check(len(results["m"]["cut_keep"]) == 2, f"T7 metric: a 0.07 m remnant is kept by cut_openings: {results['m']['cut_keep']}")
    check(results["m"]["fix_near"][1][2] == 0.1 or results["m"]["fix_near"][0][2] == 0.1, f"T7 metric: fix_walls matches a wall 0.04 m off: {results['m']['fix_near']}")
    check(results["m"]["fix_far"] == [(0.08, 4.0, 0.0, 0.2)], f"T7 metric: fix_walls leaves a wall 0.08 m off: {results['m']['fix_far']}")
    for key in results["m"]:
        check(results["m"][key] == results["ft"][key], f"T7 cut_openings/fix_walls {key}: feet {results['ft'][key]} equals metres {results['m'][key]}")


def t7():
    t7_unit("m", 1.0)
    t7_unit("ft", FT)
    t7_walls()


# ---------------------------------------------------------------- T8: plan entry without drop or keep
def t8_case(unit, u):
    label = f"T8 {unit}"
    reset(unit)
    bh.setup_cycles(8, gpu=False)
    mat = bh.principled("t8_grey", (0.5, 0.5, 0.5))
    k = 1 / u
    bh.box("floor", -5 * k, 5 * k, -5 * k, 5 * k, -0.1 * k, 0, mat)
    bh.box("low_box", 0, 1 * k, 0, 1 * k, 0, 0.5 * k, mat)
    bh.box("ceiling", -5 * k, 5 * k, -5 * k, 5 * k, 2.4 * k, 2.5 * k, mat)
    for nm, loc in (("fill_a", (0, 0, 2.3)), ("fill_b", (2, 2, 2.0))):
        ld = bpy.data.lights.new(nm, "POINT")
        lo = bpy.data.objects.new(nm, ld)
        lo.location = tuple(c * k * u for c in loc)
        bpy.context.scene.collection.objects.link(lo)
    bh.add_camera(dict(plan=True, center=(0, 0), width=8 * k, cut=1.2 * k, aspect=1.0), 160)
    check(bpy.data.objects["ceiling"].hide_render, f"{label}: a ceiling above the cut is hidden without drop or keep")
    check(not bpy.data.objects["low_box"].hide_render, f"{label}: an object under the cut stays visible")
    for nm in ("fill_a", "fill_b"):
        check(bpy.data.objects[nm].hide_render, f"{label}: scene light {nm} is hidden")
    check("plan_overhead" in bpy.data.objects, f"{label}: plan_overhead exists")
    if "plan_overhead" in bpy.data.objects:
        check(not bpy.data.objects["plan_overhead"].hide_render, f"{label}: plan_overhead is not hidden")


def t8():
    t8_case("m", 1.0)
    t8_case("ft", FT)


# ---------------------------------------------------------------- T9: plan_light size
def light_size():
    ld = bpy.data.lights["plan_overhead"]
    return ld.size, ld.size_y, ld.energy


def t9():
    reset("m")
    bh.setup_cycles(8, gpu=False)
    bh.add_camera(dict(plan=True, center=(0, 0), width=4.0, cut=1.2, aspect=1.0), 160)
    sx, sy, en = light_size()
    check(close(sx, 36.0, 1e-4) and close(sy, 18.0, 1e-4), f"T9 metric 4 m plan: light {sx:.3f} by {sy:.3f} m, want 36 by 18")
    check(close(en, 6.0 * sx * sy, 1e-2), f"T9 metric: energy {en:.2f} W is 6 W/m2 times area {sx * sy:.1f}")

    reset("ft")
    bh.setup_cycles(8, gpu=False)
    bh.add_camera(dict(plan=True, center=(0, 0), width=84.0, cut=4.0, aspect=60 / 84), 160)
    sx, sy, en = light_size()
    ex, ey = 84 * FT, 60 * FT
    check(sx >= 1.5 * ex - 1e-4 and sy >= 1.5 * ey - 1e-4,
          f"T9 84 ft by 60 ft plan: light {sx:.2f} by {sy:.2f} m covers 1.5x extent {1.5 * ex:.2f} by {1.5 * ey:.2f} m")
    check(sx >= 36 - 1e-4 and sy >= 18 - 1e-4, f"T9 84 ft plan: light is at least 36 by 18 m, got {sx:.2f} by {sy:.2f}")
    check(close(en, 6.0 * sx * sy, 1e-2), f"T9 feet: energy {en:.2f} W is 6 W/m2 times area {sx * sy:.1f}")

    # aspect > 1: extent is (width / aspect, width)
    reset("m")
    bh.setup_cycles(8, gpu=False)
    bh.add_camera(dict(plan=True, center=(0, 0), width=40.0, cut=1.2, aspect=2.0), 160)
    sx, sy, _ = light_size()
    check(sx >= 1.5 * 20.0 - 1e-4 and sy >= 1.5 * 40.0 - 1e-4, f"T9 aspect 2 entry: light {sx:.2f} by {sy:.2f} m covers 1.5x (20, 40)")


def main():
    t6()
    t7()
    t8()
    t9()
    finish("bl_rev3")


main()
