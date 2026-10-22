"""Blender test: v1.1.1 (T42 floor_fit support, T43 lid on a plate, T44 cost, T45 coplanar overlaps, T46 run_checks
overlaps output, T47 hits_file, T49 finishes and wall_gaps) from Revision 9 of the design. T48 is in test_v111.py."""
import contextlib
import io
import math
import os
import random
import re
import shutil
import sys
import time
import traceback

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, finish

import bhelpers as bh
import checks as ck
import mannequin as mq


def reset(unit="m"):
    bh.set_units(unit)
    bh.clear_scene()
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def upd():
    bpy.context.view_layer.update()


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


def collection(name, objs=(), parent=None):
    """A collection linked under parent (default: the scene collection) that holds objs and only objs."""
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    for o in objs:
        for oc in list(o.users_collection):
            oc.objects.unlink(o)
        c.objects.link(o)
    return c


def clean_room(thick_floor=0.1):
    reset()
    bh.box("floor", -0.1, 3.1, -0.1, 4.1, -thick_floor, 0)
    bh.box("wall_south", -0.1, 3.1, -0.1, 0, 0, 2.6)
    bh.box("wall_north", -0.1, 3.1, 4, 4.1, 0, 2.6)
    bh.box("wall_west", -0.1, 0, 0, 4, 0, 2.6)
    bh.box("wall_east", 3, 3.1, 0, 4, 0, 2.6)
    bh.box("ceiling", -0.1, 3.1, -0.1, 4.1, 2.6, 2.7)
    bh.box("counter", 1.6, 2.9, 0.1, 0.7, -0.005, 0.9)
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


def first(lines, pattern):
    """Index of the first line that matches the regex, or None."""
    return next((i for i, ln in enumerate(lines) if re.match(pattern, ln)), None)


def mesh_count():
    return sum(1 for o in bpy.data.objects if o.type == "MESH" and not o.hide_render)


