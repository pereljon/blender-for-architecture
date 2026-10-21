"""Blender helpers for scripted renders: geometry, materials, tiles, plan input, lights, cameras, plan overlays.

Runs inside Blender 5.2 (bpy, bmesh, mathutils; no numpy):
  /Applications/Blender.app/Contents/MacOS/Blender -b -P scene.py -- --view NAME --res 800 --samples 48 --out out/NAME.png

Conventions:
- Every length argument is in project units; U is metres per project unit (set_units), applied inside each helper.
  Energies, angles, colours, sample counts and pixels are not scaled.
- Plan axes: X and Y on the floor, Z up from the finished floor. The project fixes the origin and the axis directions.
- Colours are linear RGB tuples. Give hex values through srgb(); raw sRGB values overexpose.
- Object names carry a prefix per element group ("wic_", "mech_"). Plan views hide, drop or keep objects by prefix.
- Project values (rooms, views, wall corrections) live in the project's own constants block. Nothing here knows a house.
"""
import json
import math

import bpy  # must precede bmesh
import bmesh
from mathutils import Matrix, Vector

U = 1.0
EYE_HEIGHT = 1.5875   # metres: the eye of a 5'-7" viewer, 5'-2 1/2"
_OV = 0.03       # plan overlay mark height, metres


def set_units(u):
    """Set metres per project unit: "m", "ft" or a number."""
    global U
    U = {"m": 1.0, "ft": 0.3048}[u] if isinstance(u, str) else float(u)
    return U


def clear_scene():
    """Remove every object, mesh, material, light, camera and curve, and forget the tile pieces."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for d in list(coll):
            coll.remove(d)
    PIECES.clear()


# ---------------------------------------------------------------- geometry


def new_obj(name, mesh, mat=None):
    """Link a mesh object to the scene, with an optional material."""
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def _to_mesh(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0, seg=2):
    """Axis-aligned box from its extents; optional bevel modifier with smooth shading.

    Butt boxes against each other; overlapping solids render black or z-fight.
    """
    x0, x1, y0, y1, z0, z1 = (v * U for v in (x0, x1, y0, y1, z0, z1))
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        bm.faces.new([vs[i] for i in f])
    ob = new_obj(name, _to_mesh(name, bm), mat)
    if bevel > 0:
        m = ob.modifiers.new("bev", "BEVEL")
        m.width = bevel * U
        m.segments = seg
        m.limit_method = "ANGLE"
        ob.data.shade_smooth()
        ob.data.set_sharp_from_angle(angle=math.radians(40))
    return ob


def slab(name, pts, ztop, thick, mat=None, zbot=None):
    """XY polygon extruded down from ztop to ztop - thick, or to zbot (sloped floors, counters).

    ztop and zbot are numbers or callables f(x, y) in project units.
    """
    ft = ztop if callable(ztop) else (lambda x, y: ztop)
    fb = zbot if callable(zbot) or zbot is None else (lambda x, y: zbot)
    bm = bmesh.new()
    top = [bm.verts.new((x * U, y * U, ft(x, y) * U)) for x, y in pts]
    bot = [bm.verts.new((x * U, y * U, (fb(x, y) if fb else ft(x, y) - thick) * U)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, _to_mesh(name, bm), mat)


def prism(name, pts, z0, z1, mat=None):
    """Vertical prism over a polygon: angled walls, bays, odd-shaped slabs."""
    bm = bmesh.new()
    lo = [bm.verts.new((x * U, y * U, z0 * U)) for x, y in pts]
    hi = [bm.verts.new((x * U, y * U, z1 * U)) for x, y in pts]
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, _to_mesh(name, bm), mat)


def seg(name, a, b, t, z0, z1, mat=None):
    """Wall segment of thickness t on the centre line a-b, any angle."""
    ob = box(name, 0, math.dist(a, b), -t / 2, t / 2, z0, z1, mat)
    ob.location = (a[0] * U, a[1] * U, 0)
    ob.rotation_euler = (0, 0, math.atan2(b[1] - a[1], b[0] - a[0]))
    return ob


def cyl(name, x, y, z0, z1, r, mat=None, n=32, rot_rad=None):
    """Vertical cylinder from z0 to z1; rot_rad=(rx, ry, rz) Euler angles in radians turn it about its centre."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r * U, radius2=r * U, depth=(z1 - z0) * U)
    ob = new_obj(name, _to_mesh(name, bm), mat)
    ob.location = (x * U, y * U, (z0 + z1) / 2 * U)
    if rot_rad:
        ob.rotation_euler = rot_rad
    ob.data.shade_smooth()
    return ob


def cyl_x(name, x0, x1, y, z, r, mat=None, n=32):
    """Cylinder along X (bars, rails)."""
    ob = cyl(name, 0, 0, -(x1 - x0) / 2, (x1 - x0) / 2, r, mat, n, rot_rad=(0, math.radians(90), 0))
    ob.location = ((x0 + x1) / 2 * U, y * U, z * U)
    return ob


