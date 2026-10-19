"""Keep reference/extensions.md in step with the extension checks: its operators and fields are the ones bl_extensions.py verifies."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extensions_names import LAS_ARGS, OPS, SUN_FIELDS

path = os.path.join(HERE, "..", "reference", "extensions.md")
if not os.path.isfile(path):
    print("FAIL reference/extensions.md does not exist")
    sys.exit(1)
doc = open(path).read()
problems = []
found = set(re.findall(r"bpy\.ops\.([a-z_]+\.[a-z0-9_]+)", doc))
if found != set(OPS):
    problems.append(f"bpy.ops names differ: only in doc {sorted(found - set(OPS))}, only in OPS {sorted(set(OPS) - found)}")
for name in SUN_FIELDS + LAS_ARGS:
    if f"`{name}`" not in doc:
        problems.append(f"`{name}` is not in backticks in the doc")
if problems:
    print("FAIL extensions.md:", "; ".join(problems))
    sys.exit(1)
print("TESTPASS test_extensions_doc")