# ---------------------------------------------------------------- T42: floor_fit support by contact
def t42_scene():
    reset()
    bh.box("floor", -8, 8, -8, 8, -0.5, 0)
    bh.box("wall_n", -8, 8, 4.0, 4.1, 0, 2.6)
    bh.box("wall_x", 6.0, 6.1, -4.0, -2.0, 0, 2.6)
    boxes = (
        # wall-hung, touching wall_n at y 4.0
        ("vanity", (-7, -6.4, 3.5, 4.0, 0.15, 0.6)),
        ("toilet", (-6.0, -5.6, 3.45, 4.0, 0.2, 0.6)),
        ("tower", (-5.2, -4.8, 3.6, 4.0, 0.12, 2.0)),
        ("outlet", (-4.4, -4.32, 3.99, 4.0, 0.25, 0.33)),
        ("blind", (-4.0, -3.2, 3.98, 4.0, 0.2, 1.5)),
        ("rail", (-2.9, -2.3, 3.97, 4.0, 0.12, 0.15)),
        ("vanity_3mm", (-2.0, -1.4, 3.5, 3.997, 0.15, 0.6)),
        ("bracket", (-1.0, -0.95, 3.9, 4.06, 0.2, 0.25)),
        # a chain from a wall at 0.15 m
        ("shelf_w", (4.0, 5.0, 3.7, 4.0, 0.15, 0.17)),
        ("box_w", (4.7, 5.4, 3.75, 3.95, 0.17, 0.4)),
        ("tag_w", (5.4, 5.5, 3.8, 3.9, 0.2, 0.3)),
        # a finish
        ("wt_7", (5.7, 6.3, 3.88, 3.894, 0.3, 1.2)),
        ("outlet_t", (5.9, 5.98, 3.87, 3.88, 0.25, 0.33)),
        # resting off centre
        ("rail_l", (-7, -6.97, -1, -0.5, 0, 0.12)),
        ("rail_r", (-6.55, -6.52, -1, -0.5, 0, 0.12)),
        ("gear", (-7, -6.52, -1, -0.5, 0.12, 0.3)),
        ("ring_s", (-5.5, -3.5, -1.0, -0.95, 0, 0.25)),
        ("ring_n", (-5.5, -3.5, 0.95, 1.0, 0, 0.25)),
        ("ring_w", (-5.5, -5.45, -0.95, 0.95, 0, 0.25)),
        ("ring_e", (-3.55, -3.5, -0.95, 0.95, 0, 0.25)),
        ("mattress", (-5.5, -3.5, -1, 1, 0.25, 0.45)),
        ("plinth", (1.0, 2.2, -1.0, -0.4, 0, 0.08)),
        ("door", (1.05, 1.65, -1.015, -0.995, 0.08, 0.8)),
        ("carcass", (1.0, 2.2, -0.995, -0.4, 0.08, 0.9)),
        ("beam", (5.4, 5.6, -1.5, 0.5, 0, 0.06)),
        ("plank", (5.0, 5.9, -0.6, -0.4, 0.06, 0.08)),
        # chain three deep from a floor
        ("leg", (-7.02, -6.94, 1.48, 1.56, 0, 0.04)),
        ("rail_c", (-7, -6.6, 1.5, 1.6, 0.04, 0.06)),
        ("slat", (-6.7, -6.3, 1.52, 1.58, 0.06, 0.07)),
        ("pad", (-6.4, -6.0, 1.53, 1.57, 0.07, 0.09)),
        # broad-face side contact
        ("carc_f", (-1.0, -0.4, 1.5, 2.0, 0, 0.9)),
        ("door_s", (-0.95, -0.45, 1.48, 1.5, 0.03, 0.85)),
        ("plinth2", (-5.0, -3.8, 1.55, 2.0, 0, 0.1)),
        ("carc2", (-5.0, -3.8, 1.5, 2.0, 0.1, 0.9)),
        ("door2", (-4.95, -4.35, 1.48, 1.5, 0.03, 0.85)),
        ("carc_d", (-3.0, -2.4, 1.5, 2.0, 0, 0.9)),
        ("drawer_f", (-2.95, -2.45, 1.48, 1.5, 0.03, 0.2)),
        # narrow side contact below 0.1 m
        ("chest", (-2.4, -2.1, 1.5, 1.9, 0.03, 0.5)),
        # the failures
        ("bed_raised", (-5, -3, -5.5, -3.5, 0.08, 0.5)),
        ("bed_side", (1.5, 3.5, -4, -2, 0.08, 0.5)),
        ("nightstand", (1.0, 1.5, -4, -3.5, 0, 0.6)),
        ("bed_wall", (0.5, 2.5, 2.0, 4.0, 0.08, 0.5)),
        ("corner_box", (6.12, 6.5, -1.98, -1.6, 0.15, 0.5)),
        ("ledge", (3.0, 3.6, 3.8, 4.0, 0.05, 0.3)),
        ("peg", (3.2, 3.3, 3.7, 3.8, 0.12, 0.2)),
        ("shelf_float", (-7, -6, -4.3, -4.0, 0.08, 0.10)),
        ("vanity_gap", (-0.5, 0.1, 3.46, 3.96, 0.15, 0.6)),
        ("wall_float", (7.0, 7.1, 1.0, 4.0, 0.05, 2.6)),
        ("sunk_box", (7.5, 7.7, -7.5, -7.3, -0.05, 0.5)),
    )
    for n, r in boxes:
        bh.box(n, *r)
    # a stand built mirrored (negative x scale), placed so that its world extents are x 2.99 to 3.01
    stand = bh.box("stand", 2.99, 3.01, -1.01, -0.99, 0, 0.14)
    stand.scale.x = -1
    stand.location.x = 6.0
    # a cymbal: a 32-segment disc, underside centre at (3, -1, 0.14), turned 20 degrees about the world x axis
    cym = bh.cyl("cymbal", 0, 0, 0, 0.004, 0.18, n=32)
    cym.data.transform(Matrix.Translation((0, 0, 0.002)))
    cym.rotation_euler = (math.radians(20), 0, 0)
    cym.location = (3.0, -1.0, 0.14)
    upd()


