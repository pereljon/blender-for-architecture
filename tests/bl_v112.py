"""Blender test: v1.1.2 (T52 coplanar_pairs, T53 cover marks, T54 number-suffix WARN, T55 thin buried depth, T57 broad
tie) from Revision 10 of the design. T56 (slab pierce) did not reproduce and has no test. T58 is in test_v112.py."""
import contextlib
import io
import os
import re
import shutil
import sys
import traceback

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, finish

import bhelpers as bh
import checks as ck


def reset():
    bh.set_units("m")
    bh.clear_scene()
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def upd():
    bpy.context.view_layer.update()


def run(**kw):
    """run_checks output lines and the exit code (None when it returns)."""
    buf = io.StringIO()
    code = None
    with contextlib.redirect_stdout(buf):
        try:
            ck.run_checks(**kw)
        except SystemExit as e:
            code = e.code
        except Exception as e:
            check(False, f"run_checks({kw}) raised {type(e).__name__}: {e}")
    return buf.getvalue().splitlines(), code


def run_raises(**kw):
    """(exception, console lines) when run_checks raises; (None, lines) otherwise."""
    buf = io.StringIO()
    err = None
    with contextlib.redirect_stdout(buf):
        try:
            ck.run_checks(**kw)
        except SystemExit:
            pass
        except Exception as e:
            err = e
    return err, buf.getvalue().splitlines()


def block(lines, check_name):
    """The header line of a check and the indented lines under it."""
    out, on = [], False
    for ln in lines:
        if re.match(rf"^(OK|FAIL|SKIP) {check_name}\b", ln):
            out, on = [ln], True
        elif on and ln.startswith("  "):
            out.append(ln)
        elif on:
            break
    return out


def first(lines, pattern):
    """Index of the first line that matches the regex, or None."""
    return next((i for i, ln in enumerate(lines) if re.match(pattern, ln)), None)


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def hit_dict(hits):
    return {h[0]: h[1] for h in hits}


def collection(name, objs):
    """A collection linked under the scene collection that holds objs and only objs."""
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    for o in objs:
        for oc in list(o.users_collection):
            oc.objects.unlink(o)
        c.objects.link(o)
    return c


def pair_set(lines):
    """The unordered pairs on the hit lines of the coplanar block."""
    return {frozenset(ln.split()) for ln in block(lines, "coplanar")[1:]}


# ---------------------------------------------------------------- T52: coplanar_pairs
def t52_scene():
    reset()
    bh.box("floor", -4, 4, -4, 4, -0.1, 0)
    bh.box("ceiling_hall", 0, 2, 0, 2, 2.40, 2.45)
    bh.box("ceiling_bath", 1.7, 3.5, 0, 2, 2.40, 2.45)
    bh.box("blocking_h", 0.2, 0.6, 0.2, 1.8, 2.42, 2.45)
    bh.box("wall_n", -0.1, 3.6, 2.0, 2.1, 0, 2.6)
    upd()


HALL_BATH = frozenset(("ceiling_hall", "ceiling_bath"))
HALL_BLOCK = frozenset(("ceiling_hall", "blocking_h"))
NOT_A_HIT = "WARN exempt coplanar_pairs: {} is not a coplanar hit"


