"""Blender test: mannequin builds a figure of 20+ prefixed objects, scales with U, and ik reaches or clamps."""
import math

import bpy
from mathutils import Vector

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, close, extents, finish

import bhelpers as bh
import mannequin as mq  # imported before set_units on purpose: U must be read at call time


def man_objs(prefix):
    return [o for o in bpy.data.objects if o.name.startswith(prefix)]


def top(objs):
    return max(extents(o)[1][2] for o in objs if o.type == "MESH")


def scaled_pose(pose, k):
    p = dict(pose)
    for key in ("root", "ankles", "rw", "lw"):
        v = pose[key]
        p[key] = tuple(tuple(c * k for c in e) for e in v) if isinstance(v[0], (tuple, list)) else tuple(c * k for c in v)
    if pose.get("pz") is not None:
        p["pz"] = pose["pz"] * k
    return p


def main():
    bh.set_units("m")
    bh.clear_scene()
    mq.mannequin(mq.EXAMPLE_POSE, height=1.78)
    objs_m = man_objs("man_")
    check(len(objs_m) >= 20, f"mannequin builds 20+ man_* objects, got {len(objs_m)}")
    h_m = top(objs_m)
    check(abs(h_m - 1.78) < 0.15, f"mannequin height in metres about 1.78, got {h_m}")

    bh.clear_scene()
    mq.mannequin(mq.EXAMPLE_POSE, height=1.6, prefix="fig_")
    check(len(man_objs("fig_")) >= 20 and not man_objs("man_"), "custom prefix is used for every object")

    bh.set_units("ft")
    bh.clear_scene()
    k = 1 / 0.3048
    mq.mannequin(scaled_pose(mq.EXAMPLE_POSE, k), height=1.78 * k)
    objs_f = man_objs("man_")
    check(len(objs_f) == len(objs_m), f"same object count in feet ({len(objs_f)} vs {len(objs_m)})")
    h_f = top(objs_f)
    check(abs(h_f - h_m) < 0.02, f"feet figure has the same world height: {h_f} vs {h_m}")
    xs = [extents(o)[0][0] for o in objs_f]
    check(min(xs) > 0.5 and max(xs) < 2.0, "figure stays near the scaled root position in world metres")

    bh.set_units("m")
    a, t, l1, l2 = (0, 0, 0), (0.3, 0.2, 0.1), 0.3, 0.3
    elbow, end = mq.ik(a, t, l1, l2, (0, -1, 0))
    check(close((Vector(elbow) - Vector(a)).length, l1, 1e-5), "ik: first bone length")
    check(close((Vector(end) - Vector(elbow)).length, l2, 1e-5), "ik: second bone length")
    check((Vector(end) - Vector(t)).length < 1e-5, "ik: reachable target is reached")
    elbow, end = mq.ik(a, (3, 0, 0), l1, l2, (0, 1, 0))
    check(Vector(end).x < l1 + l2 + 1e-6 and Vector(end).x > l1 + l2 - 1e-2, f"ik: out-of-reach clamps, end {tuple(end)}")
    check(Vector(elbow).y >= -1e-6, "ik: joint bends toward the pole")
    finish("bl_mannequin")


main()