T42_FAIL = [("bed_raised", 0.08), ("bed_side", 0.08), ("bed_wall", 0.08), ("chest", 0.03), ("corner_box", 0.15),
            ("ledge", 0.05), ("peg", 0.12), ("shelf_float", 0.08), ("sunk_box", -0.05), ("vanity_gap", 0.15),
            ("wall_float", 0.05)]


def t42():
    t42_scene()
    lo = bpy.data.objects["cymbal"].matrix_world
    zs = [(lo @ v.co).z for v in bpy.data.objects["cymbal"].data.vertices]
    check(0.07 < min(zs) < 0.085, f"T42 fixture: the cymbal's lowest point is about 0.077 m up, got {min(zs):.4f}")
    st = tcommon.extents(bpy.data.objects["stand"])
    check(abs(st[0][0] - 2.99) < 1e-6 and abs(st[1][0] - 3.01) < 1e-6, f"T42 fixture: mirrored stand extents x {st[0][0]}, {st[1][0]}")
    expect("T42 floor_fit_check with finishes", ck.floor_fit_check(("floor",), finishes=("wt_",)), T42_FAIL)
    expect("T42 floor_fit_check without finishes: outlet_t also floats", ck.floor_fit_check(("floor",)),
           sorted(T42_FAIL + [("outlet_t", 0.25)], key=lambda h: h[0]))


def t42b():
    """Walls and finishes in the band keep today's rule: no contact support, reported when floating."""
    reset()
    bh.box("floor", -8, 8, -8, 8, -0.5, 0)
    bh.box("wall_n", -8, 8, 4.0, 4.1, 0, 2.6)
    bh.box("wall_hi", 7.0, 7.1, 1.0, 4.0, 0.15, 2.6)
    bh.box("wt_9", 1.0, 1.4, 3.9, 4.0, 0.15, 0.5)
    # A raised bed that runs 0.3 m into a nightstand whose top is level with the bed's top: the bed's top corners
    # lie on the nightstand's top face, but only a face that the bed rests on counts.
    bh.box("nightstand2", 2.5, 3.3, -6.8, -6.2, 0, 0.5)
    bh.box("bed2", 3.0, 5.0, -6.5, -4.5, 0.08, 0.5)
    upd()
    expect("T42 a wall and a finish at base 0.15 m touching wall_n are floating",
           ck.floor_fit_check(("floor",), finishes=("wt_",)), [("bed2", 0.08), ("wall_hi", 0.15), ("wt_9", 0.15)])
    expect("T42 without finishes the tile piece is an object on the wall and passes",
           ck.floor_fit_check(("floor",)), [("bed2", 0.08), ("wall_hi", 0.15)])


# ---------------------------------------------------------------- T43: a lid on a plate
def t43():
    reset()
    bh.box("floor", -8, 8, -8, 8, -0.5, 0)
    bh.box("plate", 0, 0.4, 6.0, 6.4, 0.11, 0.115)
    bh.box("lid", 0, 0.4, 6.0, 6.4, 0.115, 0.12)
    upd()
    expect("T43 a plate and the lid on it hold each other up", ck.floor_fit_check(("floor",)),
           [("lid", 0.115), ("plate", 0.11)])

    # A lid that is a support root (skipped) and covers only half the plate: it is above the plate, so it is
    # not the plate's support. The centre ray misses, so only the vertex rays and the side test could pass it.
    reset()
    bh.box("floor", -8, 8, -8, 8, -0.5, 0)
    bh.box("plate", 0, 1, 0, 1, 0.11, 0.115)
    bh.box("lid", 0.6, 1, 0, 1, 0.115, 0.12)
    upd()
    expect("T43 a skipped lid on half of a plate is not its support", ck.floor_fit_check(("floor",), skip=("lid",)),
           [("plate", 0.11)])