def t52():
    t52_scene()
    base = pair_set(run(floors=("floor",))[0])
    check(base == {HALL_BATH, HALL_BLOCK}, f"T52 fixture: without exemptions the coplanar hits are the hall pairs: {base}")

    lines, code = run(floors=("floor",), exempt={"coplanar_pairs": [("blocking_h", "ceiling_hall")]})
    blk = block(lines, "coplanar")
    check(blk[:1] and blk[0].startswith("FAIL coplanar: 1 (") and pair_set(lines) == {HALL_BATH},
          f"T52 the reversed pair drops the hall and blocking hit, keeps the hall and bath hit: {blk}")
    check(not any(ln.startswith("WARN exempt") for ln in lines), f"T52 a pair that is a hit gives no WARN exempt line: {lines}")
    check(code == 1 and lines[-1:] == ["FAIL run_checks: coplanar"], f"T52 the verdict still fails coplanar (code {code}): {lines[-2:]}")

    both = [("blocking_h", "ceiling_hall"), ("ceiling_bath", "ceiling_hall")]
    lines, code = run(floors=("floor",), exempt={"coplanar_pairs": both})
    check(first(lines, r"^OK coplanar") is not None and not block(lines, "coplanar")[1:],
          f"T52 both pairs exempt: OK coplanar: {block(lines, 'coplanar')}")
    check(not any(ln.startswith("WARN exempt") for ln in lines), f"T52 both pairs are hits, so no WARN exempt line: {lines}")
    check(code is None and lines[-1:] == ["OK run_checks"], f"T52 both pairs exempt: run_checks passes (code {code}): {lines[-2:]}")

    miss = NOT_A_HIT.format("ceiling_hall wall_n")
    lines, code = run(floors=("floor",), exempt={"coplanar_pairs": [("ceiling_hall", "wall_n")]})
    i, j = first(lines, "^" + re.escape(miss) + "$"), first(lines, r"^(OK|FAIL) coplanar")
    check(i is not None and j is not None and i < j, f"T52 the not-a-hit WARN {miss!r} comes before the coplanar status line: {lines}")
    check(lines.count(miss) == 1, f"T52 the not-a-hit WARN appears once: {lines}")
    check(pair_set(lines) == {HALL_BATH, HALL_BLOCK}, f"T52 a pair that is no hit exempts nothing: {block(lines, 'coplanar')}")

    lines, code = run(floors=("floor",), exempt={"coplanar_pairs": [("ceiling_hall", "nope")]})
    check("WARN exempt coplanar_pairs: no object named nope" in lines, f"T52 the unknown-name WARN: {lines}")
    check(NOT_A_HIT.format("ceiling_hall nope") in lines, f"T52 the not-a-hit WARN for the pair with an unknown name: {lines}")

    # the object exemption alone drops every pair of the object: the masking that pairs avoid (passes before the change)
    lines, code = run(floors=("floor",), exempt={"coplanar": ["ceiling_hall"]})
    check(first(lines, r"^OK coplanar") is not None, f"T52 exempt coplanar ceiling_hall alone gives OK coplanar: {block(lines, 'coplanar')}")

    # a pair that an object exemption already hides, and a pair that overlaps already hides, is no hit
    lines, code = run(floors=("floor",), exempt={"coplanar": ["ceiling_hall"], "coplanar_pairs": [("ceiling_hall", "ceiling_bath")]})
    check(NOT_A_HIT.format("ceiling_hall ceiling_bath") in lines, f"T52 a pair hidden by an object exemption: not-a-hit WARN: {lines}")
    collection("ceilings", [bpy.data.objects["ceiling_hall"], bpy.data.objects["ceiling_bath"]])
    lines, code = run(floors=("floor",), overlaps=("ceilings",), exempt={"coplanar_pairs": [("ceiling_hall", "ceiling_bath")]})
    check(NOT_A_HIT.format("ceiling_hall ceiling_bath") in lines, f"T52 a pair hidden by overlaps: not-a-hit WARN: {lines}")
    check(pair_set(lines) == {HALL_BLOCK}, f"T52 the overlaps collection still leaves the hall and blocking hit: {block(lines, 'coplanar')}")

    # bad values raise before any check line prints
    for label, val in (("a bare pair", ("ceiling_hall", "blocking_h")), ("a list of one string", ["ceiling_hall"]),
                       ("a triple", [("a", "b", "c")]), ("a string", "ceiling_hall"), ("a pair with a non-string", [("a", 2)])):
        err, out = run_raises(floors=("floor",), exempt={"coplanar_pairs": val})
        check(isinstance(err, ValueError) and str(err) == "exempt coplanar_pairs: give a list of (name, name) pairs",
              f"T52 {label} raises the pairs ValueError: {err!r}")
        check(not any(re.match(r"^(OK|FAIL|SKIP) ", ln) for ln in out), f"T52 {label}: no check line printed before the error: {out}")
    err, _ = run_raises(floors=("floor",), exempt={"bogus": []})
    check(isinstance(err, ValueError) and "coplanar_pairs" in str(err), f"T52 the unknown-key error lists coplanar_pairs: {err!r}")

    # the coplanar check skipped for an error: no not-a-hit WARN
    real = ck.coplanar_check

    def boom(*a, **kw):
        raise RuntimeError("boom")

    ck.coplanar_check = boom
    try:
        lines, code = run(floors=("floor",), exempt={"coplanar_pairs": [("ceiling_hall", "wall_n")]})
    finally:
        ck.coplanar_check = real
    check("FAIL coplanar: error RuntimeError: boom" in lines, f"T52 fixture: the coplanar check errors: {lines}")
    check(not any("is not a coplanar hit" in ln for ln in lines), f"T52 an errored coplanar check prints no not-a-hit WARN: {lines}")


