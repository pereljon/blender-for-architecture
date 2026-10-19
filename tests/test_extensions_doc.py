"""Keep reference/extensions.md in step with the extension checks: its operators and fields are the ones bl_extensions.py verifies."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extensions_names import LAS_ARGS, OPS, SUN_FIELDS

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
if problems:
    print("FAIL extensions.md:", "; ".join(problems))
    sys.exit(1)
print("TESTPASS test_extensions_doc")
