"""template_lib.py TEMPLATE: print the template's module-level LIB string (parsed, not executed); print nothing when it has none."""
import ast
import sys

tree = ast.parse(open(sys.argv[1]).read())
for node in tree.body:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    if any(isinstance(t, ast.Name) and t.id == "LIB" for t in targets) and isinstance(node.value, ast.Constant):
        print(node.value.value)
        break