def t52_file():
    base = os.path.join(tcommon.OUT, "v112")
    path = os.path.join(base, "pairs", "checks.txt")
    shutil.rmtree(base, ignore_errors=True)
    t52_scene()
    lines, code = run(floors=("floor",), exempt={"coplanar_pairs": [("blocking_h", "ceiling_hall")]}, hits_file=path)
    if not check(os.path.isfile(path), "T52 the hits file exists"):
        return
    got = read_lines(path)
    check(not any("blocking_h" in ln for ln in got), f"T52 the hits file has no line for the exempt pair: {got}")
    check(sum(1 for ln in got if ln.startswith("    plane")) == 1, f"T52 the hits file has one detail line, for the pair left: {got}")
    check(any(re.match(r"^  ceiling_(hall|bath) ceiling_(hall|bath)$", ln) for ln in got), f"T52 the hall and bath hit line is in the file: {got}")

    miss = NOT_A_HIT.format("ceiling_hall wall_n")
    lines, code = run(floors=("floor",), exempt={"coplanar_pairs": [("ceiling_hall", "wall_n"), ("ceiling_hall", "nope")]}, hits_file=path)
    got = read_lines(path)
    for w in (miss, "WARN exempt coplanar_pairs: no object named nope", NOT_A_HIT.format("ceiling_hall nope")):
        check(w in got, f"T52 the hits file holds {w!r}: {got}")
    i, j = first(got, "^" + re.escape(miss) + "$"), first(got, r"^(OK|FAIL) coplanar")
    check(i is not None and j is not None and i < j, f"T52 in the file the not-a-hit WARN is before the coplanar status line: {got}")
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------- T53: cover marks
def plane_obj(name, x0, x1, y0, y1, z):
    """An open single-quad mesh."""
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))]
    bm.faces.new(vs)
    return bh.new_obj(name, bh._to_mesh(name, bm))


ENCLOSE = (-0.1, 1.6, -0.1, 1.1, 0.2, 0.4)
MARK = re.compile(r"; (buried|exposed|partly buried \((\d+) of (\d+) points\))$")


def mark_scene(tag, covers):
    """Plates a_<tag> and b_<tag> (Verified: they overlap on the tops and on two 5 mm side strips) and the covers."""
    reset()
    a, b = f"a_{tag}", f"b_{tag}"
    bh.box(a, 0, 1, 0, 1, 0.29, 0.3)
    bh.box(b, 0.5, 1.5, 0, 1, 0.295, 0.3)
    covers(tag)
    upd()
    return a, b


def read_mark(a, b, path):
    """The detail line of the pair a, b in the hits file and its regex match, or (None, None)."""
    got = read_lines(path)
    i = first(got, rf"^  ({a} {b}|{b} {a})$")
    if i is None:
        return None, None
    for ln in got[i + 1:]:
        if not ln.startswith("    "):
            break
        if ln.startswith("    plane"):
            return ln, MARK.search(ln)
    return None, None