# ---------------------------------------------------------------- T44: cost
def t44():
    rnd = random.Random(1)
    reset()
    bh.box("floor", -40, 40, -40, 40, -0.2, 0)
    bh.cut_holes("floor", [(-20, -18, -20, -18, -0.3, 0.1), (10, 13, 5, 8, -0.3, 0.1), (25, 28, -25, -22, -0.3, 0.1)])
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
    # one dense open mesh, 0.04 m above the floor, over an area that holds band objects
    for k in range(12):
        x, y = -6 + 1.0 * (k % 4), -6 + 1.0 * (k // 4)
        bh.box(f"band_{k}", x, x + 0.4, y, y + 0.4, 0.11 + 0.01 * k, 0.5)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=316, y_segments=316, size=8.0)
    n_verts = len(bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, 0.04), verts=bm.verts)
    bh.new_obj("dense", bh._to_mesh("dense", bm))
    check(n_verts >= 90000, f"T44 fixture: the dense mesh has about 100,000 vertices, got {n_verts}")
    upd()
    n_obj = sum(1 for o in bpy.data.objects if o.type == "MESH")
    t0 = time.perf_counter()
    hits = ck.floor_fit_check(("floor",))
    dt = time.perf_counter() - t0
    print(f"TIMING floor_fit {dt:.2f} s ({n_obj} mesh objects, {n_verts} vertices in the dense mesh, {len(hits)} hits)")
    check(dt < 10, f"T44 floor_fit_check on {n_obj} objects and a {n_verts}-vertex mesh takes under 10 s, took {dt:.1f} s")


# ---------------------------------------------------------------- T45: coplanar overlaps
def t45_scene():
    reset()
    bh.box("floor", -5, 5, -5, 5, -0.5, 0)
    la = bh.box("leaf_a", 0, 1, 0, 1, 1.0, 1.001)
    lb = bh.box("leaf_b", 0.5, 1.5, 0.5, 1.5, 1.0, 1.001)
    lc = bh.box("leaf_c", 0.8, 1.8, 0, 1, 1.0, 1.001)
    va = bh.box("vine_a", 1.0, 2.0, 0.5, 1.5, 1.0, 1.001)
    vb = bh.box("vine_b", 1.5, 2.5, 0.5, 1.5, 1.0, 1.001)
    bh.box("panel", 1.2, 2.2, 1.2, 2.2, 1.0, 1.001)
    leaves = collection("leaves", [la, lb])
    collection("leaves_sub", [lc], parent=leaves)
    collection("vines", [va, vb])
    upd()


def pairs(hits):
    return {frozenset(h) for h in hits}


def t45():
    t45_scene()
    every = [("leaf_a", "leaf_b"), ("leaf_a", "leaf_c"), ("leaf_b", "leaf_c"), ("vine_a", "vine_b"),
             ("leaf_b", "vine_a"), ("leaf_c", "vine_a"), ("leaf_c", "vine_b"), ("panel", "leaf_b"),
             ("panel", "vine_a"), ("panel", "vine_b")]
    want_all = pairs(every)
    got = ck.coplanar_check()
    check(pairs(got) == want_all and len(got) == len(want_all), f"T45 coplanar_check reports every overlapping pair: want {sorted(map(sorted, want_all))}, got {got}")

    got = ck.coplanar_check(overlaps=("leaves", "vines"))
    want = want_all - pairs([("leaf_a", "leaf_b"), ("leaf_a", "leaf_c"), ("leaf_b", "leaf_c"), ("vine_a", "vine_b")])
    check(pairs(got) == want and len(got) == len(want),
          f"T45 overlaps=(leaves, vines) drops the pairs inside each, keeps panel pairs and leaf-vine pairs: want {sorted(map(sorted, want))}, got {got}")

    got = ck.coplanar_check(overlaps="leaves")
    want = want_all - pairs([("leaf_a", "leaf_b"), ("leaf_a", "leaf_c"), ("leaf_b", "leaf_c")])
    check(pairs(got) == want and len(got) == len(want),
          f"T45 overlaps='leaves' (a bare string) drops only the pairs inside leaves, child collection included: want {sorted(map(sorted, want))}, got {got}")

    got = ck.coplanar_check(overlaps=("nope",))
    check(pairs(got) == want_all and len(got) == len(want_all), f"T45 overlaps=('nope',) reports every pair, got {got}")
    got = ck.coplanar_check(overlaps=("leaves_sub",))
    check(pairs(got) == want_all, f"T45 a collection of one object skips nothing, got {got}")


