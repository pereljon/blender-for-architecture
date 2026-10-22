"""Synthetic 5 x 4 m room for an eval fixture. Views: persp, plan.

This is the synthetic scene of eval E12 (v1.1.1): three planted defects (a floating shelf, a raised bed, a slab coplanar
with the floor). An eval copies the skill's scripts/ folder to lib/v1.1.1 beside this file; no lib is stored here.
"""
import argparse
import os
import sys

LIB = "v1.1.1"   # the skill version this script is pinned to (SKILL.md, Project lib)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", LIB))

import bhelpers as bh
from bhelpers import box, cyl, srgb, principled
from checks import clash_check, fail_on, run_checks

bh.set_units("m")
VIEWER = None   # viewer's height in project units; None is 5'-7"
EYE = bh.eye_height(VIEWER)

# ---------------------------------------------------------------- constants (metres)
ROOM = (0.0, 5.0, 0.0, 4.0)          # x0, x1, y0, y1 of the room interior
WALL_T, WALL_H = 0.10, 2.60
VIEWS = {
    "persp": dict(interior=True, loc=(4.7, 0.6, EYE), target=(2.0, 2.8, 0.9), lens=20),
    "plan": dict(plan=True, center=(2.5, 2.0), width=7.0, cut=1.2, drop=()),
}


def join(name, objs):
    import bpy
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def build(opts):
    import bpy
    x0, x1, y0, y1 = ROOM
    t = WALL_T
    floor = principled("floor", srgb("#b9a58c"), 0.45)
    wall = principled("wall", srgb("#e8e4dc"), 0.8)
    wood = bh.wood_material("wood")
    tile = principled("tile", srgb("#9fb8c4"), 0.3)
    green = principled("green", srgb("#4f8a3c"), 0.6)
    fab = principled("fab", srgb("#8a8fa8"), 0.9)
    metal = principled("metal", srgb("#c9a227"), 0.3, metal=1.0)

    box("floor", x0 - t, x1 + t, y0 - t, y1 + t, -0.10, 0.0, floor)
    for name, rect in (("s", (x0 - t, x1 + t, y0 - t, y0)), ("n", (x0 - t, x1 + t, y1, y1 + t)),
                       ("w", (x0 - t, x0, y0, y1)), ("e", (x1, x1 + t, y0, y1))):
        box(f"wall_{name}", *rect, 0.0, WALL_H, wall)

    # tile layer on the inside face of wall_n (y = 4.0), 10 mm thick
    box("wt_vanity", 1.0, 2.6, y1 - 0.01, y1, 0.0, 1.4, tile)
    # wall-hung vanity: base 0.45 m, back on the tile, drawer front 18 mm
    box("vanity_carcass", 1.2, 2.4, 3.4, y1 - 0.01, 0.45, 0.90, wood)
    box("vanity_drawer", 1.2, 2.4, 3.4 - 0.018, 3.4, 0.50, 0.85, wood)

    # shelf unit standing on the floor, boxes resting off-centre on two shelves
    parts = [box("p1", 3.3, 3.32, 3.3, 3.7, 0.0, 1.2, wood), box("p2", 4.18, 4.2, 3.3, 3.7, 0.0, 1.2, wood),
             box("p3", 3.32, 4.18, 3.68, 3.7, 0.0, 1.2, wood),
             box("b1", 3.32, 4.18, 3.3, 3.68, 0.0, 0.02, wood), box("b2", 3.32, 4.18, 3.3, 3.68, 0.40, 0.42, wood),
             box("b3", 3.32, 4.18, 3.3, 3.68, 0.80, 0.82, wood)]
    join("shelf", parts)
    box("shelf_box_a", 3.34, 3.64, 3.40, 3.64, 0.42, 0.72, fab)
    box("shelf_box_b", 3.80, 4.14, 3.42, 3.66, 0.82, 1.10, fab)

    # cymbal stand: base + pole, cymbal rests on the pole top, off its own centre
    base = cyl("sb", 1.0, 1.0, 0.0, 0.03, 0.20, metal)
    pole = cyl("sp", 1.0, 1.0, 0.03, 1.40, 0.012, metal)
    join("cymbal_stand", [base, pole])
    cyl("cymbal", 1.07, 1.0, 1.40, 1.404, 0.18, metal)

    # plant: six overlapping coplanar leaf planes in collection foliage
    cyl("plant_pot", 4.2, 1.0, 0.0, 0.30, 0.20, wood)
    coll = bpy.data.collections.new("foliage")
    bpy.context.scene.collection.children.link(coll)
    for i in range(6):
        ob = box(f"leaf_{i}", 4.0 + 0.05 * i, 4.2 + 0.05 * i, 0.9 + 0.03 * i, 1.1 + 0.03 * i, 0.30, 0.302, green)
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)

    # DEFECT 1: wall shelf floating 0.08 m above the floor
    box("shelf_float", 4.6, 4.95, 2.0, 2.8, 0.08, 0.10, wood)
    # DEFECT 2: bed raised 0.08 m, head on wall_s; nightstand on the floor, top level with the bed top
    box("bed", 2.0, 3.6, y0, 2.0, 0.08, 0.50, fab)
    box("nightstand", 3.6, 4.0, y0, 0.4, 0.0, 0.50, wood)
    # DEFECT 3: slab coplanar with the floor top, overlapping the floor
    box("box_overlap", 0.3, 0.9, 2.4, 3.0, -0.05, 0.0, wood)

    bh.room_fill_lights({"main": ROOM}, WALL_H)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", choices=sorted(VIEWS), default="persp")
    ap.add_argument("--res", type=int, default=800)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--option", choices=("a", "b"), default="a")
    ap.add_argument("--export-pieces", default=None)
    args = ap.parse_args(argv)
    bh.clear_scene()
    build(args)
    if args.export_pieces:
        path = os.path.abspath(args.export_pieces)
        bh.export_pieces(path)
        print(f"DONE {path}")
        return
    fail_on(clash_check(("counter", "opt_"), ("wall_",)), "clash")
    bh.setup_cycles(args.samples, gpu=args.gpu)
    bh.add_camera(VIEWS[args.view], args.res)
    # foliage: leaf cards overlap on one plane by design; wt_: tile layer on wall_n
    run_checks(floors=("floor",), interior=VIEWS[args.view].get("interior"),
               overlaps=("foliage",), finishes=("wt_",),
               hits_file=f"scratch/checks_{args.view}.txt")
    bh.render(args.out or f"out/{args.view}.png")


if __name__ == "__main__":
    main()
