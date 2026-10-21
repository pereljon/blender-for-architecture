"""Plain Python test: scripts/ifc_walls.py drawing_walls() (T25, Revision 5b R33), with no ifcopenshell installed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcommon
from tcommon import OUT, SCRIPTS, check, finish

sys.path.insert(0, SCRIPTS)
try:
    import ifc_walls
except ImportError as e:
    print("  FAIL cannot import ifc_walls:", e)
    sys.exit(1)

check("ifcopenshell" not in sys.modules and "numpy" not in sys.modules,
      "T25 importing ifc_walls does not import ifcopenshell or numpy")

TOL = 1e-6
FT = 0.3048
# Model boxes in metres (x0, x1, y0, y1): the observed two-wall drawing, 10 ft east-west wall and a 10 ft north-south wall.
EW = (0.0, 10 * FT, 0.0, 0.5 * FT)
NS = (19.5 * FT, 20 * FT, 0.0, 10 * FT)
GID_EW, GID_NS = "0LsK0nZyHFlxwxEtjB7M2z", "3VGLPhqwnD8foTTakatrfq"

HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:ifc="http://www.ifcopenshell.org/ns" '
        'viewBox="0 0 500.0 500.0" width="500.0mm" height="500.0mm">'
        '<defs><marker id="m"><g><path d="M 11 3.5 L 11 10.5 L 1 7" class="annotation"/></g></marker></defs>')


def section(matrix3, body, plane_z=1.6):
    plane = f"[[1,0,0,0],[0,1,0,0],[0,0,1,{plane_z}],[0,0,0,1]]"
    return (f'<g ifc:name="Elevation LEVEL 1 PLAN" class="section" ifc:plane="{plane}" ifc:matrix3="{matrix3}">'
            f'{body}</g>')


# As Bonsai wrote them: the projection group has ifc:guid and no "cut"; the cut groups list the class words in any order.
OBSERVED = HEAD + section(
    "[[10.000000,0.000000,249.999995],[0.000000,10.000000,249.999995],[0.000000,0.000000,1.000000]]",
    f'<g id="product-1" class="IfcWall material-null projection" ifc:name="ew" ifc:guid="{GID_EW}">'
    '<path d="M280.47,249.99 L249.99,249.99"/></g>'
    f'<g class="cut material-null {GID_NS} IfcWall"><path d="M310.96,239.52 L310.96,219.52 L310.436,219.52 '
    'L309.436,219.52 L309.436,230.0 L309.436,250.0 L309.96,250.0 L310.96,250.0 Z"/></g>'
    f'<g class="cut material-null IfcWall {GID_EW}"><path d="M260.48,250.0 L280.48,250.0 L280.48,249.476 '
    'L280.48,248.476 L270.0,248.476 L250.0,248.476 L250.0,249.0 L250.0,250.0 Z"/></g>') + '</svg>'


def rect_path(box, sx, tx, ty):
    """Closed rectangle path in SVG millimetres for a model box in metres: x = sx*X + tx, y = ty - sx*Y."""
    x0, x1, y0, y1 = box
    p = [(sx * x0 + tx, ty - sx * y0), (sx * x1 + tx, ty - sx * y0), (sx * x1 + tx, ty - sx * y1), (sx * x0 + tx, ty - sx * y1)]
    return "M" + " L".join(f"{x:.6f},{y:.6f}" for x, y in p) + " Z"


SCALED = HEAD + section(
    "[[20,0,100],[0,20,300],[0,0,1]]",
    f'<g class="cut IfcWall {GID_EW} material-null"><path d="{rect_path(EW, 20, 100, 300)}"/></g>'
    f'<g class="material-null cut {GID_NS} IfcWall"><path d="{rect_path(NS, 20, 100, 300)}"/></g>') + '</svg>'


def write(name, text):
    path = os.path.join(OUT, name)
    with open(path, "w") as fh:
        fh.write(text)
    return path


def raises(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return True
    except Exception as e:
        print("   raised", repr(e))
        return False
    return False


for label, svg in (("scale 10, offset 250", OBSERVED), ("scale 20, offset (100, 300)", SCALED)):
    got = ifc_walls.drawing_walls(write("t25.svg", svg))
    check(set(got) == {GID_EW, GID_NS}, f"T25 {label}: keys are the two cut GlobalIds (got {sorted(got)})")
    for gid, box in ((GID_EW, EW), (GID_NS, NS)):
        if gid in got:
            off = max(abs(a - b) for a, b in zip(got[gid], box))
            check(off <= TOL, f"T25 {label}: {gid} box {tuple(round(v, 6) for v in got[gid])} vs {tuple(round(v, 6) for v in box)} (off {off:.2e} m)")

arc = OBSERVED.replace("L310.96,250.0 Z", "A5,5 0 0 1 310.96,250.0 Z")
check(raises(ifc_walls.drawing_walls, write("t25_arc.svg", arc)), "T25 a path with an A command raises ValueError")
two = OBSERVED.replace("</svg>", section("[[10,0,250],[0,10,250],[0,0,1]]", "") + "</svg>")
check(raises(ifc_walls.drawing_walls, write("t25_two.svg", two)), "T25 two drawing groups raise ValueError")
none = OBSERVED.replace("ifc:matrix3", "ifc:matrix4")
check(raises(ifc_walls.drawing_walls, write("t25_none.svg", none)), "T25 no drawing group raises ValueError")

finish("test_ifc_walls")