def t53():
    base = os.path.join(tcommon.OUT, "v112")
    shutil.rmtree(base, ignore_errors=True)
    cases = (
        ("none", lambda t: None, "exposed"),
        ("enclose", lambda t: bh.box(f"cover_{t}", *ENCLOSE), "buried"),
        ("tops", lambda t: bh.box(f"cover_{t}", -0.1, 1.6, -0.1, 1.1, 0.3, 0.4), "partly"),
        ("part", lambda t: bh.box(f"cover_{t}", 0.5, 0.75, -0.1, 1.1, 0.2, 0.4), "partly"),
        ("open", lambda t: (plane_obj(f"sheet_{t}", -0.1, 1.6, -0.1, 1.1, 0.301),
                            setattr(bh.box(f"cover_{t}", *ENCLOSE), "hide_render", True)), "exposed"),
        ("thin", lambda t: bh.box(f"cover_{t}", -0.1, 1.6, -0.1, 1.1, 0.301, 0.3015), "exposed"),
        ("figure", lambda t: bh.box("man_cover", *ENCLOSE), "exposed"),
    )
    for tag, covers, want in cases:
        a, b = mark_scene(tag, covers)
        path = os.path.join(base, tag, "checks.txt")
        got = ck.coplanar_check()
        check(got and all(isinstance(h, tuple) and len(h) == 2 for h in got) and frozenset((a, b)) in {frozenset(h) for h in got},
              f"T53 {tag}: coplanar_check returns a list of 2-tuples that holds the pair: {got}")
        lines, code = run(floors=(), hits_file=path)
        check(first(lines, r"^FAIL coplanar") is not None and code == 1, f"T53 {tag}: the run still fails coplanar (code {code}): {lines}")
        check(not any(re.search(r"buried|exposed", ln) for ln in lines), f"T53 {tag}: the console holds no mark: {lines}")
        if not check(os.path.isfile(path), f"T53 {tag}: the hits file exists"):
            continue
        detail, m = read_mark(a, b, path)
        if not check(m, f"T53 {tag}: the detail line of the pair ends with a mark: {detail!r}"):
            continue
        if want == "partly":
            k, n = int(m.group(2) or -1), int(m.group(3) or -1)
            check(m.group(1).startswith("partly buried") and 0 < k < n, f"T53 {tag}: partly buried with 0 < k < n: {m.group(1)}")
        else:
            check(m.group(1) == want, f"T53 {tag}: want {want}, got {m.group(1)} ({detail!r})")
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------- T54: number-suffix WARN
def t54():
    base = os.path.join(tcommon.OUT, "v112")
    path = os.path.join(base, "names", "checks.txt")
    shutil.rmtree(base, ignore_errors=True)
    reset()
    bh.box("floor", -2, 8, -2, 2, -0.1, 0)
    for k, n in enumerate(("chair", "chair.001", "chair.002", "lamp.017", "hidden.001", "lamp.12", "pad.0012")):
        o = bh.box(n, 1.0 * k, 1.0 * k + 0.4, 0, 0.4, 0, 0.5)
        o.hide_render = n == "hidden.001"
    upd()
    check(all(n in bpy.data.objects for n in ("chair.001", "lamp.017", "pad.0012")), "T54 fixture: the suffixed names exist as given")
    want = "WARN names: 3 rendered meshes have a number suffix, such as chair.001"
    lines, code = run(floors=("nofloor",), overlaps=("nope",), hits_file=path)
    check(lines.count(want) == 1 and sum(1 for ln in lines if ln.startswith("WARN names")) == 1,
          f"T54 exactly one WARN names line {want!r}: {[ln for ln in lines if 'names' in ln]}")
    i, f, o = first(lines, "^" + re.escape(want) + "$"), first(lines, "^WARN floors"), first(lines, "^WARN overlaps")
    check(None not in (i, f, o) and f < i < o, f"T54 the line comes after the floors WARN and before the overlaps WARN: {lines[:5]}")
    check(os.path.isfile(path) and want in read_lines(path), "T54 the line is in the hits file")

    lines, code = run(floors=("floor",))
    clean_code, clean_last = code, lines[-1:]
    check(want in lines and clean_last == ["OK run_checks"] and clean_code is None,
          f"T54 the WARN changes no verdict (code {code}): {lines[-3:]}")

    bpy.data.objects["chair.001"].name = "chair_b"
    bpy.data.objects["chair.002"].name = "chair_c"
    bpy.data.objects["lamp.017"].name = "lamp_a"
    bpy.data.objects["hidden.001"].name = "hidden_b"
    upd()
    lines, code = run(floors=("floor",))
    check(not any(ln.startswith("WARN names") for ln in lines), f"T54 without suffixed names (lamp.12 and pad.0012 are not) there is no WARN names line: {lines}")
    check(code is None and lines[-1:] == ["OK run_checks"], f"T54 the verdict is the same without the WARN (code {code}): {lines[-2:]}")
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------- T55: the depth of a thin buried object
def t55():
    reset()
    bh.box("floor", -2, 2, -2, 2, -0.1, 0)
    bh.box("thin_15", 0, 0.3, 0, 0.3, -0.015, -0.010)
    bh.box("thin_40", 1, 1.3, 0, 0.3, -0.040, -0.035)
    bh.box("deep_35", -1.5, -1.2, 1.0, 1.3, -0.35, 0.2)
    bh.box("proud_15", -1, -0.7, 0, 0.3, -0.015, 0.005)
    upd()
    got = hit_dict(ck.floor_fit_check(("floor",)))
    check(got.get("thin_15") is not None and abs(got["thin_15"] + 0.015) <= 1e-3, f"T55 thin_15 reports its depth -0.015: {got}")
    check(got.get("thin_40") is not None and abs(got["thin_40"] + 0.040) <= 1e-3, f"T55 thin_40 keeps -0.04: {got}")
    check("deep_35" in got and got["deep_35"] is None, f"T55 an object 0.35 m deep keeps None: {got}")
    check("proud_15" not in got, f"T55 proud_15 passes: {got}")
    check(set(got) == {"thin_15", "thin_40", "deep_35"}, f"T55 only the three buried objects are reported: {got}")
    lines, _ = run(floors=("floor",))
    check("  thin_15 sunk 0.015 m" in lines, f"T55 the line reads 'thin_15 sunk 0.015 m': {block(lines, 'floor_fit')}")
    check("  deep_35 sunk more than 0.300 m" in lines, f"T55 deep_35 keeps 'sunk more than 0.300 m': {block(lines, 'floor_fit')}")

    # a 0.4 m deep object needs a floor thicker than the hang limit for its probe to start inside the floor
    reset()
    bh.box("floor", -2, 2, -2, 2, -0.5, 0)
    bh.box("deep_40", 0, 0.3, 0, 0.3, -0.4, 0.3)
    upd()
    got = hit_dict(ck.floor_fit_check(("floor",)))
    check("deep_40" in got and got["deep_40"] is None, f"T55 an object 0.4 m deep in a 0.5 m floor keeps None: {got}")


