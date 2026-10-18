"""Pre-render scene checks (Blender): surface clashes, coplanar overlaps, and a pass/fail gate for the build script."""
import sys
from collections import Counter

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

_RAY = Vector((0.5773, 0.3011, 0.7561)).normalized()    # skewed so a ray rarely grazes an edge or vertex


def _prefixes(p):
    return (p,) if isinstance(p, str) else tuple(p)


def _geom(ob, dg):
    """World-space BVH, vertices and closed flag of an evaluated object (modifiers and curves included)."""
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    me.transform(ob.matrix_world)
    vs = [v.co.copy() for v in me.vertices]
    tree = BVHTree.FromPolygons(vs, [p.vertices[:] for p in me.polygons])
    edges = Counter(lp.edge_index for lp in me.loops)
    closed = bool(edges) and all(c % 2 == 0 for c in edges.values())
    e.to_mesh_clear()
    return tree, vs, closed


def _inside(tree, p):
    """True when p is inside the closed mesh of tree: an odd number of surface crossings along a ray."""
    n, o = 0, p.copy()
    while n < 1000:
        hit = tree.ray_cast(o, _RAY)
        if hit[0] is None:
            break
        n += 1
        o = hit[0] + _RAY * 1e-4
    return n % 2 == 1


def clash_check(a_prefixes=("man_",), b_prefixes=None, ignore=()):
    """Pairs (a_name, b_name) where an a* object overlaps a b* object, or has a vertex inside it.

    b_prefixes None or empty means every other visible mesh or curve not in a and not ignored.
    Call after the build, before rendering; fail the render or re-pose when the list is not empty.
    The vertex-inside test needs a closed b mesh, so it is skipped for a b with open boundary edges.
    """
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE") and not o.hide_render]
    pa, pb, pi = _prefixes(a_prefixes), _prefixes(b_prefixes or ()), _prefixes(ignore)
    A = [o for o in objs if o.name.startswith(pa)]
    B = [o for o in objs if o not in A and (not pb or o.name.startswith(pb)) and not o.name.startswith(pi)]
    gb = {o.name: _geom(o, dg) for o in B}
    box = {}
    for n, (_, vs, _) in gb.items():
        box[n] = (Vector(map(min, zip(*vs))), Vector(map(max, zip(*vs)))) if vs else None
    hits = []
    for a in A:
        ta, va, _ = _geom(a, dg)
        for b in B:
            tb, _, closed = gb[b.name]
            if ta.overlap(tb):
                hits.append((a.name, b.name))
            elif closed and box[b.name]:
                lo, hi = box[b.name]
                near = [v for v in va if all(lo[i] <= v[i] <= hi[i] for i in range(3))]
                if any(_inside(tb, v) for v in near):
                    hits.append((a.name, b.name))
    return hits


def _tris(ob, dg, min_area):
    """World-space triangles (a, b, c, unit normal, area, bbox) of faces with area of at least min_area."""
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    me.calc_loop_triangles()
    vs = [ob.matrix_world @ v.co for v in me.vertices]
    raw, area = [], Counter()
    for t in me.loop_triangles:
        a, b, c = (vs[i] for i in t.vertices)
        n = (b - a).cross(c - a)
        if n.length > 0:
            raw.append((t.polygon_index, a, b, c, n.normalized(), n.length / 2))
            area[t.polygon_index] += n.length / 2
    e.to_mesh_clear()
    return [(a, b, c, n, ar, (Vector(map(min, zip(a, b, c))), Vector(map(max, zip(a, b, c)))))
            for pi, a, b, c, n, ar in raw if area[pi] >= min_area]


def _clip_area(sub, clip):
    """Area of the overlap of two convex counter-clockwise 2D polygons (Sutherland-Hodgman)."""
    out = sub
    for i in range(len(clip)):
        p, q = clip[i], clip[(i + 1) % len(clip)]
        inp, out = out, []
        side = lambda s: (q[0] - p[0]) * (s[1] - p[1]) - (q[1] - p[1]) * (s[0] - p[0])
        for j in range(len(inp)):
            s, e = inp[j], inp[(j + 1) % len(inp)]
            ds, de = side(s), side(e)
            if ds >= 0:
                out.append(s)
            if (ds >= 0) != (de >= 0):
                t = ds / (ds - de)
                out.append((s[0] + (e[0] - s[0]) * t, s[1] + (e[1] - s[1]) * t))
        if not out:
            return 0.0
    return abs(sum(out[k][0] * out[(k + 1) % len(out)][1] - out[(k + 1) % len(out)][0] * out[k][1]
                   for k in range(len(out)))) / 2


def _overlap(t1, t2):
    """Overlap area of two coplanar-ish triangles, both projected onto the plane of t1."""
    a, b, c, n = t1[:4]
    u = (b - a).normalized()
    v = n.cross(u)
    p1 = [((q - a).dot(u), (q - a).dot(v)) for q in (a, b, c)]
    p2 = [((q - a).dot(u), (q - a).dot(v)) for q in t2[:3]]
    for p in (p1, p2):
        if (p[1][0] - p[0][0]) * (p[2][1] - p[0][1]) - (p[1][1] - p[0][1]) * (p[2][0] - p[0][0]) < 0:
            p.reverse()
    return _clip_area(p2, p1)


def coplanar_check(prefixes=None, tol=0.0005, min_area=1e-6):
    """Pairs (name1, name2) of mesh objects with faces on one plane (within tol metres) whose in-plane extents overlap.

    Faces count when their normals point the same way and the overlap exceeds min_area square metres; faces that
    meet back to back (butt joints, a wall on a floor) do not z-fight and are not reported.
    Objects hidden from render are skipped. Catches z-fighting and black strips before rendering.
    """
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pre = None if prefixes is None else _prefixes(prefixes)
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render
            and (pre is None or o.name.startswith(pre))]
    data = []
    for o in objs:
        ts = _tris(o, dg, min_area)
        if ts:
            data.append((o.name, ts, (Vector(map(min, zip(*(t[5][0] for t in ts)))),
                                      Vector(map(max, zip(*(t[5][1] for t in ts)))))))
    hits = []
    for i, (n1, t1s, b1) in enumerate(data):
        for n2, t2s, b2 in data[i + 1:]:
            if any(b1[0][k] > b2[1][k] + tol or b2[0][k] > b1[1][k] + tol for k in range(3)):
                continue
            total = 0.0
            for t1 in t1s:
                for t2 in t2s:
                    if t1[3].dot(t2[3]) <= 0.9995 or abs((t2[0] - t1[0]).dot(t1[3])) >= tol:
                        continue
                    if any(t1[5][0][k] > t2[5][1][k] + tol or t2[5][0][k] > t1[5][1][k] + tol for k in range(3)):
                        continue
                    total += _overlap(t1, t2)
                if total > min_area:
                    break
            if total > min_area:
                hits.append((n1, n2))
    return hits


def fail_on(hits, label):
    """Print OK <label>, or FAIL <label>: <hits> and exit with status 1 when hits is not empty."""
    if hits:
        print(f"FAIL {label}: {hits}")
        sys.exit(1)
    print(f"OK {label}")
