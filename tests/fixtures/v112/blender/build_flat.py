"""Synthetic flat for eval E13 (v1.1.2): a hall and a bathroom under one roof slab. Views: persp, plan.

The scene holds six coplanar hits that the checks report and no other defect. Four wall plates lie inside the walls
with their tops on the wall tops, under the roof slab (buried). The two dropped ceilings overlap by 0.3 m in plan, with
their bottoms in the open and their tops under an insulation box (partly buried). A blocking strip inside the hall
ceiling has its top on the ceiling's top, under the insulation (buried).

An eval copies the skill's scripts/ folder to blender/lib/v1.1.2 beside this file; no lib is stored here.
"""
import argparse
import os
import sys

LIB = "v1.1.2"   # the skill version this script is pinned to (SKILL.md, Project lib)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", LIB))

import bhelpers as bh
from bhelpers import box, srgb, principled
from checks import run_checks

bh.set_units("m")
VIEWER = None   # viewer's height in project units; None is 5'-7"
EYE = bh.eye_height(VIEWER)

# ---------------------------------------------------------------- constants (metres)
ROOM = (0.0, 6.1, 0.0, 3.0)          # x0, x1, y0, y1 of the interior: the hall in the west, the bathroom in the east
WALL_T, WALL_H = 0.10, 2.60
VIEWS = {
    "persp": dict(interior=True, loc=(0.5, 0.5, EYE), target=(3.05, 1.5, 2.4), lens=20),
    "plan": dict(plan=True, center=(3.05, 1.5), width=8.0, cut=1.2, drop=()),
}


def build(opts):
    x0, x1, y0, y1 = ROOM
    t = WALL_T
    floor = principled("floor", srgb("#b9a58c"), 0.45)
    wall = principled("wall", srgb("#e8e4dc"), 0.8)
    slab = principled("slab", srgb("#c8c8c8"), 0.9)
    ceil = principled("ceil", srgb("#f2efe8"), 0.8)
    wood = bh.wood_material("wood")
    foam = principled("foam", srgb("#e6d77a"), 0.9)

    box("floor", x0 - t, x1 + t, y0 - t, y1 + t, -0.10, 0.0, floor)
    for name, rect in (("s", (x0 - t, x1 + t, y0 - t, y0)), ("n", (x0 - t, x1 + t, y1, y1 + t)),
                       ("w", (x0 - t, x0, y0, y1)), ("e", (x1, x1 + t, y0, y1))):
        box(f"wall_{name}", *rect, 0.0, WALL_H, wall)
    box("roof_slab", x0 - t, x1 + t, y0 - t, y1 + t, WALL_H, WALL_H + 0.20, slab)

    # wall plates: inside each wall, 10 mm in from both faces, top on the wall top
    box("plate_n", 0.5, 5.5, y1 + 0.01, y1 + t - 0.01, 2.50, WALL_H, wood)
    box("plate_s", 0.5, 5.5, y0 - t + 0.01, y0 - 0.01, 2.50, WALL_H, wood)
    box("plate_e", x1 + 0.01, x1 + t - 0.01, 0.5, 2.5, 2.50, WALL_H, wood)
    box("plate_w", x0 - t + 0.01, x0 - 0.01, 0.5, 2.5, 2.50, WALL_H, wood)

    # dropped ceilings, 0.3 m of overlap in plan (x 2.9 to 3.2)
    box("ceiling_hall", 0.2, 3.2, 0.2, 2.8, 2.40, 2.45, ceil)
    box("ceiling_bath", 2.9, 5.9, 0.2, 2.8, 2.40, 2.45, ceil)
    # blocking inside the hall ceiling, top on the ceiling's top
    box("blocking_h", 0.6, 1.0, 0.6, 2.4, 2.42, 2.45, wood)
    # insulation above both ceilings, under the roof slab, clear of the walls
    box("insul", 0.5, 5.5, 0.5, 2.5, 2.45, WALL_H, foam)

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
    bh.setup_cycles(args.samples, gpu=args.gpu)
    bh.add_camera(VIEWS[args.view], args.res)
    run_checks(floors=("floor",), interior=VIEWS[args.view].get("interior"))
    bh.render(args.out or f"out/{args.view}.png")


if __name__ == "__main__":
    main()
