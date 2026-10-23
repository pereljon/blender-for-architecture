"""Plain-Python tests for v1.1.1 (T48), from Revision 9 of the design: reference/api.md, SKILL.md, and the CHANGELOG
stay in step with scripts/checks.py.

SKILL_DIR overrides the skill folder (default: the parent of tests/); SCRIPTS_DIR overrides its scripts folder.
"""
import ast
import os
import re
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SKILL_DIR") or os.path.dirname(HERE)
SCRIPTS = os.environ.get("SCRIPTS_DIR") or os.path.join(ROOT, "scripts")
FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)
        print("  FAIL", msg)
    return bool(cond)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def module_constants(tree):
    """{name: value} of the module-level assignments whose value is a literal."""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return out


def default_text(node, consts):
    try:
        return repr(ast.literal_eval(node))
    except ValueError:
        if isinstance(node, ast.Name) and node.id in consts:
            return repr(consts[node.id])
        raise


def signature(fn, consts):
    """The arguments of fn as inspect.signature prints them, without the parentheses."""
    a = fn.args
    parts = []
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    for i, (arg, d) in enumerate(zip(pos, defaults)):
        parts.append(arg.arg if d is None else f"{arg.arg}={default_text(d, consts)}")
        if a.posonlyargs and i == len(a.posonlyargs) - 1:
            parts.append("/")
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    elif a.kwonlyargs:
        parts.append("*")
    for arg, d in zip(a.kwonlyargs, a.kw_defaults):
        parts.append(arg.arg if d is None else f"{arg.arg}={default_text(d, consts)}")
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return ", ".join(parts)


def t48_api():
    with open(os.path.join(SCRIPTS, "checks.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    consts = module_constants(tree)
    doc = read("reference", "api.md")
    start = doc.index("## checks.py")
    end = doc.find("\n## ", start + 1)
    section = doc[start:end if end > 0 else len(doc)]
    lines = {m.group(1): m.group(2) for m in re.finditer(r"^- `(\w+)\((.*)\)`\s*$", section, re.M)}
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    check(len(funcs) >= 8, f"T48 checks.py has its public functions, found {[f.name for f in funcs]}")
    for fn in funcs:
        want = signature(fn, consts)
        got = lines.get(fn.name)
        check(got == want, f"T48 reference/api.md line for {fn.name}: want `{fn.name}({want})`, got "
                           f"{'`' + fn.name + '(' + got + ')`' if got is not None else 'no line'}")


def t48_skill():
    text = read("SKILL.md")
    for needle in ("overlaps", "hits_file", "finishes", "WARN overlaps: no collection named", "WARN overlaps: collection",
                   "is a floor or wall", "NOTE coplanar: pairs inside collection", "NOTE full hit list:"):
        check(needle in text, f"T48 SKILL.md holds {needle!r}")


def t48_changelog():
    log = read("CHANGELOG.md")
    # The v1.1.1 section, headed "Unreleased" until the release retitles it [1.1.1]. From v1.1.2 on it is the [1.1.1] section.
    m = re.search(r"^## \[1\.1\.1\][^\n]*\s*$", log, re.M) or re.search(r"^## \[?Unreleased\]?\s*$", log, re.M)
    if not check(m, "T48 the CHANGELOG has an Unreleased or [1.1.1] heading"):
        return
    end = re.search(r"^## ", log[m.end():], re.M)
    body = log[m.end():m.end() + end.start()] if end else log[m.end():]
    check("checks.floor_fit_check()" in body, "T48 the v1.1.1 CHANGELOG section names `checks.floor_fit_check()`")
    check("Semantic Versioning" in body, "T48 the v1.1.1 CHANGELOG section holds the words Semantic Versioning")


CASES = (t48_api, t48_skill, t48_changelog)


def main():
    for fn in CASES:
        try:
            fn()
        except Exception as e:
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    sys.stdout.flush()
    if FAILURES:
        print(f"TESTFAIL test_v111: {len(FAILURES)} failure(s)")
        sys.exit(1)
    print("TESTPASS test_v111")


main()
