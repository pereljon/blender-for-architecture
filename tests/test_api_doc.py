"""Keep reference/api.md in step with the scripts: every public function and class has a signature line."""
import ast
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
doc = open(os.path.join(ROOT, "reference", "api.md")).read()
missing = []
for mod in ("bhelpers", "mannequin", "checks", "sheets", "wall_gaps"):
    path = os.path.join(ROOT, "scripts", f"{mod}.py")
    if not os.path.exists(path):
        missing.append(f"{mod}.py (file not found)")
        continue
    for n in ast.parse(open(path).read()).body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_") and f"`{n.name}(" not in doc:
            missing.append(f"{mod}.{n.name}")
if missing:
    print("FAIL api.md lacks:", ", ".join(missing))
    sys.exit(1)
print("TESTPASS test_api_doc")
