"""Pre-render scene checks (Blender): clashes, coplanar faces, flipped faces, wall gaps, floor fit, camera rays,
stair clearance, and run_checks, the pass/fail gate that a build script calls before it renders."""
import math
import sys
import time
from bisect import bisect_right
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


def _depsgraph():
    bpy.context.view_layer.update()
    return bpy.context.evaluated_depsgraph_get()


def _objects(types, skip=()):
    """Render-visible objects of the view layer with the given types, leaving out the exact names in skip."""
    return [o for o in bpy.context.view_layer.objects if o.type in types and not o.hide_render and o.name not in skip]


def _mesh(ob, dg, world=True):
    """(vertices, polygons as vertex-index tuples) of the evaluated object, or None when it has no polygons."""
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    try:
        if not me.polygons:
            return None
        m = ob.matrix_world if world else None
        return [(m @ v.co) if m else v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons]
    finally:
        e.to_mesh_clear()


def _box(vs):
    return Vector(map(min, zip(*vs))), Vector(map(max, zip(*vs)))


def _closed(polys):
    edges = Counter(tuple(sorted((p[k], p[(k + 1) % len(p)]))) for p in polys for k in range(len(p)))
    return all(c == 2 for c in edges.values())


def _volume(vs, polys):
    """Signed volume of a closed mesh, summed about its vertex centroid in Python floats.

    Summed about the origin, the rounding of single-precision vector maths can swamp a thin box far from it.
    """
    pts = [tuple(v) for v in vs]
    cx, cy, cz = (sum(c) / len(pts) for c in zip(*pts))
    q = [(x - cx, y - cy, z - cz) for x, y, z in pts]
    total = 0.0
    for p in polys:
        a = q[p[0]]
        for i in range(1, len(p) - 1):
            b, c = q[p[i]], q[p[i + 1]]
            total += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                      + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return total / 6


def _nz(vs, p):
    """z component of the area normal of polygon p of vs."""
    pts = [vs[i] for i in p]
    return sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))


def _outward(vs, polys):
    """polys wound so that a closed mesh faces outward and each face of an open mesh faces up or sideways."""
    if _closed(polys):
        return [p[::-1] for p in polys] if _volume(vs, polys) < 0 else polys
    return [p[::-1] if _nz(vs, p) < 0 else p for p in polys]


def _bvh(parts):
    """One BVH over parts [(vertices, polygons)], and the first polygon index of each part."""
    vs, ps, starts = [], [], []
    for pv, pp in parts:
        starts.append(len(ps))
        base = len(vs)
        vs += pv
        ps += [tuple(i + base for i in p) for p in pp]
    return BVHTree.FromPolygons(vs, ps), starts


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
    sign = -1 if ob.matrix_world.determinant() < 0 else 1
    raw, area = [], Counter()
    for t in me.loop_triangles:
        a, b, c = (vs[i] for i in t.vertices)
        n = (b - a).cross(c - a) * sign
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


def coplanar_check(prefixes=None, tol=0.0005, min_area=1e-6, skip=()):
    """Pairs (name1, name2) of mesh objects with faces on one plane (within tol metres) whose in-plane extents overlap.

    Faces count when their normals point the same way and the overlap exceeds min_area square metres; faces that
    meet back to back (butt joints, a wall on a floor) do not z-fight and are not reported.
    skip holds exact object names to leave out. Objects hidden from render are skipped.
    Catches z-fighting and black strips before rendering.
    """
    dg = _depsgraph()
    pre = None if prefixes is None else _prefixes(prefixes)
    objs = [o for o in _objects(("MESH",), skip) if pre is None or o.name.startswith(pre)]
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


def flipped_check(skip=()):
    """Pairs (name, "inside-out" | "mixed") of closed mesh objects whose faces turn the wrong way.

    "mixed": some faces are turned against their neighbours. "inside-out": all face inward (negative volume).
    Open meshes and objects hidden from render are skipped. Sorted by name.
    """
    dg = _depsgraph()
    hits = []
    for ob in _objects(("MESH",), skip):
        m = _mesh(ob, dg, world=False)
        if m is None or not _closed(m[1]):
            continue
        vs, polys = m
        directed = Counter((p[k], p[(k + 1) % len(p)]) for p in polys for k in range(len(p)))
        if any(c > 1 for c in directed.values()):
            hits.append((ob.name, "mixed"))
        elif _volume(vs, polys) < -1e-12:
            hits.append((ob.name, "inside-out"))
    return sorted(hits)