# ---------------------------------------------------------------- T46: run_checks overlaps output
def three_leaves(coll="leaves"):
    objs = [bh.box("leaf_a", 0, 1, 0, 1, 1.5, 1.501), bh.box("leaf_b", 0.5, 1.5, 0.5, 1.5, 1.5, 1.501),
            bh.box("leaf_c", 0.8, 1.8, 0, 1, 1.5, 1.501)]
    return collection(coll, objs)


def t46():
    clean_room()
    three_leaves()
    upd()
    lines, code = run(floors=("floor",), overlaps=("leaves",))
    note = f"NOTE coplanar: pairs inside collection leaves not checked (3 of {mesh_count()} objects)"
    i, j = first(lines, "^NOTE coplanar"), first(lines, r"^(OK|FAIL) coplanar")
    check(lines.count(note) == 1, f"T46 NOTE line {note!r} appears once: {lines}")
    check(i is not None and j is not None and i < j, f"T46 the NOTE line comes before the coplanar line: {lines}")
    check(any(re.match(r"^OK coplanar \(", ln) for ln in lines), f"T46 coplanar passes: {lines}")
    check(code is None and lines[-1:] == ["OK run_checks"], f"T46 run_checks passes (code {code}): {lines[-3:]}")
    check(not any(ln.startswith("WARN overlaps") for ln in lines), f"T46 no overlaps WARN for a good collection: {lines}")
    lines, code = run(floors=("floor",))
    check(any(ln.startswith("FAIL coplanar") for ln in lines), f"T46 without overlaps the same leaves fail coplanar: {lines}")

    lines, code = run(floors=("floor",), overlaps=("nope",))
    check("WARN overlaps: no collection named nope" in lines, f"T46 missing-collection WARN: {lines}")
    check(any(ln.startswith("FAIL coplanar") for ln in lines), f"T46 overlaps=('nope',) leaves the coplanar hits: {lines}")
    check(not any(ln.startswith("NOTE coplanar") for ln in lines), f"T46 no NOTE for a missing collection: {lines}")

    clean_room()
    collection("empty_c")
    hid = bh.box("hid", 4, 4.5, 4, 4.5, 3.0, 3.1)
    hid.hide_render = True
    collection("hidden_c", [hid])
    upd()
    lines, code = run(floors=("floor",), overlaps=("empty_c", "hidden_c"))
    for c in ("empty_c", "hidden_c"):
        check(f"WARN overlaps: collection {c} holds no rendered mesh" in lines, f"T46 empty or hidden collection {c} WARN: {lines}")
    check(not any(ln.startswith("NOTE coplanar") for ln in lines), f"T46 no NOTE for a collection without a rendered mesh: {lines}")
    k = first(lines, "^WARN overlaps")
    check(k is not None and k < first(lines, r"^(OK|FAIL|SKIP) coplanar"), f"T46 the WARN lines come before the first check line: {lines}")

    clean_room()
    leaves = three_leaves()
    for name in ("wall_south", "floor"):
        leaves.objects.link(bpy.data.objects[name])
    upd()
    lines, code = run(floors=("floor",), overlaps=("leaves",))
    for name in ("wall_south", "floor"):
        check(f"WARN overlaps: {name} in collection leaves is a floor or wall" in lines, f"T46 floor or wall {name} in the overlap collection: {lines}")
    check(not any(re.match(r"^WARN overlaps: leaf_\w in collection", ln) for ln in lines), f"T46 a leaf is not a floor or wall: {lines}")
    check(f"NOTE coplanar: pairs inside collection leaves not checked (5 of {mesh_count()} objects)" in lines,
          f"T46 the NOTE counts the floor and the wall as members: {lines}")
    k, j = first(lines, "^WARN overlaps"), first(lines, r"^(OK|FAIL|SKIP) coplanar")
    check(k is not None and j is not None and k < j, f"T46 the WARN lines come before the first check line: {lines}")

    # The collection skips coplanar pairs only: a member that floats is still reported by floor_fit.
    clean_room()
    low = bh.box("leaf_low", 2.0, 2.5, 3.0, 3.5, 0.11, 0.111)
    collection("leaves", [low])
    upd()
    lines, code = run(floors=("floor",), overlaps=("leaves",))
    blk = block(lines, "floor_fit")
    check(blk[:1] and blk[0].startswith("FAIL floor_fit: 1 (") and "  leaf_low floating 0.110 m" in blk,
          f"T46 a member of the overlap collection is still checked by floor_fit: {lines}")
    check(code == 1 and lines[-1] == "FAIL run_checks: floor_fit", f"T46 only floor_fit fails (code {code}): {lines[-2:]}")


