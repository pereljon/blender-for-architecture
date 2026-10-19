# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

- Imported from the untracked tree `-skills/blender-architectural-renders/` in the workspace root on 2026-10-17, without `__pycache__/` and `tests/out/`. The files match that tree (Revision 4).
- `reference/extensions.md`: install and per-run enabling of Bonsai and IfcOpenShell, Sun Position, Point Cloud I/O, and DXF tools, with an IFC recipe and a headless plan drawing; an Extensions section in SKILL.md (Revision 5).
- Tests: `bl_extensions` (operator names, a two-wall IFC within 0.01 ft, a headless plan SVG, Sun Position in a background run; skips when the extensions are not installed) and `test_extensions_doc`.

### Fixed

- SKILL.md: Blender ships numpy.
- reference/plan-input.md: extraction misses short wall pieces at junctions; shift door swings with shifted walls.
