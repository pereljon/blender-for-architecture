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
ID_A, ID_B = "0LsK0nZyHFlxwxEtjB7M2z", "3VGLPhqwnD8foTTakatrfq"      # GlobalIds as Bonsai writes them (22 characters)
ID_C, ID_D, ID_E = "30Gj94RxX05f_2shwwn9ff", "0Mujw9x95BvQSXR9U90_wS", "0zOjAGR4n78fMBc9yOdrlz"
M10 = "[[10.000000,0.000000,249.999995],[0.000000,10.000000,249.999995],[0.000000,0.000000,1.000000]]"

HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:ifc="http://www.ifcopenshell.org/ns" '
        'viewBox="0 0 500.0 500.0" width="500.0mm" height="500.0mm">'
        '<defs><marker id="m"><g><path d="M 11 3.5 L 11 10.5 L 1 7" class="annotation"/></g></marker></defs>')


def svg_of(body, matrix3=M10, plane_z=1.6):
    plane = f"[[1,0,0,0],[0,1,0,0],[0,0,1,{plane_z}],[0,0,0,1]]"
    return (HEAD + f'<g ifc:name="Elevation LEVEL 1 PLAN" class="section" ifc:plane="{plane}" ifc:matrix3="{matrix3}">'
            f'{body}</g></svg>')


def rect_path(box, sx, tx, ty):
    """Closed rectangle in SVG millimetres for a model box in metres: x = sx*X + tx, y = ty - sx*Y."""
    x0, x1, y0, y1 = box
    p = [(sx * x0 + tx, ty - sx * y0), (sx * x1 + tx, ty - sx * y0), (sx * x1 + tx, ty - sx * y1), (sx * x0 + tx, ty - sx * y1)]
    return "M" + " L".join(f"{x:.6f},{y:.6f}" for x, y in p) + " Z"


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


def same_box(got, want):
    return max(abs(a - b) for a, b in zip(got, want)) <= TOL


def expect(label, svg, want_groups, cut_z=1.6):
    """want_groups: list of (ids tuple, box)."""
    cz, groups = ifc_walls.drawing_walls(write("t25.svg", svg))
    check(abs(cz - cut_z) <= TOL, f"T25 {label}: cut_z {cz} (need {cut_z})")
    check([g[0] for g in groups] == [w[0] for w in want_groups], f"T25 {label}: ids {[g[0] for g in groups]} (need {[w[0] for w in want_groups]})")
    if len(groups) == len(want_groups):
        for (ids, box), (_, want) in zip(groups, want_groups):
            check(same_box(box, want), f"T25 {label}: {ids} box {tuple(round(v, 6) for v in box)} vs {tuple(round(v, 6) for v in want)}")


# Two separate wall groups, the class words in Bonsai's order, with a projection group that must be left out.
two_walls = svg_of(
    f'<g id="product-1" class="IfcWall material-null projection" ifc:name="ew" ifc:guid="{ID_A}">'
    '<path d="M280.47,249.99 L249.99,249.99"/></g>'
    f'<g class="IfcWall {ID_B} cut material-null"><path d="M310.96,239.52 L310.96,219.52 L310.436,219.52 '
    'L309.436,219.52 L309.436,230.0 L309.436,250.0 L309.96,250.0 L310.96,250.0 Z"/></g>'
    f'<g class="cut material-null IfcWall {ID_A}"><path d="M260.48,250.0 L280.48,250.0 L280.48,249.476 '
    'L280.48,248.476 L270.0,248.476 L250.0,248.476 L250.0,249.0 L250.0,250.0 Z"/></g>')
expect("two walls, scale 10", two_walls, sorted([((ID_A,), EW), ((ID_B,), NS)]))

scaled = svg_of(
    f'<g class="cut IfcWall {ID_A} material-null"><path d="{rect_path(EW, 20, 100, 300)}"/></g>'
    f'<g class="material-null cut {ID_B} IfcWall"><path d="{rect_path(NS, 20, 100, 300)}"/></g>',
    matrix3="[[20,0,100],[0,20,300],[0,0,1]]")
expect("two walls, scale 20 offset (100, 300)", scaled, sorted([((ID_A,), EW), ((ID_B,), NS)]))

# A merged group: Bonsai lists every GlobalId of the joined walls in the class.
L_PATH = "M251.524,207.328 L250.0,207.328 L250.0,250.0 L323.152,250.0 L323.152,248.476 L251.524,248.476 Z"
merged = svg_of(f'<g class="IfcWall {ID_D} material-null {ID_E} cut"><path d="{L_PATH}"/></g>')
expect("merged L-shape", merged, [(tuple(sorted((ID_D, ID_E))), (0.0, 7.3152, 0.0, 4.2672))])

# A column: no GlobalId in the class, an ifc:guid attribute instead.
column = svg_of(f'<g ifc:guid="{ID_C}" ifc:name="wall_5" class="IfcColumn material-null cut">'
                '<path d="M288.0999994277954,231.18800044059753 L288.0999994277954,230.18800044059753 '
                'L286.5759994277954,230.18800044059753 L286.5759994277954,231.18800044059753 Z"/></g>')
expect("column with ifc:guid", column, [((ID_C,), (3.6576, 3.81, 1.8812, 1.9812))])

# A closed room: one group, an outer ring and a hole in one path. The box is the outer ring's.
outer = (0.0, 12 * FT, 0.0, 10 * FT)
hole = (0.5 * FT, 11.5 * FT, 0.5 * FT, 9.5 * FT)
room = svg_of(f'<g class="IfcWall {ID_A} {ID_B} material-null {ID_C} cut">'
              f'<path d="{rect_path(outer, 10, 249.999995, 249.999995)} {rect_path(hole, 10, 249.999995, 249.999995)}"/></g>')
expect("closed room with a hole", room, [(tuple(sorted((ID_A, ID_B, ID_C))), outer)])

# A plane at another height is read from ifc:plane.
expect("cut height 2.2", svg_of(f'<g class="cut IfcWall {ID_A}"><path d="{rect_path(EW, 10, 249.999995, 249.999995)}"/></g>', plane_z=2.2),
       [((ID_A,), EW)], cut_z=2.2)

# Groups without a GlobalId or a point are left out.
nothing = svg_of('<g class="cut IfcWall"><path d="M250,250 L260,250 L260,240 Z"/></g>'
                 f'<g class="cut IfcWall {ID_A}"></g>')
expect("group without id or point", nothing, [])

arc = two_walls.replace("L310.96,250.0 Z", "A5,5 0 0 1 310.96,250.0 Z")
check(raises(ifc_walls.drawing_walls, write("t25_arc.svg", arc)), "T25 a path with an A command raises ValueError")
rel = two_walls.replace("L310.96,250.0 Z", "l0.5,0 Z")
check(raises(ifc_walls.drawing_walls, write("t25_rel.svg", rel)), "T25 a path with a lowercase l raises ValueError")
two = two_walls.replace("</svg>", f'<g class="section" ifc:matrix3="{M10}"></g></svg>')
check(raises(ifc_walls.drawing_walls, write("t25_two.svg", two)), "T25 two drawing groups raise ValueError")
none = two_walls.replace("ifc:matrix3", "ifc:matrix4")
check(raises(ifc_walls.drawing_walls, write("t25_none.svg", none)), "T25 no drawing group raises ValueError")

finish("test_ifc_walls")
