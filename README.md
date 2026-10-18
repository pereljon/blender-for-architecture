# blender-architectural-renders

Builds architectural and remodel renders in Blender from a Python scene script, run headless with Cycles. Covers project setup, plan input, perspective and cut plan views, option studies, a posable scale figure with clash checks, render QA, and optional construction sheets and tile cutting plans.

## Install

From the skill-developer project root, after the release is approved:

```
python3 scripts/install_skill.py blender-architectural-renders <tag>
```

## Tests

```
tests/run_tests.sh
```

- Requires Blender at `/Applications/Blender.app/Contents/MacOS/Blender`; override with `BLENDER`.
- `SCRIPTS_DIR` overrides the scripts under test (default `scripts/`).
- Output and logs go to `tests/out/`, which is gitignored.
