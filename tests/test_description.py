"""Plain Python test: SKILL.md's frontmatter description (T27, Revision 5b D19)."""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
text = open(os.path.join(ROOT, "SKILL.md")).read()
problems = []
m = re.match(r"---\n(.*?)\n---\n", text, re.S)
if not m:
    problems.append("SKILL.md has no frontmatter")
    front = ""
else:
    front = m.group(1)
if not re.search(r"^name: \S+$", front, re.M):
    problems.append("frontmatter has no one-line name")
lines = [ln for ln in front.splitlines() if ln.startswith("description:")]
if len(lines) != 1:
    problems.append(f"frontmatter has {len(lines)} description lines (need 1)")
else:
    desc = lines[0][len("description:"):].strip()
    nxt = front.splitlines()[front.splitlines().index(lines[0]) + 1:]
    if nxt and nxt[0].startswith((" ", "\t")):
        problems.append("description continues on a second line")
    if ": " in desc:
        problems.append("description contains ': '")
    if len(desc) > 1024:
        problems.append(f"description is {len(desc)} characters (limit 1024)")
    for word in ("IFC", "LiDAR"):
        if not re.search(rf"\b{word}\b", desc):
            problems.append(f"description does not name {word}")
    if not re.search(r"\bsun\b", desc, re.I):
        problems.append("description does not name the sun")
if problems:
    print("FAIL SKILL.md description:", "; ".join(problems))
    sys.exit(1)
print("TESTPASS test_description")