def _off_axis(vs, p):
    """True when polygon p of vs has a normal more than 1e-4 away from every world axis."""
    o = vs[p[0]]
    n = Vector()
    for k in range(1, len(p) - 1):
        n += (vs[p[k]] - o).cross(vs[p[k + 1]] - o)
    if n.length < 1e-12:
        return False
    big = max(range(3), key=lambda k: abs(n[k]))
    return math.hypot(*(n[k] for k in range(3) if k != big)) / n.length > 1e-4


def wall_gap_check(prefixes=("wall_",), floors=(), gap=0.3, opening=2.5, touch=0.001, tol=0.025, skip=(),
                   full_height=()):
    """Hits (name_i, name_j, kind, length_m) for wall objects that almost meet or frame a door-sized opening.

    kind "gap" or "corner": see wall_gaps.wall_gaps. "no-header": the ray up from the middle of an opening
    between in-line walls hits nothing, or first hits at the wall top (a ceiling on the walls). "no-floor": with
    floors given, the ray down hits nothing in floors, or hits more than tol below the wall bottom.
    "no-header" is probed only where the opening's walls stand at least 2.0 m above the higher wall bottom, and not
    when the scene camera is orthographic (a plan view hides what is above its cut).
    full_height holds pairs of wall names whose opening is meant to run to the ceiling. Angled walls are not
    checked and are named in a NOTE line. Sorted. Lengths are world metres.
    """
    from wall_gaps import wall_gaps, wall_openings
    dg = _depsgraph()
    cam = bpy.context.scene.camera
    plan = cam is not None and cam.type == "CAMERA" and cam.data.type == "ORTHO"
    pre, pairs = _prefixes(prefixes), {frozenset(p) for p in full_height}
    names, rects, angled = [], [], []
    for ob in _objects(("MESH",), skip):
        m = ob.name.startswith(pre) and _mesh(ob, dg)
        if not m:
            continue
        if any(_off_axis(m[0], p) for p in m[1]):
            angled.append(ob.name)
            continue
        lo, hi = _box(m[0])
        names.append(ob.name)
        rects.append((lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    if angled:
        print(f"NOTE wall_gaps: not axis-aligned, not checked: {', '.join(sorted(angled))}")
    hits = [(*sorted((names[i], names[j])), kind, d) for i, j, kind, d in wall_gaps(rects, 1.0, gap, touch)]
    trees = None
    for i, j, w, (x0, x1, y0, y1) in wall_openings(rects, 1.0, gap, opening, touch):
        pair = sorted((names[i], names[j]))
        base = max(rects[i][4], rects[j][4])
        z = base + 1.0
        top, bottom = min(rects[i][5], rects[j][5]), min(rects[i][4], rects[j][4])
        if frozenset(pair) in pairs or z >= top - tol:
            continue
        if trees is None:
            meshes = (_mesh(o, dg) for o in _objects(("MESH", "CURVE")))
            fl = (_mesh(o, dg) for o in _objects(("MESH",)) if o.name in floors)
            fl = [m for m in fl if m]
            trees = (None if plan else _bvh([m for m in meshes if m])[0], _bvh(fl)[0] if fl else None)
        scene_tree, floor_tree = trees
        at = Vector(((x0 + x1) / 2, (y0 + y1) / 2, z))
        if scene_tree is not None and top - base >= 2.0:
            up = scene_tree.ray_cast(at, Vector((0, 0, 1)))[0]
            if up is None or up.z >= top - tol:
                hits.append((*pair, "no-header", w))
        if floor_tree:
            down = floor_tree.ray_cast(at, Vector((0, 0, -1)))[0]
            if down is None or down.z < bottom - tol:
                hits.append((*pair, "no-floor", w))
    return sorted(hits)


_HANG = 0.3


def floor_fit_check(floors, walls=("wall_",), tol=0.025, hang=_HANG, skip=()):
    """Pairs (name, d) of mesh objects that float above or sink into the floor under their centre.

    floors holds exact object names. d is the base height above the floor in metres: positive is floating
    (more than tol, with nothing under the centre), negative is sunk (more than tol); None is sunk more than hang.
    An object at hang or higher is hung (lights, upper cabinets) and passes, and so does one that rests on another
    object under its centre. An object that hangs from the underside of a floor above it is measured against the
    floor below, and one that pierces that floor is sunk. Objects named with walls prefixes are reported only when
    floating. Sorted by name.
    """
    dg = _depsgraph()
    wpre = _prefixes(walls)
    data, fl = {}, []
    for ob in _objects(("MESH",)):
        m = _mesh(ob, dg)
        if m:
            data[ob.name] = (ob, *m, *_box(m[0]))
    for n in floors:
        if n in data:
            ob, vs, ps = data[n][:3]
            fl.append((vs, _outward(vs, ps)))
    if not fl:
        return []
    tree = _bvh(fl)[0]
    support = {}
    down, up = Vector((0, 0, -1)), Vector((0, 0, 1))
    hits = []
    for n, (ob, vs, ps, lo, hi) in data.items():
        if n in floors or n in skip:
            continue
        cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
        start = Vector((cx, cy, min(lo.z + hang, max(hi.z - 1e-4, lo.z + 1e-4))))
        loc, normal = tree.ray_cast(start, down)[:2]
        if loc is not None and normal.z < 0 and loc.z > lo.z + tol:
            # An up ray tells an object hung from the slab's underside from one that pierces the slab.
            top = tree.ray_cast(start, up)[0]
            if top is not None and hi.z < top.z - tol:
                loc, normal = tree.ray_cast(Vector((cx, cy, loc.z - 1e-4)), down)[:2]
        if loc is None:
            continue
        d = None if normal.z < 0 else lo.z - loc.z
        if d is None or d < -tol:
            if not n.startswith(wpre):
                hits.append((n, d))
        elif tol < d < hang:
            at = Vector((cx, cy, lo.z + tol))
            rests = False
            for o, ovs, ops, olo, ohi in data.values():
                if (o is ob or not olo.x <= cx <= ohi.x or not olo.y <= cy <= ohi.y or ohi.z < lo.z - tol):
                    continue
                if o.name not in support:
                    support[o.name] = BVHTree.FromPolygons(ovs, _outward(ovs, ops))
                hit = support[o.name].ray_cast(at, down, 2 * tol)
                if hit[0] is not None and hit[1].z > 0:
                    rests = True
                    break
            if not rests:
                hits.append((n, d))
    return sorted(hits, key=lambda h: h[0])


def camera_check(interior=None, rays=160, skip=()):
    """Items (kind, name, count, (x0, y0, x1, y1)) for faces the scene camera sees from behind, and for sky.

    Casts a grid of rays (rays columns) through the image from the camera. A face hit from behind is a "backface"
    on that object only when a ray a quarter cell away (up and right, or down and left) also hits a back face of it,
    so a ray that grazes a silhouette edge is not counted; a miss in an interior view is an "escape" (name None).
    The pixel box covers the cell centres.
    interior None means auto: interior when a ray straight up from the camera hits something; an exterior view
    prints a NOTE and checks no escapes. Returns [] for no camera or a non-perspective one. Sorted.
    """
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None or cam.type != "CAMERA" or cam.data.type != "PERSP":
        return []
    dg = _depsgraph()
    names, parts = [], []
    for ob in _objects(("MESH", "CURVE"), skip):
        m = ob.visible_camera and _mesh(ob, dg)
        if m:
            names.append(ob.name)
            parts.append((m[0], [p[::-1] for p in m[1]] if ob.matrix_world.determinant() < 0 else m[1]))
    if not parts:
        return []
    tree, starts = _bvh(parts)
    mw, c = cam.matrix_world, cam.data
    pos, rot = mw.translation, mw.to_3x3()
    if interior is None:
        interior = tree.ray_cast(pos, Vector((0, 0, 1)), c.clip_end)[0] is not None
        if not interior:
            print("NOTE camera: exterior view, escapes not checked")
    rx = sc.render.resolution_x * sc.render.resolution_percentage / 100
    ry = sc.render.resolution_y * sc.render.resolution_percentage / 100
    tr, _, bl, tl = c.view_frame(scene=sc)
    rows = max(1, round(rays * ry / rx))
    found = {}
    def cast(u, v):
        d = (rot @ (tl + (tr - tl) * u + (bl - tl) * v)).normalized()
        loc, normal, idx, _ = tree.ray_cast(pos + d * c.clip_start, d, c.clip_end - c.clip_start)
        if loc is None:
            return ("escape", None) if interior else None
        return ("backface", names[bisect_right(starts, idx) - 1]) if normal.dot(d) > 0 else None

    du, dv = 0.25 / rays, 0.25 / rows
    for j in range(rows):
        for i in range(rays):
            u, v = (i + 0.5) / rays, (j + 0.5) / rows
            key = cast(u, v)
            # Diagonal offsets: a vertical edge needs a u offset and a horizontal edge a v offset.
            if key and key[0] == "backface" and key not in (cast(u + du, v + dv), cast(u - du, v - dv)):
                key = None
            if key:
                px, py = u * rx, v * ry
                f = found.setdefault(key, [0, px, py, px, py])
                f[0] += 1
                f[1], f[2], f[3], f[4] = min(f[1], px), min(f[2], py), max(f[3], px), max(f[4], py)
    return sorted(((k[0], k[1], f[0], tuple(round(q) for q in f[1:])) for k, f in found.items()),
                  key=lambda h: (h[0], h[1] or ""))


def clearance_check(paths, headroom=2.032, unit=None, tol=0.005, skip=()):
    """Items (path, name, headroom_m) for objects inside the walking box over each path.

    paths maps a name to (x0, x1, y0, y1, z) in project units, z being the walking surface (a tread top). The box
    runs from z + tol to z + headroom metres (2.032 m is 6'-8"), inset by tol at the sides. unit is metres per
    project unit (None means bhelpers.U). An object is a hit when its surface crosses the box or a vertex lies
    inside it. headroom_m is the lowest point above the walking surface, or None when none of 9 rays up from the
    box bottom reach the object. Sorted by (path, name).
    """
    if unit is None:
        import bhelpers
        unit = bhelpers.U
    dg = _depsgraph()
    data = []
    for ob in _objects(("MESH", "CURVE"), skip):
        m = _mesh(ob, dg)
        if m:
            data.append((ob.name, *m, *_box(m[0])))
    trees = {}
    up = Vector((0, 0, 1))
    hits = []
    for pname, (x0, x1, y0, y1, z) in paths.items():
        z *= unit
        lo = Vector((x0 * unit + tol, y0 * unit + tol, z + tol))
        hi = Vector((x1 * unit - tol, y1 * unit - tol, z + headroom))
        cube = [Vector((x, y, zz)) for zz in (lo.z, hi.z) for y in (lo.y, hi.y) for x in (lo.x, hi.x)]
        cube_tree = BVHTree.FromPolygons(cube, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (1, 5, 7, 3),
                                                (3, 7, 6, 2), (2, 6, 4, 0)])
        for name, vs, ps, olo, ohi in data:
            if any(olo[k] > hi[k] or ohi[k] < lo[k] for k in range(3)):
                continue
            if name not in trees:
                trees[name] = BVHTree.FromPolygons(vs, ps)
            if not (trees[name].overlap(cube_tree) or
                    any(all(lo[k] < v[k] < hi[k] for k in range(3)) for v in vs)):
                continue
            tops = [trees[name].ray_cast(Vector((lo.x + (hi.x - lo.x) * (a + 0.5) / 3,
                                                 lo.y + (hi.y - lo.y) * (b + 0.5) / 3, lo.z)), up)[0]
                    for a in range(3) for b in range(3)]
            tops = [t.z for t in tops if t is not None]
            hits.append((pname, name, min(tops) - z if tops else None))
    return sorted(hits, key=lambda h: (h[0], h[1]))


def fail_on(hits, label):
    """Print OK <label>, or FAIL <label>: <hits> and exit with status 1 when hits is not empty."""
    if hits:
        print(f"FAIL {label}: {hits}")
        sys.exit(1)
    print(f"OK {label}")


_NAMES = ("coplanar", "flipped", "wall_gaps", "floor_fit", "camera", "clearance")


def _line(check, h):
    if check in ("coplanar", "flipped"):
        return f"{h[0]} {h[1]}"
    if check == "wall_gaps":
        return f"{h[0]} {h[1]} {h[2]} {h[3]:.3f} m"
    if check == "floor_fit":
        if h[1] is None:
            return f"{h[0]} sunk more than {_HANG:.3f} m"
        return f"{h[0]} floating {h[1]:.3f} m" if h[1] > 0 else f"{h[0]} sunk {-h[1]:.3f} m"
    if check == "camera":
        kind, name, n, (x0, y0, x1, y1) = h
        return f"{kind + ' ' + name if name else kind}: {n} rays at px {x0}-{x1}, {y0}-{y1}"
    return f"{h[0]} {h[1]} inside" if h[2] is None else f"{h[0]} {h[1]} headroom {h[2]:.3f} m"


def run_checks(floors=(), walls=("wall_",), paths=None, figure=("man_",), exempt=None, interior=None, unit=None,
               rays=160):
    """Run the six checks over the whole scene, print OK, FAIL or SKIP for each, and exit 1 when any failed.

    Call it after the camera is set and right before the render. floors: exact names of every floor, slab and
    deck. walls: wall name prefixes. paths: {name: (x0, x1, y0, y1, z)} walking boxes in project units, one per
    stair tread. figure: prefixes of the scale figure, left out of coplanar, floor fit and clearance.
    exempt: {check: [exact object names]} for coplanar, flipped, wall_gaps, floor_fit, camera and clearance, and
    {"openings": [(wall, wall)]} for openings meant to run to the ceiling. interior and rays go to camera_check;
    unit (metres per project unit, None for bhelpers.U) goes to clearance_check.
    """
    exempt = {k: v if k == "openings" else _prefixes(v) for k, v in (exempt or {}).items()}
    bad = [k for k in exempt if k not in _NAMES + ("openings",)]
    if bad:
        raise ValueError(f"unknown exempt key {bad[0]!r}; use one of {', '.join(_NAMES + ('openings',))}")
    bpy.context.view_layer.update()
    have = {o.name for o in bpy.data.objects}
    for key, names in exempt.items():
        for n in (n for item in names for n in ((item,) if isinstance(item, str) else item)):
            if n not in have:
                print(f"WARN exempt {key}: no object named {n}")
    floors, rendered = _prefixes(floors), {o.name for o in _objects(("MESH",))}
    for n in floors:
        if n not in rendered:
            print(f"WARN floors: no {'rendered mesh' if n in have else 'object'} named {n}")
    fig = tuple(n for n in have if n.startswith(_prefixes(figure))) if figure else ()
    given, floors = bool(floors), tuple(n for n in floors if n in rendered)
    cam = bpy.context.scene.camera

    def skip(check, extra=()):
        return tuple(exempt.get(check, ())) + tuple(extra)

    plan = (
        ("coplanar", None, lambda: coplanar_check(skip=skip("coplanar", fig))),
        ("flipped", None, lambda: flipped_check(skip=skip("flipped"))),
        ("wall_gaps", None, lambda: wall_gap_check(prefixes=walls, floors=floors, skip=skip("wall_gaps"),
                                                   full_height=exempt.get("openings", ()))),
        ("floor_fit", None if floors else "none of the floors exists" if given else "no floors given",
         lambda: floor_fit_check(floors, walls=walls, skip=skip("floor_fit", fig))),
        ("camera", "no scene camera" if cam is None else
         "scene camera is not a camera object" if cam.type != "CAMERA" else
         None if cam.data.type == "PERSP" else
         f"{'orthographic' if cam.data.type == 'ORTHO' else 'panoramic'} camera",
         lambda: camera_check(interior=interior, rays=rays, skip=skip("camera"))),
        ("clearance", None if paths else "no paths given",
         lambda: clearance_check(paths, unit=unit, skip=skip("clearance", fig))),
    )
    failed = []
    for name, why, fn in plan:
        if why:
            print(f"SKIP {name}: {why}")
            continue
        t0 = time.perf_counter()
        try:
            hits = fn()
        except Exception as e:
            print(f"FAIL {name}: error {type(e).__name__}: {e}")
            failed.append(name)
            continue
        dt = time.perf_counter() - t0
        if not hits:
            print(f"OK {name} ({dt:.2f} s)")
            continue
        failed.append(name)
        print(f"FAIL {name}: {len(hits)} ({dt:.2f} s)")
        for h in hits[:20]:
            print("  " + _line(name, h))
        if len(hits) > 20:
            print(f"  ... and {len(hits) - 20} more")
    if failed:
        print(f"FAIL run_checks: {', '.join(failed)}")
        sys.exit(1)
    print("OK run_checks")
