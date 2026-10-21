"""Keep reference/extensions.md in step with the extension checks: its operators and fields are the ones bl_extensions.py verifies."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extensions_names import EXTENSIONS, LAS_ARGS, OPS, SUN_FIELDS

path = os.environ.get("EXT_DOC") or os.path.join(HERE, "..", "reference", "extensions.md")
if not os.path.isfile(path):
    print("FAIL reference/extensions.md does not exist")
    sys.exit(1)
doc = open(path).read()
problems = []
found = set(re.findall(r"bpy\.ops\.([a-z_]+\.[a-z0-9_]+)", doc))
if found != set(OPS):
    problems.append(f"bpy.ops names differ: only in doc {sorted(found - set(OPS))}, only in OPS {sorted(set(OPS) - found)}")
for prefix, expected in (("- The fields are", SUN_FIELDS), ("- The LAS importer takes", LAS_ARGS)):
    lines = [ln for ln in doc.splitlines() if ln.startswith(prefix)]
    if not lines:
        problems.append(f"no line starts with '{prefix}'")
        continue
    names = set(re.findall(r"`([^`]+)`", lines[0]))
    if names != set(expected):
        problems.append(f"'{prefix}' line differs: only in doc {sorted(names - set(expected))}, only in test {sorted(set(expected) - names)}")

# Extension ids: the install line, the enable command, and every module name must agree with EXTENSIONS.
install_ids = [set(m.group(1).split(",")) for m in re.finditer(r"extension install ([\w,]+)", doc)]
if not install_ids:
    problems.append("no 'extension install' line")
enable_ids = []
for ln in (ln for ln in doc.splitlines() if "addon_utils.enable" in ln):
    tup = re.search(r"for \w+ in \(([^)]*)\)", ln)
    enable_ids.append(set(re.findall(r"'(\w+)'", tup.group(1))) if tup else set(re.findall(r"bl_ext\.blender_org\.(\w+)", ln)))
if not enable_ids:
    problems.append("no 'addon_utils.enable' line")
for kind, sets in (("extension install", install_ids), ("addon_utils.enable", enable_ids)):
    for ids in sets:
        if ids != set(EXTENSIONS):
            problems.append(f"{kind} ids {sorted(ids)} differ from {sorted(EXTENSIONS)}")
named = set(re.findall(r"bl_ext\.blender_org\.(\w+)", doc)).union(*install_ids)
if named - set(EXTENSIONS):
    problems.append(f"the doc names extension ids outside EXTENSIONS: {sorted(named - set(EXTENSIONS))}")
if problems:
    print("FAIL extensions.md:", "; ".join(problems))
    sys.exit(1)
print("TESTPASS test_extensions_doc")
