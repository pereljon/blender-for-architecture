"""Plain-Python tests for v1.1.0 (T30 to T36, T40, T41, and the E10 fixture), from Revision 8 of the design.

SKILL_DIR overrides the skill folder (default: the parent of tests/). A test that needs git or a tag prints a SKIP line
and passes when git or the tag is not available.
"""
import ast
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SKILL_DIR") or os.path.dirname(HERE)
FAILURES = []
LIB_MODULES = ("bhelpers", "checks", "mannequin", "wall_gaps", "ifc_walls", "sheets")
NUMBERED = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$", re.M)
UNRELEASED = re.compile(r"^## \[?Unreleased\]?\s*$", re.M)


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)
        print("  FAIL", msg)
    return bool(cond)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def vtuple(v):
    return tuple(int(p) for p in v.split("."))


def doc_files():
    """SKILL.md, reference/*.md, templates/*.py, scripts/*.py: the files that carry paths and commands."""
    files = [os.path.join(ROOT, "SKILL.md")]
    for pat in ("reference/*.md", "templates/*.py", "scripts/*.py"):
        files += sorted(glob.glob(os.path.join(ROOT, pat)))
    return files


def lines_of(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def rel(path):
    return os.path.relpath(path, ROOT)


def git(*args):
    """Run git in ROOT; return stdout text, or None when git is missing or the command fails."""
    if not shutil.which("git"):
        return None
    try:
        r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def has_repo():
    return git("rev-parse", "--is-inside-work-tree") is not None


# ---------------------------------------------------------------- T30
def t30():
    log = read("CHANGELOG.md")
    versions = NUMBERED.findall(log)
    if check(versions, "T30 CHANGELOG has a heading '## [X.Y.Z] - YYYY-MM-DD'"):
        order = [vtuple(v) for v in versions]
        check(order == sorted(order, reverse=True), f"T30 numbered headings run newest first, got {versions}")
        check(versions[0] == max(versions, key=vtuple), f"T30 the first numbered heading is the highest: {versions}")
    ga = [ln for ln in read(".gitattributes").splitlines() if "CHANGELOG.md" in ln and "export-ignore" in ln]
    check(not ga, f"T30 .gitattributes export-ignores CHANGELOG.md: {ga}")
    if not has_repo():
        print("SKIP T30 git archive: git is not available or this is not a repository")
        return
    r = subprocess.run(["git", "-C", ROOT, "archive", "--worktree-attributes", "--format=tar", "HEAD"],
                       capture_output=True, timeout=60)
    if not check(r.returncode == 0, f"T30 git archive runs: {r.stderr.decode()[:200]}"):
        return
    names = tarfile.open(fileobj=io.BytesIO(r.stdout)).getnames()
    check("CHANGELOG.md" in names, "T30 git archive lists CHANGELOG.md at the top level")


# ---------------------------------------------------------------- T31
def changelog_state():
    """(highest numbered version tuple or None, unreleased heading present)."""
    log = read("CHANGELOG.md")
    versions = [vtuple(v) for v in NUMBERED.findall(log)]
    return (max(versions) if versions else None), bool(UNRELEASED.search(log))


def t31():
    tree = ast.parse(read("templates", "scene_template.py"))
    lib = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "LIB" for t in node.targets) \
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            lib = node.value.value
    if not check(lib and re.fullmatch(r"v\d+\.\d+\.\d+", lib), f"T31 the template assigns LIB = 'vX.Y.Z' at module level, got {lib!r}"):
        lib = None
    inserts = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == "sys.path.insert"]
    ok = False
    for call in inserts:
        arg = call.args[1] if len(call.args) > 1 else None
        if isinstance(arg, ast.Call) and ast.unparse(arg.func) == "os.path.join" and len(arg.args) >= 3:
            last2 = arg.args[-2:]
            ok = ok or (isinstance(last2[0], ast.Constant) and last2[0].value == "lib"
                        and isinstance(last2[1], ast.Name) and last2[1].id == "LIB")
    check(ok, "T31 sys.path.insert's path is os.path.join(..., 'lib', LIB)")
    highest, unreleased = changelog_state()
    if lib and highest:
        have = vtuple(lib[1:])
        if unreleased:
            check(have >= highest, f"T31 LIB {lib} is at least the highest CHANGELOG version {highest} (unreleased heading present)")
        else:
            check(have == highest, f"T31 LIB {lib} equals v{'.'.join(map(str, highest))}")


