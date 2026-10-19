# Issues

State of the blender-architectural-renders skill: open bugs, planned work, next steps, open questions, and decisions. The skill-developer project's `docs/ISSUES.md` holds the migration.

## Bugs

- [ ] No test checks the font `compose.py` loads. With `font()` returning `None`, Pillow falls back to its default font and the suite still passes 37 of 37 (import check, 2026-10-17). Cosmetic.

## Planned

- [x] Receive the design contract (`dev/features/`) and review inputs (`dev/inputs/`) from the development session (resolved 2026-10-17): moved in unedited; three stale paths fixed.
- [ ] Release and install v1.0.0 (skill-developer migration step 5).
- [ ] Revision 5, before release: DWG route (tool to be chosen by the user); write the IFC from the scene script's wall records; Sun Position mapped to `bhelpers.sun()` with a solar-noon test; description covers IFC, scan, and sun tasks, with a discovery eval and a negative case; drawing geometry check; keep-in-step for extension ids and `ifcopenshell.api` names; re-run the evals. Details: contract, "Revision 5 review findings".

## Next steps

- Import check (2026-10-17): suite 37 of 37 in this repo. With `set_units("ft")` broken to 0.3 in a copy of `scripts/`, 8 of 37 steps fail (`bl_helpers`, `bl_mannequin`, `bl_rev2`, `bl_rev3`).

## Open questions

## Decisions
