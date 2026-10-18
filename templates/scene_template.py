"""Starting scene for a scripted render: a 3 x 4 m room with a door opening, a counter and one study option.

Copy this file into the project's render folder and copy scripts/ to lib/ beside it. Run:
  /Applications/Blender.app/Contents/MacOS/Blender --factory-startup -b --python-exit-code 1 -P scene.py -- \
      --view persp --res 800 --samples 48 --gpu --out out/persp.png
Prints DONE <path> when the render is written. Views: persp, plan. Iterate at 800 px / 48 samples.
--export-pieces PATH builds the scene, writes the tile pieces JSON to PATH, prints DONE <PATH> and skips the render.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))   # the project copies scripts/ into lib/

import bhelpers as bh
from bhelpers import box, cyl, srgb, principled
from checks import clash_check, coplanar_check, fail_on

bh.set_units("m")

# ---------------------------------------------------------------- constants (project values live here)
ROOM = (0.0, 3.0, 0.0, 4.0)          # x0, x1, y0, y1 of the room interior
WALL_T, WALL_H = 0.10, 2.60
DOOR = (0.9, 1.8, 2.1)               # x0, x1, height of the door opening in the south wall
VIEWS = {
    "persp": dict(loc=(2.7, 3.7, 1.5), target=(1.0, 0.6, 1.0), lens=20),
    "plan": dict(plan=True, center=(1.5, 2.0), width=6.0, cut=1.2, drop=("opt_",)),
}


def build(opts):
    """Make the room, the counter and the object for the chosen option."""
    x0, x1, y0, y1 = ROOM
    t = WALL_T
    floor = principled("floor", srgb("#b9a58c"), 0.45)
    wall = principled("wall", srgb("#e8e4dc"), 0.8)
    wood = bh.wood_material("wood")
    box("floor", x0 - t, x1 + t, y0 - t, y1 + t, -0.10, 0.0, floor)
    for name, rect in (("south", (x0 - t, x1 + t, y0 - t, y0)), ("north", (x0 - t, x1 + t, y1, y1 + t)),
                       ("west", (x0 - t, x0, y0, y1)), ("east", (x1, x1 + t, y0, y1))):
        box(f"wall_{name}", *rect, 0.0, WALL_H, wall)
    bh.cut_holes("wall_south", [(DOOR[0], DOOR[1], y0 - t - 0.1, y0 + 0.1, -0.05, DOOR[2])])
    box("counter", 1.6, 2.9, 0.1 + y0, 0.7 + y0, -0.005, 0.9, wood, bevel=0.005)    # sunk 5 mm so the base is not coplanar with the floor
    if opts.option == "a":
        box("opt_shelf", 0.1, 0.4, 1.0, 2.6, 0.9, 1.9, wood)
    else:
        cyl("opt_stool", 0.7, 3.2, -0.005, 0.45, 0.2, wood)
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
    fail_on(coplanar_check(("floor", "counter", "opt_")), "coplanar")      # walls butt at the corners by design
    bh.setup_cycles(args.samples, gpu=args.gpu)
    bh.add_camera(VIEWS[args.view], args.res)
    bh.render(args.out or f"out/{args.view}.png")


if __name__ == "__main__":
    main()