# ---------------------------------------------------------------- T33
LIB_FILE = re.compile(r"lib/(?=[\w.*-]+\.(?:py|json)\b)")
LIB_SPAN = re.compile(r"`blender/lib`")
SYS_PATH_LIB = re.compile(r"""["']lib["']\)""")
LIB_REST = re.compile(r"(?<![\w.])lib/([^\s`'\")]*)")
LIB_OK = re.compile(r"(?:<LIB>|vX\.Y\.Z|v\d+\.\d+\.\d+|pre-1\.0)(?!\w)")


def t33():
    bad = []
    for path in doc_files():
        for n, line in enumerate(lines_of(path), 1):
            where = f"{rel(path)}:{n}"
            for pat, what in ((LIB_FILE, "a file or glob directly under lib/"), (LIB_SPAN, "`blender/lib` with no slash"),
                              (SYS_PATH_LIB, "a sys.path entry that ends at lib")):
                if pat.search(line):
                    bad.append(f"{where}: {what}")
            for m in LIB_REST.finditer(line):
                rest = m.group(1)
                if rest.strip(".,;:") and not LIB_OK.match(rest):
                    bad.append(f"{where}: lib/{rest} is not followed by a version folder")
    check(not bad, "T33 lib paths carry the version folder: " + "; ".join(sorted(set(bad))))


# ---------------------------------------------------------------- T34
GIT_WORDS = re.compile(r"\b(git|gitignore|commit\w*|push\w*|branch\w*)\b", re.I)


def t34():
    hits = [f"SKILL.md:{n}: {m.group(0)}" for n, line in enumerate(lines_of(os.path.join(ROOT, "SKILL.md")), 1)
            for m in GIT_WORDS.finditer(line)]
    check(not hits, "T34 SKILL.md has no git rules: " + "; ".join(hits))


# ---------------------------------------------------------------- T35
PREFIX_FORM = re.compile(r'BLENDER=[^\s;]+\s+"?\$BLENDER')
RULE_LINE = 'BLENDER=<path>; "$BLENDER" --factory-startup -b --python-exit-code 1 -P script.py -- args'


def command_start(lines, i):
    """Index of the first line of the command that line i belongs to, following backslash continuations upward."""
    while i > 0 and lines[i - 1].rstrip().endswith("\\"):
        i -= 1
    return i


def t35():
    app_lines = []
    for path in doc_files():
        lines = lines_of(path)
        for i, line in enumerate(lines):
            if "/Applications/Blender.app" in line:
                app_lines.append(f"{rel(path)}:{i + 1}")
            if "--factory-startup" in line and '"$BLENDER" --factory-startup' not in line:
                head = lines[command_start(lines, i)]
                if i == command_start(lines, i) or '"$BLENDER"' not in head:
                    check(False, f'T35 {rel(path)}:{i + 1} holds --factory-startup without "$BLENDER" before it')
            if PREFIX_FORM.search(line):
                check(False, f"T35 {rel(path)}:{i + 1} uses BLENDER=<path> without a semicolon before $BLENDER")
    check(len(app_lines) == 1 and app_lines[0].startswith("SKILL.md:"),
          f"T35 /Applications/Blender.app appears on exactly one line, in SKILL.md: {app_lines}")
    skill = lines_of(os.path.join(ROOT, "SKILL.md"))
    in_fence, found = False, False
    for line in skill:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif in_fence and line.strip() == RULE_LINE:
            found = True
    check(found, f"T35 SKILL.md holds this line inside a fenced block: {RULE_LINE}")
    text = "\n".join(skill)
    for name in ("Metal", "OptiX", "CUDA", "HIP"):
        check(re.search(rf"\b{name}\b", text), f"T35 SKILL.md names {name}")


