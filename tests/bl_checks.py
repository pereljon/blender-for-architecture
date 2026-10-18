"""Blender test: clash_check, coplanar_check and fail_on behave as the contract states."""
import contextlib
import io

import bpy

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, finish

import bhelpers as bh
import checks as ck


def reset(unit="m"):
    bh.set_units(unit)
    bh.clear_scene()


def pair_set(hits):
    return {frozenset(h) for h in hits}


def main():
    # ---- clash_check
    reset()
    bh.box("man_a", 0, 1, 0, 1, 0, 1)
    bh.box("wall_b", 0.5, 2, 0, 1, 0, 1)
    hits = ck.clash_check(("man_",), ("wall_",))
    check(("man_a", "wall_b") in [tuple(h) for h in hits], f"overlapping pair is a hit: {hits}")
    check(ck.clash_check(("man_",), ("wall_",), ignore=("wall_b",)) == [], "ignore drops the pair")

    reset()
    bh.box("man_a", 0, 1, 0, 1, 0, 1)
    bh.box("wall_b", 3, 4, 0, 1, 0, 1)
    check(ck.clash_check(("man_",), ("wall_",)) == [], "clear pair has no hit")

    reset()
    bh.box("man_a", 4.4, 4.6, 0.4, 0.6, 0.4, 0.6)
    bh.box("wall_b", 4, 5, 0, 1, 0, 1)
    hits = ck.clash_check(("man_",), ("wall_",))
    check(("man_a", "wall_b") in [tuple(h) for h in hits], f"fully contained small box is a hit: {hits}")

    reset("ft")
    bh.box("man_a", 4.4, 4.6, 0.4, 0.6, 0.4, 0.6)
    bh.box("wall_b", 4, 5, 0, 1, 0, 1)
    check(len(ck.clash_check(("man_",), ("wall_",))) == 1, "containment hit in feet")

    # ---- coplanar_check
    reset()
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    bh.box("cp_b", 1, 3, 0.5, 2.5, 0, 1)
    hits = ck.coplanar_check()
    check(pair_set(hits) == {frozenset(("cp_a", "cp_b"))}, f"coplanar overlapping boxes are reported: {hits}")
    check(pair_set(ck.coplanar_check(prefixes=("cp_",))) == {frozenset(("cp_a", "cp_b"))}, "prefix filter keeps pair")
    check(ck.coplanar_check(prefixes=("zz_",)) == [], "prefix filter excludes other objects")
    check(ck.coplanar_check(min_area=10.0) == [], "min_area above the overlap area reports nothing")

    reset()
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    bh.box("cp_b", 1, 3, 0.5, 2.5, 0.002, 1.002)
    check(ck.coplanar_check() == [], f"no hit after a 2 mm offset: {ck.coplanar_check()}")
    check(len(ck.coplanar_check(tol=0.005)) == 1, "a looser tol catches the 2 mm offset")

    reset()
    bh.box("cp_a", 0, 1, 0, 1, 0, 1)
    bh.box("cp_b", 1, 2, 0, 1, 0, 1)
    check(ck.coplanar_check() == [], f"a butt joint (faces back to back) is not reported: {ck.coplanar_check()}")

    reset("ft")
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    bh.box("cp_b", 1, 3, 0.5, 2.5, 0, 1)
    check(len(ck.coplanar_check()) == 1, "coplanar pair in feet")
    bh.clear_scene()
    bh.box("cp_a", 0, 2, 0, 2, 0, 1)
    bh.box("cp_b", 1, 3, 0.5, 2.5, 0.002 / 0.3048, 1 + 0.002 / 0.3048)
    check(ck.coplanar_check() == [], "2 mm offset expressed in feet clears the pair (tol is metres)")

    # ---- fail_on
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ck.fail_on([], "empty")
    check("OK empty" in buf.getvalue(), f"fail_on prints OK label: {buf.getvalue()!r}")
    buf = io.StringIO()
    code = None
    try:
        with contextlib.redirect_stdout(buf):
            ck.fail_on([("a", "b")], "clashes")
    except SystemExit as e:
        code = e.code
    check(code == 1 and "FAIL clashes" in buf.getvalue(), f"fail_on exits 1 and prints FAIL: {code} {buf.getvalue()!r}")
    finish("bl_checks")


main()
