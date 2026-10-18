"""Neutral clay mannequin posed with two-bone IK, for ergonomic and clearance studies (Blender).

Needs bhelpers.py on the path. Pose coordinates and height are in project units; proportions are built in metres.
"""
import math

import bpy
import bmesh
from mathutils import Matrix, Vector

import bhelpers
from bhelpers import new_obj, principled


def _ellipsoid(name, center, radii, xax, yax, zax, mat):
    """Ellipsoid with its axes along xax, yax, zax."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = new_obj(name, me, mat)
    xa, ya, za = (Vector(v).normalized() * r for v, r in zip((xax, yax, zax), radii))
    ob.matrix_world = Matrix(((xa.x, ya.x, za.x, center[0]), (xa.y, ya.y, za.y, center[1]),
                              (xa.z, ya.z, za.z, center[2]), (0, 0, 0, 1)))
    me.shade_smooth()
    return ob


def _limb(name, p, q, r1, r2, mat):
    """Tapered limb from p to q with ball joints at both ends."""
    p, q = Vector(p), Vector(q)
    d = q - p
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=r1, radius2=r2, depth=d.length)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = new_obj(name, me, mat)
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    ob.location = (p + q) / 2
    me.shade_smooth()
    for nm, c, r in (("a", p, r1), ("b", q, r2)):
        _ellipsoid(f"{name}_{nm}", c, (r, r, r), (1, 0, 0), (0, 1, 0), (0, 0, 1), mat)


def ik(a, t, l1, l2, pole):
    """Two-bone IK: joint (elbow/knee) and end point for root a reaching t; the joint bends toward pole.

    Out-of-reach targets are clamped to full extension.
    """
    a, t, pole = Vector(a), Vector(t), Vector(pole)
    d = t - a
    dist = min(d.length, l1 + l2 - 1e-4)
    dn = d.normalized()
    t2 = a + dn * dist
    ca = max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)))
    pp = (pole - dn * pole.dot(dn)).normalized()
    elbow = a + dn * (l1 * ca) + pp * (l1 * math.sqrt(1 - ca * ca))
    return elbow, t2


# Pose format (keep project poses in the project script). EXAMPLE_POSE is in metres; a pose is in project units.
#   root (x, y) pelvis position; face (fx, fy) facing direction; pz pelvis height when seated, None = standing;
#   bend torso lean forward (deg); head head tilt (deg, + = down); raise_r optional right-shoulder lift;
#   ankles ((x, y), (x, y)); rw / lw ((wrist xyz), (fingertip xyz)); rpole / lpole elbow bend direction;
#   floor_z optional floor height under the feet (default 0), for a figure on an upper floor.
EXAMPLE_POSE = dict(root=(1.0, 0.75), face=(1, 0), pz=None, bend=18, head=28,
                    ankles=((0.99, 0.66), (0.99, 0.84)),
                    rw=((1.37, 0.715, 1.105), (1.44, 0.74, 1.085)), rpole=(0.0, -1.0, -0.15),
                    lw=((1.37, 0.79, 1.105), (1.44, 0.765, 1.085)), lpole=(0.0, 1.0, -0.15))


def mannequin(pose, height=None, mat=None, prefix="man_"):
    """Neutral clay figure of the given height in pose (see EXAMPLE_POSE); object names start with prefix.

    height defaults to 1.78 m. Proportions scale with height; arms and legs are solved with ik. Run clash_check
    afterwards. EXAMPLE_POSE is in metres: a project in feet writes its own pose.
    """
    u = bhelpers.U
    height = 1.78 / u if height is None else height
    sc3 = lambda v: tuple(c * u for c in v)
    P = dict(pose, root=sc3(pose["root"]), ankles=tuple(sc3(a) for a in pose["ankles"]),
             rw=tuple(sc3(a) for a in pose["rw"]), lw=tuple(sc3(a) for a in pose["lw"]),
             raise_r=pose.get("raise_r", 0.0) * u, floor_z=pose.get("floor_z", 0.0) * u, pz=None if pose.get("pz") is None else pose["pz"] * u)
    K = height * u / 1.78
    m = mat or principled("mannequin", (0.55, 0.54, 0.52), 0.55)
    z = Vector((0, 0, 1))
    f = Vector((*P["face"], 0)).normalized()
    r = Vector((f.y, -f.x, 0))                                   # figure's right
    b = math.radians(P["bend"])
    sp = (z * math.cos(b) + f * math.sin(b)).normalized()        # spine
    fs = (f * math.cos(b) - z * math.sin(b)).normalized()        # chest forward
    pel = Vector((P["root"][0], P["root"][1], P["pz"] if P["pz"] is not None else P["floor_z"] + 0.95 * K))
    _ellipsoid(f"{prefix}pelvis", pel + sp * (0.03 * K), tuple(v * K for v in (0.165, 0.105, 0.12)), r, fs, sp, m)
    _ellipsoid(f"{prefix}abdomen", pel + sp * (0.20 * K), tuple(v * K for v in (0.145, 0.098, 0.13)), r, fs, sp, m)
    _ellipsoid(f"{prefix}chest", pel + sp * (0.37 * K), tuple(v * K for v in (0.175, 0.112, 0.17)), r, fs, sp, m)
    neck = pel + sp * (0.57 * K)
    sh = {s_: pel + sp * (0.50 * K) + r * (0.19 * K * s_) for s_ in (1, -1)}
    sh[1] = sh[1] + z * P["raise_r"]
    _limb(f"{prefix}shoulders", sh[-1], sh[1], 0.055 * K, 0.055 * K, m)
    hb = math.radians(P["head"])
    hd = (sp * math.cos(hb) + fs * math.sin(hb)).normalized()
    hf = (fs * math.cos(hb) - sp * math.sin(hb)).normalized()
    _limb(f"{prefix}neck", neck - sp * (0.03 * K), neck + hd * (0.06 * K), 0.052 * K, 0.048 * K, m)
    _ellipsoid(f"{prefix}head", neck + hd * (0.17 * K), tuple(v * K for v in (0.078, 0.098, 0.115)), r, hf, hd, m)
    for side, key, pk in ((1, "rw", "rpole"), (-1, "lw", "lpole")):
        wrist, tip = P[key]
        el, wr = ik(sh[side], wrist, 0.29 * K, 0.26 * K, P[pk])
        _limb(f"{prefix}uarm{side}", sh[side], el, 0.046 * K, 0.037 * K, m)
        _limb(f"{prefix}farm{side}", el, wr, 0.036 * K, 0.026 * K, m)
        hdir = (Vector(tip) - wr).normalized()
        side_ax = hdir.cross(z).normalized() if abs(hdir.dot(z)) < 0.95 else r
        _ellipsoid(f"{prefix}hand{side}", wr + hdir * (0.08 * K), tuple(v * K for v in (0.042, 0.018, 0.085)),
                   side_ax, side_ax.cross(hdir), hdir, m)
    root = P["root"]
    by_side = sorted(P["ankles"], key=lambda a: (a[0] - root[0]) * r.x + (a[1] - root[1]) * r.y, reverse=True)
    for side, (ax, ay) in zip((1, -1), by_side):
        hip = pel + r * (0.09 * K * side) - sp * (0.03 * K)
        kn, ank = ik(hip, Vector((ax, ay, P["floor_z"] + 0.075 * K)), 0.44 * K, 0.42 * K, f + z * 0.3)
        _limb(f"{prefix}thigh{side}", hip, kn, 0.075 * K, 0.052 * K, m)
        _limb(f"{prefix}shin{side}", kn, ank, 0.050 * K, 0.034 * K, m)
        _ellipsoid(f"{prefix}foot{side}", ank + f * (0.07 * K) - z * (0.035 * K),
                   tuple(v * K for v in (0.045, 0.125, 0.038)), r, f, z, m)
