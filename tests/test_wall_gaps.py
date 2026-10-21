"""Plain Python test: scripts/wall_gaps.py, wall_gaps() and wall_openings() (T16, Revision 6 R22)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcommon
from tcommon import SCRIPTS, check, finish

sys.path.insert(0, SCRIPTS)
try:
    import wall_gaps as wg
except ImportError as e:
    print("  FAIL cannot import wall_gaps:", e)
    sys.exit(1)

TOL = 1e-6


def same_hit(a, b, tol):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if isinstance(y, float):
            if not isinstance(x, (int, float)) or abs(x - y) > tol:
                return False
        elif isinstance(y, tuple):
            if not isinstance(x, tuple) or not same_hit(x, y, tol):
                return False
        elif x != y:
            return False
    return True


def same(got, want, tol=TOL):
    return len(got) == len(want) and all(same_hit(g, w, tol) for g, w in zip(got, want))


def gaps(label, rects, want, tol=TOL, **kw):
    got = wg.wall_gaps(rects, **kw)
    check(same(got, want, tol), f"wall_gaps {label}: want {want}, got {got}")


def openings(label, rects, want, **kw):
    got = wg.wall_openings(rects, **kw)
    check(same(got, want, TOL), f"wall_openings {label}: want {want}, got {got}")


def main():
    # gap between a wall end and a stem that stops short of the wall's line
    A = (0, 4, 0, 0.1)
    gaps("gap", [A, (3.9, 4.0, 0.15, 3)], [(0, 1, "gap", 0.05)])
    gaps("T joint", [A, (3.9, 4.0, 0.1, 3)], [])
    gaps("overlap", [A, (3.9, 4.0, 0, 3)], [])

    # corner point and partial butt
    B = (0, 3.9, 0, 0.1)
    gaps("corner point", [B, (3.9, 4.0, 0.1, 3)], [(0, 1, "corner", 0.0)])
    gaps("partial butt", [B, (3.9, 4.0, 0.05, 3)], [(0, 1, "corner", 0.05)])

    # jog and aligned thickness change
    gaps("jog", [(0, 2, 0, 0.1), (2, 4, 0.05, 0.15)], [(0, 1, "corner", 0.05)])
    gaps("aligned thickness change", [(0, 2, 0, 0.1), (2, 4, 0, 0.15)], [])

    # door-sized and narrower separations along a run
    gaps("door 0.9", [(0, 2, 0, 0.1), (2.9, 4, 0, 0.1)], [])
    gaps("0.3 gap", [(0, 2, 0, 0.1), (2.3, 4, 0, 0.1)], [(0, 1, "gap", 0.3)], tol=1e-9)
    gaps("0.31 is not a gap", [(0, 2, 0, 0.1), (2.31, 4, 0, 0.1)], [])

    gaps("diagonal", [(0, 2, 0, 0.1), (2.1, 2.2, 0.2, 3)], [(0, 1, "gap", math.hypot(0.1, 0.1))])

    # touch tolerance
    gaps("0.5 mm touches", [(0, 2, 0, 0.1), (2.0005, 4, 0, 0.1)], [])
    gaps("2 mm gap", [(0, 2, 0, 0.1), (2.002, 4, 0, 0.1)], [(0, 1, "gap", 0.002)])

    # feet dicts with unit
    feet = [dict(x0=0, x1=13, y0=0, y1=0.33), dict(x0=12.67, x1=13, y0=0.5, y1=10)]
    gaps("feet dicts", feet, [(0, 1, "gap", 0.17 * 0.3048)], unit=0.3048)

    # indices follow the input order; a six-item tuple with x0 > x1 is accepted
    gaps("out of order", [(6, 4.1, 0, 0.1, 0, 2.6), (0, 2, 0, 0.1), (2, 4, 0, 0.1), (-0.2, -0.1, 0, 3)],
         [(0, 2, "gap", 0.1), (1, 3, "gap", 0.1)])

    # junctions filled by a third piece (G1)
    gaps("T with its own square", [(0, 2, 0, 0.1), (2, 2.1, 0, 0.1), (2.1, 4, 0, 0.1), (2, 2.1, 0.1, 3)], [])
    gaps("stem through a split wall", [(0, 2, 0, 0.1), (2.1, 4, 0, 0.1), (2, 2.1, 0, 3)], [])
    gaps("X crossing", [(0, 4, 1, 1.1), (2, 2.1, 0, 1), (2, 2.1, 1.1, 3)], [])
    gaps("L with a corner square", [(0, 3.9, 0, 0.1), (3.9, 4, 0, 0.1), (3.9, 4, 0.1, 3)], [])
    gaps("jog closed by a column", [(0, 2, 0, 0.1), (2, 4, 0.05, 0.15), (1.9, 2.1, -0.05, 0.2)], [])

    gaps("corner to corner", [(0, 2, 0, 0.1), (2.1, 4, 0.1, 0.2)], [(0, 1, "gap", 0.1)])

    # levels
    gaps("other level", [(0, 4, 0.0, 0.1, 0, 2.6), (3.9, 4.0, 0.15, 3, 3, 5.6)], [])
    gaps("stem on the level above does not fill",
         [(0, 2, 0, 0.1, 0, 2.6), (2.1, 4, 0, 0.1, 0, 2.6), (2, 2.1, 0, 3, 3, 5.6)],
         [(0, 1, "gap", 0.1)])

    # wall_openings
    openings("door along x", [(0, 2, 0, 0.1), (2.9, 4, 0, 0.1)], [(0, 1, 0.9, (2.0, 2.9, 0.0, 0.1))])
    openings("door along y", [(0, 0.1, 0, 2), (0, 0.1, 2.9, 4)], [(0, 1, 0.9, (0.0, 0.1, 2.0, 2.9))])
    openings("crossing wall", [(0, 2, 0, 0.1), (2.9, 4, 0, 0.1), (2.2, 2.3, -3, 3)], [])
    openings("bands overlap under half", [(0, 2, 0, 0.1), (2.9, 4, 0.06, 0.16)], [])
    openings("separation 0.2 is a gap", [(0, 2, 0, 0.1), (2.2, 4, 0, 0.1)], [])
    openings("separation 3.0", [(0, 2, 0, 0.1), (5.0, 7, 0, 0.1)], [])
    openings("second wall on the level above", [(0, 2, 0, 0.1, 0, 2.6), (2.9, 4, 0, 0.1, 3, 5.6)], [])
    openings("feet", [(0, 6, 0, 0.33), (9, 12, 0, 0.33)],
             [(0, 1, 3 * 0.3048, (6 * 0.3048, 9 * 0.3048, 0.0, 0.33 * 0.3048))], unit=0.3048)

    finish("test_wall_gaps")


main()