# ---------------------------------------------------------------- T47: hits_file
def float25():
    clean_room()
    for k in range(25):
        bh.box(f"float_{k:02d}", 0.2 + 0.4 * (k % 5), 0.3 + 0.4 * (k % 5), 1.0 + 0.4 * (k // 5),
               1.1 + 0.4 * (k // 5), 0.11, 0.3)
    upd()


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def same_path(a, b):
    return os.path.isabs(a) and os.path.realpath(a) == os.path.realpath(b)


def t47():
    base = os.path.join(tcommon.OUT, "v111")
    path = os.path.join(base, "sub", "checks.txt")
    shutil.rmtree(base, ignore_errors=True)
    float25()
    lines, code = run(floors=("floor",), exempt={"floor_fit": ["no_such"]}, hits_file=path)
    check(code == 1, f"T47 exit code 1, got {code}")
    if not check(os.path.isfile(path), f"T47 the file {path} exists, parents created"):
        return
    got = read_lines(path)
    extra = [f"  float_{k:02d} floating 0.110 m" for k in range(20, 25)]
    check(lines[:1] == ["WARN exempt floor_fit: no object named no_such"], f"T47 console starts with the exempt WARN: {lines[:2]}")
    check(lines[-1] == "FAIL run_checks: floor_fit", f"T47 console verdict: {lines[-1:]}")
    check(len(lines) >= 2 and lines[-2].startswith("NOTE full hit list: ") and same_path(lines[-2][len("NOTE full hit list: "):], path),
          f"T47 the second-to-last console line is the NOTE with the absolute path: {lines[-3:]}")
    blk = block(lines, "floor_fit")
    check(len(blk) == 22 and blk[-1] == "  ... and 5 more", f"T47 the console still shows 20 hits and '... and 5 more': {blk}")
    if not check("  ... and 5 more" in lines, f"T47 console has the '... and 5 more' line: {lines}"):
        return
    idx = lines.index("  ... and 5 more")
    want = lines[:idx] + extra + [ln for ln in lines[idx + 1:] if not ln.startswith("NOTE full hit list")]
    check(got == want, f"T47 the file holds the WARN, every status line, all 25 hits in order, the verdict:\n  want {want}\n  got  {got}")
    check(not any(ln.startswith("NOTE full hit list") for ln in got), "T47 the file has no NOTE full hit list line")
    check(not any("... and" in ln for ln in got), "T47 the file has no '... and' line")
    check(got[-1:] == [lines[-1]], f"T47 the file ends with the console's last line: {got[-1:]}")
    check(sum(1 for ln in got if re.match(r"^  float_\d\d floating 0\.110 m$", ln)) == 25, "T47 the file holds 25 hit lines")

    # A relative path prints the absolute path.
    here = os.getcwd()
    rel = os.path.join("v111", "rel", "checks.txt")
    try:
        os.chdir(tcommon.OUT)
        lines, code = run(floors=("floor",), hits_file=rel)
    finally:
        os.chdir(here)
    want_path = os.path.join(tcommon.OUT, rel)
    check(os.path.isfile(want_path), f"T47 a relative hits_file is written relative to the current folder: {want_path}")
    note = [ln for ln in lines if ln.startswith("NOTE full hit list: ")]
    check(len(note) == 1 and same_path(note[0][len("NOTE full hit list: "):], want_path), f"T47 a relative path prints the absolute path: {note}")

    # The clean room, same path (a path-like this time): the old list does not outlive a clean run.
    clean_room()
    lines, code = run(floors=("floor",), hits_file=__import__("pathlib").Path(path))
    check(code is None and lines[-1] == "OK run_checks", f"T47 clean room passes (code {code}): {lines[-2:]}")
    got = read_lines(path)
    check(got and all(re.match(r"^(OK|SKIP) ", ln) for ln in got) and got[-1] == "OK run_checks",
          f"T47 the clean run overwrites the file with only OK and SKIP lines: {got}")
    check(not any("float_" in ln for ln in got), "T47 no hit of the old run is left in the file")
    check(any(ln.startswith("NOTE full hit list: ") for ln in lines), f"T47 a clean run still prints the NOTE line: {lines}")

    # The NOTE line of run_checks is in the file; the lines printed inside a check are not.
    clean_room()
    three_leaves()
    bh.seg("wall_angle", (5, 0), (5.9, 0.55), 0.1, 0, 2.6)
    upd()
    lines, code = run(floors=("floor",), overlaps=("leaves",), hits_file=path)
    got = read_lines(path)
    note = f"NOTE coplanar: pairs inside collection leaves not checked (3 of {mesh_count()} objects)"
    check(note in got, f"T47 the file holds the NOTE coplanar line: {got}")
    check(any(ln.startswith("NOTE wall_gaps:") for ln in lines), f"T47 fixture: the console shows NOTE wall_gaps: {lines}")
    check(not any(ln.startswith("NOTE wall_gaps") for ln in got), f"T47 the file leaves out the NOTE printed inside a check: {got}")
    check(got.index(note) < first(got, r"^(OK|FAIL|SKIP) coplanar"), f"T47 the NOTE line is before the first check line in the file: {got}")

    # A check that raises: the FAIL line with the error is in the file.
    clean_room()
    real = ck.floor_fit_check

    def boom(*a, **kw):
        raise RuntimeError("boom")

    ck.floor_fit_check = boom
    try:
        lines, code = run(floors=("floor",), hits_file=path)
    finally:
        ck.floor_fit_check = real
    got = read_lines(path)
    check("FAIL floor_fit: error RuntimeError: boom" in got, f"T47 the file holds the error status line: {got}")
    check(code == 1 and got[-1] == "FAIL run_checks: floor_fit", f"T47 the file ends with the verdict (code {code}): {got[-2:]}")

    # Without hits_file: no file, no NOTE line.
    shutil.rmtree(base, ignore_errors=True)
    float25()
    lines, code = run(floors=("floor",))
    check(not os.path.exists(base), f"T47 without hits_file nothing is written under {base}")
    check(not any("full hit list" in ln for ln in lines), f"T47 without hits_file there is no NOTE full hit list line: {lines[-3:]}")
    blk = block(lines, "floor_fit")
    check(len(blk) == 22 and blk[-1] == "  ... and 5 more", f"T47 without hits_file the console is unchanged: {blk}")
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------- T49: finishes and wall_gaps
def t49():
    reset()
    bh.box("floor", -1, 5, -1, 2, -0.2, 0)
    bh.box("wall_a", 0, 2, 0, 0.1, 0, 2.6)
    bh.box("wall_b", 2.2, 4, 0, 0.1, 0, 2.6)
    bh.box("wt_fill", 2.0, 2.2, 0, 0.1, 0, 2.6)
    upd()

    def gaps(**kw):
        lines, _ = run(floors=("floor",), **kw)
        return [re.sub(r"\(\d+\.\d\d s\)", "(t s)", ln) for ln in block(lines, "wall_gaps")]

    without = gaps()
    with_f = gaps(finishes=("wt_",))
    check(with_f == without, f"T49 the wall_gaps block is the same with finishes: without {without}, with {with_f}")
    check(with_f == ["FAIL wall_gaps: 1 (t s)", "  wall_a wall_b gap 0.200 m"],
          f"T49 the gap between wall_a and wall_b is reported although wt_fill fills it: {with_f}")
    expect("T49 wall_gap_check alone", ck.wall_gap_check(), [("wall_a", "wall_b", "gap", 0.2)])


# ---------------------------------------------------------------- T50: coplanar detail lines in the hits file
DETAIL = re.compile(r"^    plane n=\((-?\d+\.\d{3}), (-?\d+\.\d{3}), (-?\d+\.\d{3})\) d=(-?\d+\.\d{3}) m; "
                    r"overlap x (-?\d+\.\d{3})-(-?\d+\.\d{3}) y (-?\d+\.\d{3})-(-?\d+\.\d{3}) "
                    r"z (-?\d+\.\d{3})-(-?\d+\.\d{3}) m; area (\d+\.\d{4}) m2$")


def t50():
    base = os.path.join(tcommon.OUT, "v111")
    path = os.path.join(base, "detail", "checks.txt")
    shutil.rmtree(base, ignore_errors=True)
    clean_room()
    # Two tops on the plane z = 0.3; the overlap is x 0.1 to 0.5, y 0.2 to 0.4 (0.08 m2). Side and bottom faces
    # do not share a plane.
    bh.box("box_a", 0.0, 0.5, 0.0, 0.4, 0.0, 0.3)
    bh.box("box_b", 0.1, 0.6, 0.2, 0.6, 0.1, 0.3)
    upd()
    pairs_got = ck.coplanar_check()
    check(len(pairs_got) == 1 and all(isinstance(h, tuple) and len(h) == 2 for h in pairs_got)
          and set(pairs_got[0]) == {"box_a", "box_b"}, f"T50 coplanar_check still returns a list of 2-tuples: {pairs_got}")
    lines, code = run(floors=("floor",), hits_file=path)
    check(not any(ln.startswith("    ") for ln in lines), f"T50 the console shows no detail line: {lines}")
    blk = block(lines, "coplanar")
    check(len(blk) == 2 and re.match(r"^  box_[ab] box_[ab]$", blk[1]), f"T50 the console shows the header and the pair line only: {blk}")
    if not check(os.path.isfile(path), "T50 the hits file exists"):
        return
    got = read_lines(path)
    i = first(got, r"^  box_[ab] box_[ab]$")
    if not check(i is not None and i + 1 < len(got), f"T50 the file holds the pair line: {got}"):
        return
    m = DETAIL.match(got[i + 1])
    if not check(m, f"T50 the next line is the detail line: {got[i + 1]!r}"):
        return
    v = [float(x) for x in m.groups()]
    want = [0.0, 0.0, 1.0, 0.3, 0.1, 0.5, 0.2, 0.4, 0.3, 0.3, 0.08]
    check(all(abs(a - b) <= 1e-3 for a, b in zip(v, want)), f"T50 detail values (n, d, x, y, z, area) want {want}, got {v}")
    check(sum(1 for ln in got if ln.startswith("    ")) == 1, "T50 one detail line for one pair")
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------- T51: flipped_check on a thin box far from the origin
def t51():
    # Verified in Blender 5.2 on the v1.1.0 code: the correct box at (7, 0, 0) and at (0, 7, 0) is not reported, but at
    # (4.12, 4.12, 4.12), 7.1 m from the origin, a correct 1.2 mm x 0.2 m x 0.009 m box reads inside-out.
    c = 7 / 1.7
    for label, (a, b, d) in (("1.2 mm thick along y", (0.2, 0.0012, 0.009)), ("1.2 mm thick along z", (0.2, 0.009, 0.0012))):
        for flip in (False, True):
            reset()
            ob = bh.box("thin", c, c + a, c, c + b, c, c + d)
            if flip:
                ob.data.flip_normals()
            upd()
            got = ck.flipped_check()
            want = [("thin", "inside-out")] if flip else []
            expect(f"T51 {label}, {'flipped' if flip else 'wound correctly'}, 7.1 m from the origin", got, want)


CASES = (t42, t42b, t43, t44, t45, t46, t47, t49, t50, t51)


def main():
    for fn in CASES:
        try:
            fn()
        except Exception as e:
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finish("bl_v111")


main()
