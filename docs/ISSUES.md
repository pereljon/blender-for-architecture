# Issues

State of the blender-architectural-renders skill: open bugs, planned work, next steps, open questions, and decisions. The skill-developer project's `docs/ISSUES.md` holds the migration.

## Bugs

- [ ] No test checks the font `compose.py` loads. With `font()` returning `None`, Pillow falls back to its default font and the suite still passes 37 of 37 (import check, 2026-10-17). Cosmetic.

## Planned

- [x] Receive the design contract (`dev/features/`) and review inputs (`dev/inputs/`) from the development session (resolved 2026-10-17): moved in unedited; three stale paths fixed.
- [ ] Release and install v1.0.0 (skill-developer migration step 5).
- [ ] Revision 6, before Revision 5's remaining items and before release: catch phantom geometry defects (one check gate run before every render, five new checks, loop rules, default eye height). Source: `dev/inputs/2026-10-20-phantom-defects.md`. Design: contract, "Revision 6". Branch `rev6-phantom-checks`.
- [ ] Revision 5, before release: test the DXF import and export extensions the doc names (install only with the user's consent; DWG is out of scope); write the IFC from the scene script's wall records; Sun Position mapped to `bhelpers.sun()` with a solar-noon test; description covers IFC, scan, and sun tasks, with a discovery eval and a negative case; drawing geometry check; keep-in-step for extension ids and `ifcopenshell.api` names; re-run the evals. Details: contract, "Revision 5 review findings".

## Next steps

- Import check (2026-10-17): suite 37 of 37 in this repo. With `set_units("ft")` broken to 0.3 in a copy of `scripts/`, 8 of 37 steps fail (`bl_helpers`, `bl_mannequin`, `bl_rev2`, `bl_rev3`).

## Open questions

## Decisions

- 2026-10-20, the user: take on Revision 6 as proposed (a `run_checks()` gate before every render, previews included; checks for wall gaps, camera rays, floor fit, clearance, and flipped faces; rules for `view_layer.update()`, exact-name skips, recessed emissive strips, and re-checks after level changes). It goes before Revision 5's remaining items, into v1.0.0. The default eye height is 5'-2 1/2" (a 5'-7" viewer). Rejected: separate checks for exposed slab sides (the coplanar check over the whole scene covers them) and for emissive faces (a rule and a QA item cover one occurrence); a Bonsai route for long-lived models (already in Revision 5).