# ---------------------------------------------------------------- T57: broad tie
def t57():
    reset()
    bh.box("floor", -2, 8, -2, 2, -0.1, 0)
    for k in range(3):
        x = 2.5 * k
        bh.box(f"carcass_{k}", x, x + 0.6, 0, 0.6, 0, 0.9)
    bh.box("front_flush", 0.05, 0.55, 0, 0.02, 0.05, 0.35)
    bh.box("chest_flush", 2.5 + 0.1, 2.5 + 0.4, 0, 0.4, 0.05, 0.52)
    bh.box("front_out", 5.0 + 0.05, 5.0 + 0.55, -0.02, 0, 0.05, 0.35)
    upd()
    got = hit_dict(ck.floor_fit_check(("floor",)))
    check("front_flush" not in got, f"T57 a 20 mm front inside the carcass's plan box passes: {got}")
    check("chest_flush" in got and abs(got["chest_flush"] - 0.05) <= 1e-3, f"T57 the chest inside its carcass is reported floating 0.05 m: {got}")
    check("front_out" not in got, f"T57 a front outside the carcass's plan box passes: {got}")
    check(set(got) <= {"chest_flush"}, f"T57 nothing else is reported: {got}")


CASES = (t52, t52_file, t53, t54, t55, t57)


def main():
    for fn in CASES:
        try:
            fn()
        except Exception as e:
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finish("bl_v112")


main()
