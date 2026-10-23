"""Plain-Python tests for v1.1.2 (T58), from Revision 10 of the design: reference/scripts.md, reference/api.md, README.md,
SKILL.md, the CHANGELOG, and the dump_diff script in reference/migration.md stay in step with the code.

SKILL_DIR overrides the skill folder (default: the parent of tests/).
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SKILL_DIR") or os.path.dirname(HERE)
FAILURES = []

SCRIPTS = ("templates/scene_template.py", "bhelpers.py", "checks.py", "sheets.py", "extract_plan.py", "compose.py",
           "annotate_plan.py", "ifc_walls.py", "mannequin.py", "wall_gaps.py")


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)
        print("  FAIL", msg)
    return bool(cond)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def section(text, heading, level=2):
    """The body under a heading, up to the next heading of the same or a higher level; None when it is absent."""
    m = re.search(rf"^{'#' * level} {re.escape(heading)}[^\n]*$", text, re.M)
    if not m:
        return None
    end = re.search(rf"^#{{1,{level}}} ", text[m.end():], re.M)
    return text[m.end():m.end() + end.start()] if end else text[m.end():]


def template_flags():
    tree = ast.parse(read("templates", "scene_template.py"))
    flags = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            flags += [a.value for a in node.args if isinstance(a, ast.Constant) and str(a.value).startswith("--")]
    return flags


def t58_scripts_doc():
    path = os.path.join(ROOT, "reference", "scripts.md")
    if not check(os.path.isfile(path), "T58 reference/scripts.md exists"):
        return
    doc = read("reference", "scripts.md")
    for s in SCRIPTS:
        check(os.path.basename(s) in doc, f"T58 scripts.md names {s}")
    flags = template_flags()
    check(len(flags) >= 7, f"T58 fixture: the template defines its flags, found {flags}")
    for f in flags:
        check(f in doc, f"T58 scripts.md holds the template flag {f}")
    check(any("--dump" in ln and "migration.md" in ln for ln in doc.splitlines()), "T58 scripts.md holds --dump with a link to migration.md")
    check(any("--ifc" in ln and "extensions.md" in ln for ln in doc.splitlines()), "T58 scripts.md holds --ifc with a link to extensions.md")


def t58_api_doc():
    doc = read("reference", "api.md")
    check(not re.search(r"^#+ Command-line scripts", doc, re.M | re.I), "T58 api.md has no heading 'Command-line scripts'")
    m = re.search(r"^- `run_checks\(.*?(?=^- `|^## |\Z)", doc, re.M | re.S)
    check(m and "coplanar_pairs" in m.group(0), "T58 the run_checks entry of api.md holds coplanar_pairs")


def t58_readme():
    doc = read("README.md")
    heads = re.findall(r"^## (.+)$", doc, re.M)
    if not check("The scripts" in heads and "What it does not do" in heads and heads.index("The scripts") == heads.index("What it does not do") + 1,
                 f"T58 README has '## The scripts' right after '## What it does not do': {heads}"):
        return
    body = section(doc, "The scripts")
    check("reference/scripts.md" in body, "T58 README's The scripts section links reference/scripts.md")
    rows = [ln for ln in body.splitlines() if ln.startswith("|")][2:]
    firsts = [re.sub(r"[`\s]", "", r.split("|")[1]) for r in rows]
    check(firsts == list(SCRIPTS), f"T58 README's table lists the ten scripts in order: {firsts}")
    built = section(doc, "How a model gets built")
    para = next((p for p in (built or "").split("\n\n") if p.startswith("**The scene script.**")), None)
    if check(para, "T58 README has the scene-script paragraph under 'How a model gets built'"):
        check("--" not in para and "LIB" not in para, f"T58 the scene-script paragraph holds no '--' and no 'LIB': {para!r}")


def t58_skill():
    text = read("SKILL.md")
    for needle in ("coplanar_pairs", "WARN exempt coplanar_pairs:", "WARN names:", "partly buried", "reference/scripts.md"):
        check(needle in text, f"T58 SKILL.md holds {needle!r}")


def t58_changelog():
    log = read("CHANGELOG.md")
    # The v1.1.2 section, headed "Unreleased" until the release retitles it [1.1.2].
    body = section(log, "[1.1.2]")
    if body is None:
        body = section(log, "Unreleased")
    if not check(body is not None, "T58 the CHANGELOG has an '## Unreleased' or '## [1.1.2]' section"):
        return
    check("checks.run_checks()" in body, "T58 the v1.1.2 CHANGELOG section names `checks.run_checks()`")
    check("checks.floor_fit_check()" in body, "T58 the v1.1.2 CHANGELOG section names `checks.floor_fit_check()`")
    check("Semantic Versioning" in body, "T58 the v1.1.2 CHANGELOG section holds the words Semantic Versioning")


def run_dump_diff(code, a, b, names=None):
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for label, data in (("a", a), ("b", b), ("names", names)):
            if data is None:
                continue
            p = os.path.join(tmp, label + ".json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            files.append(p)
        script = os.path.join(tmp, "dump_diff.py")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(code)
        out = subprocess.run([sys.executable, "-I", script, *files], capture_output=True, text=True, timeout=30)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def t58_dump_diff():
    section_text = section(read("reference", "migration.md"), "Compare and decide")
    if not check(section_text, "T58 migration.md has a 'Compare and decide' section"):
        return
    blocks = re.findall(r"```python\n(.*?)```", section_text, re.S)
    code = next((b for b in blocks if "def diff(" in b), None)
    if not check(code, "T58 'Compare and decide' holds a python block that defines diff("):
        return
    base = {"wall_a": {"loc": [0.0, 1.0, 2.0], "dims": [1.0, 2.0, 3.0], "mat": "paint"}, "cam": {"fov": 0.5}}
    near = {"wall_a": {"loc": [0.0, 1.0 + 1e-6, 2.0], "dims": [1.0, 2.0, 3.0], "mat": "paint"}, "cam": {"fov": 0.5 + 1e-6}}
    far = {"wall_a": {"loc": [0.0, 1.0 + 1e-4, 2.0], "dims": [1.0, 2.0, 3.0], "mat": "paint"}, "cam": {"fov": 0.5}}
    renamed = {"wall_main": base["wall_a"], "cam": base["cam"]}

    rc, out, err = run_dump_diff(code, base, near)
    check(rc == 0 and out == "SAME", f"T58 dumps that differ by 1e-6 print SAME: rc {rc}, {out!r}, {err!r}")
    rc, out, err = run_dump_diff(code, base, far)
    check(rc == 0 and out != "SAME" and "wall_a" in out and "loc" in out, f"T58 a 1e-4 difference prints a line that names the key: {out!r}, {err!r}")
    rc, out, err = run_dump_diff(code, base, renamed, {"wall_a": "wall_main"})
    check(rc == 0 and out == "SAME", f"T58 a renamed object with a name map prints SAME: rc {rc}, {out!r}, {err!r}")
    rc, out, err = run_dump_diff(code, base, renamed)
    lines = out.splitlines()
    check(rc == 0 and len(lines) == 2 and all("only in" in ln for ln in lines) and any("wall_a" in ln for ln in lines)
          and any("wall_main" in ln for ln in lines), f"T58 without the map the rename prints two 'only in' lines: {out!r}, {err!r}")


CASES = (t58_scripts_doc, t58_api_doc, t58_readme, t58_skill, t58_changelog, t58_dump_diff)


def main():
    for fn in CASES:
        try:
            fn()
        except Exception as e:
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    sys.stdout.flush()
    if FAILURES:
        print(f"TESTFAIL test_v112: {len(FAILURES)} failure(s)")
        sys.exit(1)
    print("TESTPASS test_v112")


main()