def cyl_y(name, y0, y1, x, z, r, mat=None, n=32):
    """Cylinder along Y."""
    ob = cyl(name, 0, 0, -(y1 - y0) / 2, (y1 - y0) / 2, r, mat, n, rot_rad=(math.radians(90), 0, 0))
    ob.location = (x * U, (y0 + y1) / 2 * U, z * U)
    return ob


def sphere(name, x, y, z, r, mat=None, scale=(1, 1, 1)):
    """UV sphere (ellipsoid with scale) centred at x, y, z."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r * U)
    ob = new_obj(name, _to_mesh(name, bm), mat)
    ob.location = (x * U, y * U, z * U)
    ob.scale = scale
    ob.data.shade_smooth()
    return ob


def tube(name, pts, r, mat=None):
    """Round tube along a NURBS path through pts (spouts, levers, pipes). Caps are closed; open ends render as holes."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r * U
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (c[0] * U, c[1] * U, c[2] * U, 1)
    sp.use_endpoint_u = True
    sp.order_u = 3 if len(pts) >= 3 else 2
    sp.resolution_u = 24
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def polyline(name, pts, z, width, mat=None):
    """Flat line through (x, y) points at height z, as a bevelled curve: door swings and break lines in plan views."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = width / 2 * U
    cu.use_fill_caps = True          # open tube ends otherwise
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for pt, (x, y) in zip(sp.points, pts):
        pt.co = (x * U, y * U, z * U, 1)
    ob = bpy.data.objects.new(name, cu)
    if mat:
        ob.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def lathe(name, profile, mat=None, n=64, plan=None):
    """Revolve an (r, z) profile around local Z (basins, bowls, knobs); place it with place().

    plan = (a, b, e) makes each ring a superellipse with semi-axes a, b and exponent e, scaled by r.
    """
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            if plan:
                pa, pb, e = plan
                c, s_ = math.cos(a), math.sin(a)
                ring.append(bm.verts.new((r * pa * math.copysign(abs(c) ** (2 / e), c) * U,
                                          r * pb * math.copysign(abs(s_) ** (2 / e), s_) * U, z * U)))
            else:
                ring.append(bm.verts.new((r * math.cos(a) * U, r * math.sin(a) * U, z * U)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = new_obj(name, _to_mesh(name, bm), mat)
    ob.data.shade_smooth()
    return ob


def place(ob, x, y, z, rot_deg=0.0):
    """Set an object's location and its Z rotation in degrees."""
    ob.location = (x * U, y * U, z * U)
    ob.rotation_euler.z = math.radians(rot_deg)
    return ob


