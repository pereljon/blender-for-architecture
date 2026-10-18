"""Blender test: Revision 4 behavior (T11, T12) from the scripts contract."""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, finish

import bhelpers as bh
import checks


def reset(unit="m"):
    bh.set_units(unit)
    bh.clear_scene()


# ---------------------------------------------------------------- T11: perspective hide is camera-only
def t11():
    persp = dict(loc=(3, -4, 1.5), target=(0, 0, 1), hide=("wall_s",))
    plan = dict(plan=True, center=(0, 0), width=6.0, cut=1.2, hide=("wall_s",))
    for kind, view in (("perspective", persp), ("plan", plan)):
        reset()
        bh.setup_cycles(8, gpu=False)
        bh.box("wall_s", -2, 2, -2.1, -2.0, 0, 2.4)
        bh.box("wall_n", -2, 2, 2.0, 2.1, 0, 2.4)
        bh.add_camera(view, 160)
        ws, wn = bpy.data.objects["wall_s"], bpy.data.objects["wall_n"]
        if kind == "perspective":
            check(ws.visible_camera is False, "T11 perspective: wall_s visible_camera is False")
            check(ws.hide_render is False, "T11 perspective: wall_s hide_render stays False")
        else:
            check(ws.hide_render is True, "T11 plan: wall_s hide_render is True")
        check(wn.visible_camera is True and wn.hide_render is False,
              f"T11 {kind}: wall_n is unaffected (visible_camera {wn.visible_camera}, hide_render {wn.hide_render})")


# ---------------------------------------------------------------- T12: clash_check on touching boxes
def t12():
    for gap, expect in ((0.0, True), (0.001, False)):
        reset()
        bh.box("man_a", 0, 1, 0, 1, 0, 1)
        bh.box("blk_b", 1 + gap, 2 + gap, 0, 1, 0, 1)
        hits = checks.clash_check(("man_",), ("blk_",))
        if expect:
            check(("man_a", "blk_b") in hits, f"T12 boxes touching face to face are a hit, got {hits}")
        else:
            check(hits == [], f"T12 boxes 1 mm apart report nothing, got {hits}")


def main():
    t11()
    t12()
    finish("bl_rev4")


main()
