"""Shared helpers for the Blender test scripts: path setup, assertions, world-space extents."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SCRIPTS = os.environ.get("SCRIPTS_DIR") or os.path.normpath(os.path.join(HERE, "..", "scripts"))
os.makedirs(OUT, exist_ok=True)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)
        print("  FAIL", msg)
    return bool(cond)


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def extents(ob):
    """World-space (min, max) corners over the object's mesh vertices (no modifiers)."""
    import bpy
    bpy.context.view_layer.update()  # matrix_world is stale until the depsgraph updates
    me = ob.data
    pts = [ob.matrix_world @ v.co for v in me.vertices]
    lo = tuple(min(p[i] for p in pts) for i in range(3))
    hi = tuple(max(p[i] for p in pts) for i in range(3))
    return lo, hi


def dims(ob):
    lo, hi = extents(ob)
    return tuple(hi[i] - lo[i] for i in range(3))


def finish(name):
    sys.stdout.flush()
    if FAILURES:
        print(f"TESTFAIL {name}: {len(FAILURES)} failure(s)")
        sys.stdout.flush()
        os._exit(1)
    print(f"TESTPASS {name}")


def script_args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