def placed(build, tx, ty, tz, rot):
    """Run build(), which models an element around the origin, then move the new objects to (tx, ty, tz) turned rot degrees.

    Lets one element (a grill, a vanity) be studied at several sites with the same code.
    """
    before = set(bpy.data.objects)
    build()
    bpy.context.view_layer.update()
    T = Matrix.Translation((tx * U, ty * U, tz * U)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    new = [ob for ob in bpy.data.objects if ob not in before]
    for ob in new:
        ob.matrix_world = T @ ob.matrix_world
    return new


def cut_holes(prefixes, holes, solver="EXACT"):
    """Boolean-difference each hole (x0, x1, y0, y1, z0, z1) out of every object whose name starts with prefixes.

    Model a floor as one continuous slab and cut the stair and light-well openings out of it; piecing a floor
    together from rectangles leaves gaps at door thresholds.
    """
    prefixes = (prefixes,) if isinstance(prefixes, str) else tuple(prefixes)
    cutters = []
    for k, h in enumerate(holes):
        c = box(f"cutter_{k}", *h)
        c.hide_render = True
        c.display_type = "WIRE"
        cutters.append(c)
    for ob in list(bpy.data.objects):
        if ob.name.startswith(prefixes) and ob not in cutters:
            for c in cutters:
                m = ob.modifiers.new("hole", "BOOLEAN")
                m.operation = "DIFFERENCE"
                m.object = c
                m.solver = solver


def look(ob, loc, target):
    """Place an object (camera, spot light) at loc pointing at target."""
    loc, target = Vector(loc) * U, Vector(target) * U
    ob.location = loc
    ob.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()


def person(mat, x, y, h=None):
    """Scale figure: a cylinder body and a sphere head, h tall in project units (default 1.75 m)."""
    h = 1.75 / U if h is None else h
    cyl("person_body", x, y, 0, h * 0.861, h * 0.096, mat)
    sphere("person_head", x, y, h * 0.927, h * 0.066, mat)


# ---------------------------------------------------------------- materials (colours are linear, not sRGB)


def srgb(hexstr):
    """Hex sRGB colour ("#c8b49a" or "c8b49a") to a linear RGB tuple for Principled inputs."""
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def sock(node, name, kind=None):
    """Input socket by name and type; needed for nodes like Mix that have several sockets with the same name."""
    for s in node.inputs:
        if s.name == name and s.enabled and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def osock(node, name, kind=None):
    """Output socket by name and type (see sock)."""
    for s in node.outputs:
        if s.name == name and s.enabled and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def principled(name, color, rough=0.5, metal=0.0, **kw):
    """Principled BSDF material. Extra inputs by socket name, e.g. **{"Transmission Weight": 1.0, "IOR": 1.45}."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m


def emission(name, color, strength):
    """Emission-only material: downlight discs, LED strips, screens, plan-view overlay marks."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


def wood_material(name, axis="Z", dark=(0.22, 0.11, 0.045), light=(0.30, 0.165, 0.07), rough=0.45):
    """Procedural wood grain (wave bands and a colour ramp) on object coordinates; grain runs across axis."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = {"X": (11, 1, 1), "Y": (1, 11, 1), "Z": (1, 1, 11)}[axis]
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = axis
    wave.inputs["Scale"].default_value = 1.0
    wave.inputs["Distortion"].default_value = 14
    wave.inputs["Detail Scale"].default_value = 2.5
    wave.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs[0], wave.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    return m


def _tone_mix(nt, a_out, b_out, bsdf):
    """Multiply a base-colour output by a tone-variation output into the BSDF Base Color."""
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    sock(mix, "Factor", "VALUE").default_value = 1.0
    nt.links.new(a_out, sock(mix, "A", "RGBA"))
    nt.links.new(b_out, sock(mix, "B", "RGBA"))
    nt.links.new(osock(mix, "Result", "RGBA"), bsdf.inputs["Base Color"])


def planks(name, color, plank_w=None, plank_l=None):
    """Plank floor: brick-texture boards (plank_w by plank_l) with per-board tone, grain and bumped seams.

    plank_w and plank_l default to 0.18 m and 1.8 m.
    """
    plank_w = 0.18 / U if plank_w is None else plank_w
    plank_l = 1.8 / U if plank_l is None else plank_l
    m = principled(name, color, rough=0.42)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.37
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = plank_l * U
    br.inputs["Row Height"].default_value = plank_w * U
    br.inputs["Mortar Size"].default_value = 0.0012
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Color1"].default_value = (*[c * 0.86 for c in color], 1)
    br.inputs["Color2"].default_value = (*[min(1, c * 1.10) for c in color], 1)
    br.inputs["Mortar"].default_value = (*[c * 0.45 for c in color], 1)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0, 60.0, 1)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.80, 0.80, 0.80, 1)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    _tone_mix(nt, br.outputs["Color"], ramp.outputs["Color"], b)
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def stone_tile(name, color, tile=None, tile_h=None, plane="xy", joint=None, rough=0.7):
    """Stone or porcelain tile in stack bond (tile by tile_h, joint = full joint width): per-tile tone, mottling, bumped joints.

    tile and joint default to 0.6 m and 10 mm. plane picks the two object axes the pattern runs on: "xy" for floors, "xz" for walls facing +Y or -Y, "yz" for
    walls facing +X or -X. A wall material on the wrong plane shows stretched streaks, not tiles.
    """
    tile = 0.6 / U if tile is None else tile
    joint = 0.01 / U if joint is None else joint
    m = principled(name, color, rough=rough)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = tile * U
    br.inputs["Row Height"].default_value = (tile_h or tile) * U
    br.inputs["Mortar Size"].default_value = joint * U / 2
    br.inputs["Color1"].default_value = (*[c * 0.85 for c in color], 1)
    br.inputs["Color2"].default_value = (*[min(1, c * 1.12) for c in color], 1)
    br.inputs["Mortar"].default_value = (*[c * 0.4 for c in color], 1)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 40.0
    nz.inputs["Detail"].default_value = 10.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.82, 0.82, 0.82, 1)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    vec = tc.outputs["Object"]
    if plane != "xy":
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        com = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        nt.links.new(sep.outputs["X" if plane == "xz" else "Y"], com.inputs["X"])
        nt.links.new(sep.outputs["Z"], com.inputs["Y"])
        vec = com.outputs["Vector"]
    nt.links.new(vec, br.inputs["Vector"])
    nt.links.new(vec, nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    _tone_mix(nt, br.outputs["Color"], ramp.outputs["Color"], b)
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def fabric(name, color, scale=180.0, strength=0.35):
    """Woven or boucle textile: fine noise bump on a matte base."""
    m = principled(name, color, rough=0.95)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def image_tile_material(name, path, mult=(1, 1, 1), rough=0.5, bump=0.1, spec=0.5):
    """One photo or scan per tile piece through the piece's UVs (each tile shows the whole image), tinted by mult.

    Adds a light bump from the image. Pair with tile_poly and tile_wall, which write the UVs.
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(path)
    img.interpolation = "Cubic"
    img.extension = "EXTEND"
    nt.links.new(uvn.outputs["UV"], img.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    sock(mx, "Factor", "VALUE").default_value = 1.0
    nt.links.new(img.outputs["Color"], sock(mx, "A", "RGBA"))
    sock(mx, "B", "RGBA").default_value = (*mult, 1)
    nt.links.new(osock(mx, "Result", "RGBA"), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Specular IOR Level"].default_value = spec
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.0005
    nt.links.new(img.outputs["Color"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def projected_tile_material(name, path, size, rough=0.5, bump=0.1):
    """Image box-projected on object coordinates, one image per size (scalar or (x, y, z)); no UVs needed."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    sx, sy, sz = size if isinstance(size, tuple) else (size, size, size)
    mp.inputs["Scale"].default_value = (1 / (sx * U), 1 / (sy * U), 1 / (sz * U))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(path)
    img.projection = "BOX"
    img.projection_blend = 0.2
    img.interpolation = "Cubic"
    nt.links.new(mp.outputs["Vector"], img.inputs["Vector"])
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.0005
    nt.links.new(img.outputs["Color"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# ---------------------------------------------------------------- tiles: real setout, each piece its own object


class Face:
    """A tiled surface: p(u, v, d) = origin + u*uax + v*vax + d*nax (nax points into the room), in project units.

    Example, wall along X at y = 0 facing +Y: Face((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0)).
    """

    def __init__(self, origin, uax, vax, nax):
        self.o, self.u, self.v, self.n = (Vector(a) for a in (origin, uax, vax, nax))

    def p(self, u, v, d=0.0):
        return self.o + self.u * u + self.v * v + self.n * d


def tile_poly(name, pts, uvs, nvec, mat, thick=None, bevel=None):
    """Tile piece: front face pts (3D) with UVs, extruded thick behind it (against nvec); a tiny bevel reads as grout.

    thick and bevel default to 10 mm and 0.7 mm.
    """
    thick = 0.010 / U if thick is None else thick
    bevel = 0.0007 / U if bevel is None else bevel
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    nv = Vector(nvec)
    front = [bm.verts.new(Vector(p) * U) for p in pts]
    back = [bm.verts.new((Vector(p) - nv * thick) * U) for p in pts]
    uvmap = {}
    for vf, vb, uv in zip(front, back, uvs):
        uvmap[vf] = uv
        uvmap[vb] = uv
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([front[i], front[j], back[j], back[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = uvmap[lp.vert]
    ob = new_obj(name, _to_mesh(name, bm), mat)
    if bevel:
        b = ob.modifiers.new("bev", "BEVEL")
        b.width = bevel * U
        b.segments = 1
        b.limit_method = "ANGLE"
    return ob


PIECES = []   # every tile piece in face coordinates (project units); export_pieces() dumps it for cutting plans


def face_piece(name, face, poly_uv, origin, mat, flips, tile=None, rot=False, thick=None):
    """One (possibly cut) tile piece. poly_uv: polygon in face (u, v); origin: (u, v) of the full tile's corner.

    A cut piece shows the matching part of the image. flips: random mirror of the image per tile.
    tile defaults to 1.20 by 0.60 m.
    """
    tile = (1.20 / U, 0.60 / U) if tile is None else tile
    lu, lv = (tile[1], tile[0]) if rot else tile
    uvs = []
    for u, v in poly_uv:
        s, t = (u - origin[0]) / lu, (v - origin[1]) / lv
        if rot:
            s, t = t, s
        if flips[0]:
            s = 1 - s
        if flips[1]:
            t = 1 - t
        uvs.append((s, t))
    PIECES.append(dict(name=name, poly=[(round(u, 4), round(v, 4)) for u, v in poly_uv], rot=rot))
    return tile_poly(name, [face.p(u, v) for u, v in poly_uv], uvs, face.n, mat, thick)


def u_pieces(u0, u1, start, sign, length=None, joint=None):
    """Columns of full tiles laid from start in direction sign (+1/-1), clipped to [u0, u1]: (lo, hi, tile_start).

    length and joint default to 1.20 m and 2 mm.
    """
    length = 1.20 / U if length is None else length
    joint = 0.002 / U if joint is None else joint
    out, k = [], 0
    while True:
        a = start + sign * k * (length + joint)
        b = a + sign * length
        lo, hi = min(a, b), max(a, b)
        if (sign > 0 and lo >= u1) or (sign < 0 and hi <= u0):
            break
        if hi > u0 and lo < u1:
            out.append((max(lo, u0), min(hi, u1), lo))
        k += 1
    return out


def subtract(r, h):
    """Rectangle r minus hole h, both (a0, a1, b0, b1): up to four rectangles (niches, windows, cut-outs)."""
    a0, a1, b0, b1 = r
    h0, h1, k0, k1 = max(h[0], a0), min(h[1], a1), max(h[2], b0), min(h[3], b1)
    if h0 >= h1 or k0 >= k1:
        return [r]
    out = []
    if k0 > b0:
        out.append((a0, a1, b0, k0))
    if k1 < b1:
        out.append((a0, a1, k1, b1))
    if h0 > a0:
        out.append((a0, h0, k0, k1))
    if h1 < a1:
        out.append((h1, a1, k0, k1))
    return out


def tile_wall(tag, face, u0, u1, start, sign, rows, mat, rnd, holes=(), tile=None, joint=None):
    """Stacked tiles on a Face between u0 and u1, laid from start (a full tile at the most visible corner).

    rows: [(v0, v1), ...] with the joints already in, e.g. [(0, .6), (.602, 1.202), ...]; holes: (u0, u1, v0, v1).
    rnd: random.Random(seed), so the image flips repeat between renders. tile and joint default to 1.20 by 0.60 m
    and 2 mm.
    """
    tile = (1.20 / U, 0.60 / U) if tile is None else tile
    joint = 0.002 / U if joint is None else joint
    for ci, (a, b, orig) in enumerate(u_pieces(u0, u1, start, sign, tile[0], joint)):
        for ri, (z0, z1) in enumerate(rows):
            flips = (rnd.random() < 0.5, rnd.random() < 0.5)
            rects = [(a, b, z0, z1)]
            for h in holes:
                rects = [r2 for r in rects for r2 in subtract(r, h)]
            for k, (ra, rb, rz0, rz1) in enumerate(rects):
                if rb - ra < 0.004 / U or rz1 - rz0 < 0.004 / U:      # skip slivers
                    continue
                face_piece(f"wt_{tag}_{ci}_{ri}_{k}", face, [(ra, rz0), (rb, rz0), (rb, rz1), (ra, rz1)],
                           (orig, z0), mat, flips, tile)


def export_pieces(path):
    """Write PIECES as JSON {"pieces": [...]}, polygons in project units."""
    with open(path, "w") as fh:
        json.dump({"pieces": PIECES}, fh)


# ---------------------------------------------------------------- plan input and the correction layer


def load_plan(path):
    """Walls JSON written by extract_plan.py: {"walls": [{kind, x0, x1, y0, y1}], "doors": [...], "leaves": [...]}."""
    with open(path) as fh:
        d = json.load(fh)
    return d["walls"], d.get("doors", []), d.get("leaves", [])


# The correction layer. Keep every hand correction to the extracted walls in these named lists in the project's
# build script, each with a dated comment giving its source (owner markup, site measurement, a newer sheet).
# Rectangles are (x0, x1, y0, y1) in project units.
#   WALL_FIXES   = [(old_rect, (new_y0, new_y1))]   move a piece onto the correct line (a false jog in the drawing)
#   WALL_REPLACE = [(old_rect, new_rect or None)]   replace a piece, or remove it (None) to open a wall
#   EXTRA_WALLS  = [(kind, x0, x1, y0, y1)]         add what the extraction missed (angled walls go in as seg())


def fix_walls(walls, wall_fixes=(), wall_replace=(), tol=None):
    """Apply WALL_REPLACE, then WALL_FIXES, to the extracted walls. Pieces match within tol (default 0.06 m)."""
    tol = 0.06 / U if tol is None else tol
    out = []
    near = lambda w, r, t: max(abs(w["x0"] - r[0]), abs(w["x1"] - r[1]), abs(w["y0"] - r[2]), abs(w["y1"] - r[3])) < t
    for w in walls:
        hit = [n for o, n in wall_replace if near(w, o, tol)]
        if hit:
            if hit[0] is None:
                continue
            w = dict(w, x0=hit[0][0], x1=hit[0][1], y0=hit[0][2], y1=hit[0][3])
        for o, (ny0, ny1) in wall_fixes:
            if near(w, o, tol):
                w = dict(w, y0=ny0, y1=ny1)
        out.append(w)
    return out


def extra_walls(rows):
    """Wall dicts, as load_plan returns them, from EXTRA_WALLS tuples (kind, x0, x1, y0, y1)."""
    return [dict(kind=k, x0=x0, x1=x1, y0=y0, y1=y1) for k, x0, x1, y0, y1 in rows]


def cut_openings(walls, holes, min_piece=None):
    """Trim wall rectangles where they run into an opening (jamb fragments left by the extraction).

    min_piece defaults to 0.05 m.
    """
    min_piece = 0.05 / U if min_piece is None else min_piece
    out = []
    for w in walls:
        pieces = [(w["x0"], w["x1"], w["y0"], w["y1"])]
        for hx0, hx1, hy0, hy1 in holes:
            nxt = []
            for x0, x1, y0, y1 in pieces:
                if min(x1, hx1) - max(x0, hx0) <= min_piece or min(y1, hy1) - max(y0, hy0) <= min_piece:
                    nxt.append((x0, x1, y0, y1))
                elif x1 - x0 >= y1 - y0:
                    nxt += [p for p in ((x0, hx0, y0, y1), (hx1, x1, y0, y1)) if p[1] - p[0] > min_piece]
                else:
                    nxt += [p for p in ((x0, x1, y0, hy0), (x0, x1, hy1, y1)) if p[3] - p[2] > min_piece]
            pieces = nxt
        out += [dict(w, x0=p[0], x1=p[1], y0=p[2], y1=p[3]) for p in pieces]
    return out


def walls_from_plan(walls, z0, z1, mat=None, prefix="wall_"):
    """One box per wall dict from load_plan, named prefix + index. Returns the objects."""
    return [box(f"{prefix}{k}", w["x0"], w["x1"], w["y0"], w["y1"], z0, z1, mat) for k, w in enumerate(walls)]


def door_swings(doors, mat, z=None, width=None, skip=None):
    """Door swing arcs from the extracted plan, drawn flat on the floor for plan views.

    z and width default to 0.06 m and 0.04 m. skip(door) -> True drops a swing (a door the design has changed to a slider).
    """
    z = 0.06 / U if z is None else z
    width = 0.04 / U if width is None else width
    for k, d in enumerate(doors):
        if skip and skip(d):
            continue
        polyline(f"swing_{k}", d["arc"], z, width, mat)


# ---------------------------------------------------------------- lighting


def room_fill_lights(rooms, ceil, w_per_m2=24.0, color=(1.0, 0.93, 0.84)):
    """One hidden area light per room under the ceiling; energy is w_per_m2 times the room area in square metres.

    rooms = {name: (x0, x1, y0, y1)}. The panels stay out of the camera and out of glass and mirror reflections.
    """
    for name, (x0, x1, y0, y1) in rooms.items():
        ld = bpy.data.lights.new(f"L_{name}", "AREA")
        ld.shape = "RECTANGLE"
        ld.size = (x1 - x0) * 0.6 * U
        ld.size_y = (y1 - y0) * 0.6 * U
        ld.energy = w_per_m2 * (x1 - x0) * (y1 - y0) * U * U
        ld.color = color
        ob = bpy.data.objects.new(f"L_{name}", ld)
        ob.location = ((x0 + x1) / 2 * U, (y0 + y1) / 2 * U, ceil * U - 0.015)
        ob.visible_camera = False
        ob.visible_glossy = False
        bpy.context.scene.collection.objects.link(ob)


def opening_light(name, x0, x1, y0, y1, z, energy=900, color=(0.9, 0.95, 1.0)):
    """Daylight through a skylight or other glazed opening: the sun does not pass glass solids, so the opening emits."""
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = (x1 - x0) * U, (y1 - y0) * U
    ld.energy = energy
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.location = ((x0 + x1) / 2 * U, (y0 + y1) / 2 * U, z * U)
    ob.visible_camera = False
    ob.visible_glossy = False
    bpy.context.scene.collection.objects.link(ob)
    return ob


def sun(elevation_deg, azimuth_deg, plan_north_deg=0.0, energy=3.0):
    """Sun from a solar position (elevation, azimuth clockwise from true north).

    plan_north_deg is the angle of true north from the plan's +Y axis, counter-clockwise. Pick one time of day for
    every render in a project so the studies compare fairly; take elevation and azimuth for the site and date from
    a solar calculator and record them in the dimensions file.
    """
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = energy
    ld.angle = math.radians(1.5)
    ob = bpy.data.objects.new("sun", ld)
    # Blender's sun shines down its local -Z. Tilt it from vertical by (90 - elevation), toward the sun's direction.
    az = math.radians(azimuth_deg) - math.radians(plan_north_deg)
    ob.rotation_euler = (math.radians(90 - elevation_deg), 0, math.pi - az)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def downlights(mat, rect, ceil, nx=3, ny=2, watts=45, tag="room", trim_r=None):
    """Recessed downlights over rect (x0, x1, y0, y1): an emissive trim in the ceiling plane plus a spot light below each.

    trim_r defaults to 60 mm.
    """
    trim_r = 0.06 / U if trim_r is None else trim_r
    x0, x1, y0, y1 = rect
    for i in range(nx):
        for j in range(ny):
            x = x0 + (x1 - x0) * (i + 0.5) / nx
            y = y0 + (y1 - y0) * (j + 0.5) / ny
            cyl(f"can_{tag}_{i}{j}", x, y, ceil - 0.009 / U, ceil - 0.0015 / U, trim_r, mat)
            ld = bpy.data.lights.new(f"S_{tag}_{i}{j}", "SPOT")
            ld.energy = watts
            ld.spot_size = math.radians(95)
            ld.spot_blend = 0.6
            ld.shadow_soft_size = 0.05
            ld.color = (1.0, 0.88, 0.74)
            ob = bpy.data.objects.new(f"S_{tag}_{i}{j}", ld)
            ob.location = (x * U, y * U, ceil * U - 0.018)
            bpy.context.scene.collection.objects.link(ob)


# ---------------------------------------------------------------- render setup and cameras


def setup_cycles(samples, gpu=True, exposure=0.0, look="AgX - Medium High Contrast", max_bounces=10,
                 glossy_bounces=6, transmission_bounces=10, sky=(0.55, 0.70, 0.95), sky_strength=1.0):
    """Cycles with adaptive sampling, denoising, AgX and a sky world. Does not set resolution or output.

    gpu=True uses Metal on every device; without a Metal device it prints one warning and renders on CPU.
    """
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    if gpu:
        metal = False
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            metal = any(dv.type == "METAL" for dv in prefs.devices)
            for dv in prefs.devices:
                dv.use = True
        except (TypeError, KeyError, AttributeError):
            pass
        if metal:
            sc.cycles.device = "GPU"
        else:
            print("WARN no Metal device found, rendering on CPU")
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = max_bounces
    sc.cycles.glossy_bounces = glossy_bounces
    sc.cycles.transmission_bounces = transmission_bounces
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = look
    sc.view_settings.exposure = exposure
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*sky, 1)
    bg.inputs["Strength"].default_value = sky_strength
    sc.world = world
    return sc


def set_resolution(res, aspect=0.625):
    """Width res pixels, height round(res * aspect), at 100 percent."""
    sc = bpy.context.scene
    sc.render.resolution_x = res
    sc.render.resolution_y = round(res * aspect)
    sc.render.resolution_percentage = 100


def new_camera(name="cam", clip_start=None):
    """Add a camera object, make it the scene camera and return it; clip_start defaults to 0.05 m."""
    clip_start = 0.05 / U if clip_start is None else clip_start
    sc = bpy.context.scene
    cam_d = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam_d.clip_start = clip_start * U
    return cam


def perspective_camera(loc, target, lens=24, sensor=36, shift_x=0.0, shift_y=0.0):
    """Camera at loc aimed at target; shift frames a level camera. Keep it outside every object after moving furniture."""
    cam = new_camera()
    cam.data.sensor_width = sensor
    cam.data.lens = lens
    cam.data.shift_x = shift_x
    cam.data.shift_y = shift_y
    look(cam, loc, target)
    return cam


def plan_camera(center, width, cut, floor_z=0.0, height=None):
    """Ortho camera looking straight down, height above floor_z (default 12 m). The near clip sits at the plan cut.

    Anything above the cut is clipped; the far clip reaches 6 m below floor_z.
    """
    height = 12.0 / U if height is None else height
    cam = new_camera()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = width * U
    cam.location = (center[0] * U, center[1] * U, (floor_z + height) * U)
    cam.rotation_euler = (0, 0, 0)
    cam.data.clip_start = (height - cut) * U
    cam.data.clip_end = height * U + 6
    return cam


def add_camera(view, res):
    """Camera from a VIEWS entry, with resolution set from res and the entry's aspect.

    Perspective: dict(loc, target, lens=24, aspect=0.625, shift_x=0, shift_y=0, hide=()).
    Plan: dict(plan=True, center=(x, y), width, cut, floor_z=0, aspect=1.0, hide=(), drop=(), keep=()).
    hide names prefixes left out of this view only. A perspective hide clears camera visibility only: the object
    still casts shadows, blocks light, and shows in reflections. A plan hide sets hide_render. Every plan view runs
    plan_cut and plan_light, so ceilings and scene lights are hidden; drop and keep are optional.
    """
    plan = view.get("plan")
    set_resolution(res, view.get("aspect", 1.0 if plan else 0.625))
    hide, drop, keep = (tuple(view.get(k, ())) for k in ("hide", "drop", "keep"))
    if plan:
        cam = plan_camera(view["center"], view["width"], view["cut"], view.get("floor_z", 0.0))
    else:
        cam = perspective_camera(view["loc"], view["target"], view.get("lens", 24),
                                 shift_x=view.get("shift_x", 0.0), shift_y=view.get("shift_y", 0.0))
    for ob in bpy.data.objects:
        if hide and ob.name.startswith(hide):
            if plan:
                ob.hide_render = True
            else:
                ob.visible_camera = False
    if plan:
        w, a = view["width"], view.get("aspect", 1.0)
        extent = (w, w * a) if a <= 1 else (w / a, w)
        plan_cut(view["cut"], view.get("floor_z", 0.0), hide, drop, keep)
        plan_light(view["center"], view.get("floor_z", 0.0), extent=extent)
    return cam


def _bounds_z(ob):
    zs = [(ob.matrix_world @ Vector(c)).z for c in ob.bound_box]
    return min(zs) / U, max(zs) / U


def plan_cut(cut, floor_z=0.0, hide=(), drop=(), keep=()):
    """Plan-view object rules by name prefix, with cut measured above floor_z.

    hide: never shown in plan (ceilings, fill lights, scale figures, wall tile, upper cabinets).
    drop: items taller than the cut are squashed about the floor plane to end 60 mm under the cut, so they still
    read in plan (closet hanging, fixtures) instead of being clipped to an outline.
    Everything else whose bottom is above the cut (headers, soffits) is hidden so it casts no stray shadow,
    unless its name starts with a prefix in keep. All lights are hidden: call plan_light() for an even overhead light.
    """
    top = floor_z + cut
    fz = floor_z * U
    bpy.context.view_layer.update()
    for ob in list(bpy.data.objects):
        if hide and ob.name.startswith(hide):
            ob.hide_render = True
        elif drop and ob.name.startswith(drop) and ob.type in ("MESH", "CURVE") and _bounds_z(ob)[1] > top:
            s = (cut * U - 0.06) / (_bounds_z(ob)[1] * U - fz)
            ob.matrix_world = (Matrix.Translation((0, 0, fz)) @ Matrix.Diagonal((1, 1, s, 1))
                               @ Matrix.Translation((0, 0, -fz)) @ ob.matrix_world)
    bpy.context.view_layer.update()
    for ob in list(bpy.data.objects):
        if ob.type == "LIGHT":
            ob.hide_render = True
        elif ob.type in ("MESH", "CURVE") and not (keep and ob.name.startswith(keep)):
            if _bounds_z(ob)[0] > top:
                ob.hide_render = True


def plan_light(center, floor_z=0.0, height=None, size=None, w_per_m2=6.0, extent=None):
    """One even overhead area light for plan views, height above floor_z, and a dim grey world.

    height defaults to 9 m. size defaults to the larger, per axis, of 36 by 18 m and 1.5 times extent, the plan's
    (x, y) span in project units. Energy is w_per_m2 times the light's area in square metres, so exposure does not
    depend on the project unit.
    """
    height = 9.0 / U if height is None else height
    if size is None:
        ex, ey = extent or (0.0, 0.0)
        size = (max(36.0 / U, 1.5 * ex), max(18.0 / U, 1.5 * ey))
    ld = bpy.data.lights.new("plan_overhead", "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = size[0] * U, size[1] * U
    ld.energy = w_per_m2 * size[0] * U * size[1] * U
    lo = bpy.data.objects.new("plan_overhead", ld)
    lo.location = (center[0] * U, center[1] * U, (floor_z + height) * U)
    bpy.context.scene.collection.objects.link(lo)
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1)
    bg.inputs["Strength"].default_value = 0.4


def project_points(points):
    """Points in project units to pixel (x, y) in the current camera, for PIL labels and rulers added after the render."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    bpy.context.view_layer.update()        # camera matrix_world is stale until the depsgraph updates
    rx = sc.render.resolution_x * sc.render.resolution_percentage / 100
    ry = sc.render.resolution_y * sc.render.resolution_percentage / 100
    out = []
    for p in points:
        q = world_to_camera_view(sc, sc.camera, Vector(p) * U)
        out.append((q.x * rx, (1 - q.y) * ry))
    return out


def render(out):
    """Render the scene camera to the PNG at out (made absolute), then print DONE <out>."""
    import os
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sc = bpy.context.scene
    sc.render.filepath = out
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print(f"DONE {out}")


# ---------------------------------------------------------------- plan-view overlays (drawn just under the cut)


def dotted_square(name, px, py, half, z, mat, dash=None, pitch=None, w=None):
    """Dotted outline of a square (an existing post) centred at px, py; half = half the side.

    dash, pitch and w default to 0.02 m, 0.04 m and 0.03 m.
    """
    dash = 0.02 / U if dash is None else dash
    pitch = 0.04 / U if pitch is None else pitch
    w = 0.03 / U if w is None else w
    h, k = _OV / U, 0
    for side in range(4):
        a = -half
        while a < half:
            b = min(half, a + dash)
            x0, x1, y0, y1 = ((px + a, px + b, py - half - w / 2, py - half + w / 2),
                              (px + a, px + b, py + half - w / 2, py + half + w / 2),
                              (px - half - w / 2, px - half + w / 2, py + a, py + b),
                              (px + half - w / 2, px + half + w / 2, py + a, py + b))[side]
            box(f"{name}_{k}", x0, x1, y0, y1, z, z + h, mat)
            k += 1
            a += pitch


def dashed_path(name, pts, z, mat, dash=None, gap=None, w=None):
    """Dashed line along a polyline (an outline of the floor above). Close it by repeating the first point.

    dash, gap and w default to 0.2 m, 0.12 m and 0.03 m.
    """
    dash = 0.2 / U if dash is None else dash
    gap = 0.12 / U if gap is None else gap
    w = 0.03 / U if w is None else w
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.dist((ax, ay), (bx, by))
        t = 0.0
        while t < L:
            e = min(L, t + dash)
            p0 = (ax + (bx - ax) * t / L, ay + (by - ay) * t / L)
            p1 = (ax + (bx - ax) * e / L, ay + (by - ay) * e / L)
            seg(name, p0, p1, w, z, z + _OV / U, mat)
            t += dash + gap


def dotted_rect(name, x0, x1, y0, y1, z, mat, dash=None, pitch=None, w=None):
    """Dotted outline of a rectangle (a wall to be removed).

    dash, pitch and w default to 0.09 m, 0.15 m and 0.025 m.
    """
    dash = 0.09 / U if dash is None else dash
    pitch = 0.15 / U if pitch is None else pitch
    w = 0.025 / U if w is None else w
    h, off = _OV / U, 0.012 / U
    yy = y0
    while yy < y1:
        for xx in (x0 - w - off, x1 + off):
            box(name, xx, xx + w, yy, min(y1, yy + dash), z, z + h, mat)
        yy += pitch
    for yy in (y0 - w - off, y1 + off):
        box(f"{name}_end", x0 - w - off, x1 + w + off, yy, yy + w, z, z + h, mat)