# ---------------------------------------------------------------- T36
def t36():
    docs = [os.path.join(ROOT, "SKILL.md")] + sorted(glob.glob(os.path.join(ROOT, "reference", "*.md")))
    for token in ("context/", "deliverables/", "incoming/"):
        hits = [f"{rel(p)}:{n}" for p in docs for n, line in enumerate(lines_of(p), 1) if token in line]
        if token == "incoming/":
            check(not hits, f"T36 incoming/ appears nowhere: {hits}")
        else:
            check(len(hits) == 1 and hits[0].startswith("SKILL.md:"),
                  f"T36 {token} appears on exactly one line, in SKILL.md: {hits}")


# ---------------------------------------------------------------- T40
def public_api(source):
    """{name: signature} for each public top-level function, and each public class (its __init__ arguments)."""
    out = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            out[node.name] = "def " + ast.unparse(node.args)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
            out[node.name] = "class " + (ast.unparse(init.args) if init else "")
    return out


def sections(log):
    """[(heading text, body)] of the CHANGELOG's '## ' sections, in file order."""
    parts = re.split(r"^(## .*)$", log, flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def named(text, module, name):
    return re.search(rf"`{re.escape(module)}\.{re.escape(name)}(\([^`]*\))?`", text) is not None


def t40():
    if not has_repo():
        print("SKIP T40 git is not available or this is not a repository")
        return
    here_tags = set((git("tag", "--points-at", "HEAD", "--list", "v*") or "").split())
    merged = (git("tag", "--merged", "HEAD", "--list", "v*", "--sort=-v:refname") or "").split()
    older = [t for t in merged if t not in here_tags]
    log = read("CHANGELOG.md")
    if not older:
        print("SKIP T40 no earlier v* tag is reachable from HEAD")
    else:
        tag = older[0]
        m = re.search(rf"^## \[{re.escape(tag[1:])}\]", log, re.M)
        if check(m, f"T40 CHANGELOG has a heading for {tag}"):
            above = log[:m.start()]
            for mod in LIB_MODULES:
                old_src = git("show", f"{tag}:scripts/{mod}.py")
                old = public_api(old_src) if old_src else {}
                path = os.path.join(ROOT, "scripts", f"{mod}.py")
                new = public_api(open(path, encoding="utf-8").read()) if os.path.isfile(path) else {}
                for name in sorted(set(old) | set(new)):
                    if old.get(name) != new.get(name):
                        what = "added" if name not in old else "removed" if name not in new else "changed"
                        check(named(above, mod, name),
                              f"T40 {mod}.{name} was {what} since {tag} but the CHANGELOG above {tag} does not name `{mod}.{name}()`")
    # R45.3: the v1.1.0 entry names setup_cycles and eye_height
    highest, unreleased = changelog_state()
    secs = sections(log)
    entry = next((body for head, body in secs if head.startswith("## [1.1.0]")), None)
    if entry is None and unreleased and highest and highest < (1, 1, 0):
        entry = next((body for head, body in secs if UNRELEASED.match(head)), None)
    if entry is None:
        print("SKIP T40 no v1.1.0 entry to check")
        return
    for name in ("setup_cycles", "eye_height"):
        check(named(entry, "bhelpers", name), f"T40 the v1.1.0 CHANGELOG entry names `bhelpers.{name}()`")


# ---------------------------------------------------------------- T41
def t41():
    if not has_repo():
        print("SKIP T41 git is not available or this is not a repository")
        return
    tags = (git("tag", "--points-at", "HEAD", "--list", "v*") or "").split()
    if not tags:
        print("SKIP T41 HEAD carries no v* tag")
        return
    tag = max(tags, key=lambda t: vtuple(t[1:]))
    log = read("CHANGELOG.md")
    check(not UNRELEASED.search(log), f"T41 at {tag} the CHANGELOG has no unreleased heading")
    nums = NUMBERED.findall(log)
    check(bool(nums) and nums[0] == tag[1:], f"T41 the first numbered CHANGELOG heading equals {tag[1:]}, got {nums[:1]}")
    out = subprocess.run([sys.executable, "-I", os.path.join(HERE, "template_lib.py"),
                          os.path.join(ROOT, "templates", "scene_template.py")], capture_output=True, text=True)
    check(out.stdout.strip() == tag, f"T41 the template's LIB equals {tag}, got {out.stdout.strip()!r}")


# ---------------------------------------------------------------- E10 fixture
def fixture_checks():
    base = os.path.join(HERE, "fixtures", "migration")
    build = os.path.join(base, "renders", "build_house.py")
    sheet = os.path.join(base, "renders", "make_sheet.py")
    for p in (build, sheet, os.path.join(base, "renders", "cuts.py")):
        check(os.path.isfile(p), f"fixture file exists: {os.path.relpath(p, HERE)}")
    if not (os.path.isfile(build) and os.path.isfile(sheet)):
        return
    src = open(build, encoding="utf-8").read()
    check(len(src.splitlines()) >= 250, "fixture build_house.py is a monolithic script of about 300 lines")
    check(not re.search(r"^\s*(import|from)\s+(bhelpers|checks|mannequin|sheets)\b", src, re.M), "fixture build_house.py imports no skill library")
    check("lib" not in re.findall(r"['\"]lib['\"]", src), "fixture build_house.py has no lib path")
    tree = ast.parse(src)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    check("box" in funcs and [a.arg for a in funcs["box"].args.args] == ["name", "x0", "x1", "y0", "y1", "z0", "z1", "mat", "bevel", "seg"],
          "fixture box() has the lib's signature")
    check("cyl" in funcs and "CYL_SEGMENTS" in ast.unparse(funcs["cyl"]) and "n" not in [a.arg for a in funcs["cyl"].args.args],
          "fixture cyl() reads a project constant for its segments")
    check("principled" in funcs and ast.unparse(funcs["principled"].args).count("0.8") == 1, "fixture principled() defaults roughness to 0.8")
    check("wall_{i}" in src, "fixture names walls by list index (wall_0 to wall_9)")
    check("FT = 0.3048" in src and "shelf_floating" in src and "SUN = (" in src, "fixture is in feet, with a floating shelf and a fixed sun")
    check("sys.path" not in open(sheet, encoding="utf-8").read(), "fixture make_sheet.py relies on the interpreter for its sibling import")
    s = open(sheet, encoding="utf-8").read()
    check("PAGE = (3300, 2340)" in s and re.search(r"^from cuts import", s, re.M), "fixture sheet has PAGE = (3300, 2340) and imports its sibling cuts")
    delivered = glob.glob(os.path.join(base, "delivered", "*", "*.png"))
    check(len(delivered) == 1, f"fixture holds one delivered image, got {len(delivered)}")
    check(not os.path.exists(os.path.join(base, ".git")) and not os.path.isdir(os.path.join(base, "renders", "lib")),
          "fixture has no git folder and no lib folder")


CASES = (t30, t31, t33, t34, t35, t36, t40, t41, fixture_checks)


def main():
    import traceback
    for fn in CASES:
        try:
            fn()
        except Exception as e:
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    sys.stdout.flush()
    if FAILURES:
        print(f"TESTFAIL test_v110: {len(FAILURES)} failure(s)")
        sys.exit(1)
    print("TESTPASS test_v110")


main()
