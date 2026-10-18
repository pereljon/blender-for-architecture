"""list_views.py TEMPLATE: print the keys of the template's VIEWS dict, one per line (parsed, not executed)."""
import ast
import sys

tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    if any(isinstance(t, ast.Name) and t.id == "VIEWS" for t in targets) and isinstance(node.value, ast.Dict):
        for k in node.value.keys:
            print(ast.literal_eval(k))
        break
